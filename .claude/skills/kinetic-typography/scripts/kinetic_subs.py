#!/usr/bin/env python3
"""Kinetic typography subtitles for interview videos.

Reads a cue sheet (JSON) and writes an ASS subtitle file with three layers:

  1. Bottom captions   - speaker tag + dialogue, fade/slide-in, keywords
                          highlighted and pulsed at the moment they are spoken.
  2. Keyword cards     - big centred term + one-line gloss (e.g. SSOT,
                          PRD) with a pop-in scale animation.
  3. Emphasis phrases  - centred punch / typewriter / slide reveal.

Then optionally burns it into a video with ffmpeg (libass) and extracts
preview frames at the busiest moments so a person (or Claude) can look.

Usage:
  kinetic_subs.py cues.json -o out.ass                 # build + validate
  kinetic_subs.py cues.json -o out.ass --render in.mp4 out.mp4 --frames frames/
  kinetic_subs.py cues.json --check                    # validate only

Only the standard library is needed to build the ASS file. Rendering needs
ffmpeg with libass and a Korean font (Noto Sans CJK KR).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

# ---------------------------------------------------------------- defaults
DEFAULT_STYLE = {
    "font": "Noto Sans CJK KR",
    "caption_scale": 0.052,      # caption font size as a fraction of height
    "card_scale": 0.105,
    "gloss_scale": 0.040,
    "emph_scale": 0.085,
    "caption_margin": 0.075,     # bottom margin as a fraction of height
    "card_y": 0.38,              # card centre as a fraction of height
    "emph_y": 0.42,
    "accent": "#FFC93C",         # keyword highlight colour
    "card_box": "#101418",       # card background box
    "card_box_alpha": 0.25,      # 0 = opaque, 1 = transparent
    "max_cps": 16.0,             # Korean reading speed warning threshold
    "min_caption": 0.8,          # seconds
    "card_duration": 2.4,
    "card_max_delay": 1.2,       # a queued card later than this is dropped
    "keyword_once": True,        # card only on a keyword's first mention
}

SPEAKER_COLORS = ["#FFFFFF", "#7FDBFF", "#FFC93C", "#B8F2A0"]


@dataclass
class Event:
    layer: int
    start: float
    end: float
    style: str
    text: str
    kind: str = ""
    label: str = ""


@dataclass
class Report:
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    info: dict = field(default_factory=dict)

    def ok(self) -> bool:
        return not self.errors


# ---------------------------------------------------------------- helpers
def ass_color(hex_rgb: str, alpha: float = 0.0) -> str:
    """'#RRGGBB' -> '&HAABBGGRR' (ASS is BGR with inverted alpha)."""
    h = hex_rgb.lstrip("#")
    if len(h) != 6 or not re.fullmatch(r"[0-9A-Fa-f]{6}", h):
        raise ValueError(f"bad colour: {hex_rgb}")
    r, g, b = h[0:2], h[2:4], h[4:6]
    a = max(0, min(255, round(alpha * 255)))
    return f"&H{a:02X}{b}{g}{r}".upper()


def inline_color(hex_rgb: str) -> str:
    return "&H" + ass_color(hex_rgb)[4:] + "&"  # &HBBGGRR&


def ass_time(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def esc(text: str) -> str:
    """Escape user text for an ASS Dialogue line."""
    return (text.replace("\\", "＼").replace("{", "｛")
            .replace("}", "｝").replace("\n", "\\N"))  # \n = row break from wrap()


def visual_len(text: str) -> float:
    """Approximate width in em: CJK = 1, latin/digits/space ~ 0.55."""
    w = 0.0
    for ch in text:
        if ord(ch) >= 0x1100:
            w += 1.0
        elif ch == " ":
            w += 0.3
        else:
            w += 0.58
    return w


def wrap(text: str, max_em: float) -> list[str]:
    """Wrap into at most 2 balanced lines at a space; never split a word."""
    text = " ".join(text.split())
    if visual_len(text) <= max_em:
        return [text]
    words = text.split(" ")
    best, best_diff = None, None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        diff = abs(visual_len(a) - visual_len(b))
        if best_diff is None or diff < best_diff:
            best, best_diff = [a, b], diff
    return best or [text]


def parse_time(v) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    m = re.fullmatch(r"(?:(\d+):)?(\d+):(\d+(?:[.,]\d+)?)", str(v).strip())
    if not m:
        raise ValueError(f"bad time: {v}")
    h = int(m.group(1) or 0)
    return h * 3600 + int(m.group(2)) * 60 + float(m.group(3).replace(",", "."))


# ---------------------------------------------------------------- builder
class Builder:
    def __init__(self, cues: dict):
        self.cues = cues
        v = cues.get("video", {})
        self.W = int(v.get("width", 1920))
        self.H = int(v.get("height", 1080))
        self.st = {**DEFAULT_STYLE, **cues.get("style", {})}
        self.report = Report()
        self.events: list[Event] = []

        self.speakers = {}
        for i, (key, sp) in enumerate(cues.get("speakers", {}).items()):
            sp = sp if isinstance(sp, dict) else {"name": str(sp)}
            self.speakers[key] = {
                "name": sp.get("name", key),
                "color": sp.get("color", SPEAKER_COLORS[i % len(SPEAKER_COLORS)]),
            }

        self.keywords = []
        for kw in cues.get("keywords", []):
            kw = kw if isinstance(kw, dict) else {"term": str(kw)}
            terms = [kw["term"], *kw.get("aliases", [])]
            # longest first so "기능 명세서" beats "명세서"
            # a space in a term also matches the row break inserted by wrap()
            pat = "|".join(r"\s+".join(map(re.escape, t.split()))
                           for t in sorted(terms, key=len, reverse=True))
            self.keywords.append({
                "term": kw["term"],
                "gloss": kw.get("gloss", ""),
                "card": kw.get("card", True),
                "re": re.compile(pat, re.IGNORECASE),
            })

    # sizes ---------------------------------------------------------------
    def fs(self, key: str) -> int:
        # scale by the short side so 9:16 shorts don't get 1920-tall fonts;
        # portrait gets +15% because phones are viewed small.
        base = min(self.W, self.H) * (1.15 if self.H > self.W else 1.0)
        return max(12, round(base * self.st[key]))

    # header --------------------------------------------------------------
    def header(self) -> str:
        f = self.st["font"]
        white, black = ass_color("#FFFFFF"), ass_color("#000000")
        shadow = ass_color("#000000", 0.45)
        box = ass_color(self.st["card_box"], self.st["card_box_alpha"])
        accent = ass_color(self.st["accent"])
        ol = max(2, round(self.H / 360))
        mv = round(self.H * self.st["caption_margin"])
        styles = [
            # Name,Font,Size,Primary,Secondary,Outline,Back,Bold,Italic,U,S,
            # ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Align,ML,MR,MV,Enc
            f"Caption,{f},{self.fs('caption_scale')},{white},{white},{black},{shadow},"
            f"-1,0,0,0,100,100,0,0,1,{ol},{ol//2+1},2,60,60,{mv},1",
            f"Card,{f},{self.fs('card_scale')},{accent},{accent},{box},{box},"
            f"-1,0,0,0,100,100,2,0,3,{round(self.H/60)},0,5,60,60,0,1",
            f"Gloss,{f},{self.fs('gloss_scale')},{white},{white},{black},{shadow},"
            f"-1,0,0,0,100,100,0,0,1,{ol},1,5,60,60,0,1",
            f"Emph,{f},{self.fs('emph_scale')},{white},{white},{black},{shadow},"
            f"-1,0,0,0,100,100,1,0,1,{ol+2},{ol},5,80,80,0,1",
        ]
        return (
            "[Script Info]\nScriptType: v4.00+\nWrapStyle: 2\n"
            f"PlayResX: {self.W}\nPlayResY: {self.H}\nScaledBorderAndShadow: yes\n"
            "YCbCr Matrix: TV.709\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
            "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
            "MarginL, MarginR, MarginV, Encoding\n"
            + "\n".join("Style: " + s for s in styles)
            + "\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, "
            "MarginR, MarginV, Effect, Text\n"
        )

    # 1. captions -----------------------------------------------------------
    def build_captions(self):
        lines = self.cues.get("lines", [])
        max_em = (self.W * 0.88) / self.fs("caption_scale")
        x = self.W // 2
        y = self.H - round(self.H * self.st["caption_margin"])
        lift = round(self.H * 0.018)
        tag_fs = round(self.fs("caption_scale") * 0.62)
        accent = inline_color(self.st["accent"])
        prev_end = -1.0
        mentions = []  # (time, keyword) for cards

        for n, ln in enumerate(lines, 1):
            try:
                s, e = parse_time(ln["start"]), parse_time(ln["end"])
            except (KeyError, ValueError) as ex:
                self.report.errors.append(f"line {n}: {ex}")
                continue
            text = " ".join(str(ln.get("text", "")).split())
            if e <= s:
                self.report.errors.append(f"line {n}: end <= start ({s}->{e})")
                continue
            if s < prev_end - 0.01:
                self.report.errors.append(
                    f"line {n}: overlaps previous caption by {prev_end - s:.2f}s")
            prev_end = e
            dur = e - s
            if dur < self.st["min_caption"]:
                self.report.warnings.append(f"line {n}: only {dur:.2f}s on screen")
            chars = len(re.sub(r"\s", "", text))
            if dur > 0 and chars / dur > self.st["max_cps"]:
                self.report.warnings.append(
                    f"line {n}: {chars / dur:.1f} chars/s (> {self.st['max_cps']}) "
                    "- split it or extend the time")

            spk = ln.get("speaker")
            if spk and spk not in self.speakers:
                self.report.errors.append(f"line {n}: unknown speaker '{spk}'")
                spk = None

            rows = wrap(text, max_em)
            if len(rows) > 2 or any(visual_len(r) > max_em for r in rows):
                self.report.warnings.append(f"line {n}: too long for 2 rows - split it")
            flat = "\n".join(rows)

            # keyword spans on the wrapped text
            spans = []
            for kw in self.keywords:
                for m in kw["re"].finditer(flat):
                    spans.append((m.start(), m.end(), kw))
            spans.sort(key=lambda t: (t[0], -(t[1] - t[0])))
            kept, cursor = [], -1
            for sp in spans:
                if sp[0] >= cursor:
                    kept.append(sp)
                    cursor = sp[1]

            total = max(1, len(flat))
            out, pos = [], 0
            for a, b, kw in kept:
                out.append(esc(flat[pos:a]))
                t_kw = round(dur * 1000 * a / total)            # ms into the line
                t_kw = max(0, min(t_kw, round(dur * 1000) - 300))
                out.append(
                    f"{{\\c{accent}\\t({t_kw},{t_kw+140},\\fscx116\\fscy116)"
                    f"\\t({t_kw+140},{t_kw+300},\\fscx100\\fscy100)}}"
                    + esc(flat[a:b]) + "{\\c&HFFFFFF&}")
                mentions.append((s + t_kw / 1000, kw, n))
                pos = b
            out.append(esc(flat[pos:]))
            body = "".join(out)

            tag = ""
            if spk:
                sp = self.speakers[spk]
                tag = (f"{{\\fs{tag_fs}\\c{inline_color(sp['color'])}}}"
                       f"{esc(sp['name'])}\\N{{\\fs{self.fs('caption_scale')}\\c&HFFFFFF&}}")
            fade_in = min(150, round(dur * 250))
            self.events.append(Event(
                0, s, e, "Caption",
                f"{{\\fad({fade_in},120)\\move({x},{y + lift},{x},{y},0,200)}}{tag}{body}",
                "caption", text[:30]))
        return mentions

    # 2. emphasis ---------------------------------------------------------
    def build_emphasis(self):
        x, y = self.W // 2, round(self.H * self.st["emph_y"])
        windows = []
        max_em = (self.W * 0.86) / self.fs("emph_scale")
        for n, em in enumerate(self.cues.get("emphasis", []), 1):
            try:
                s, e = parse_time(em["start"]), parse_time(em["end"])
            except (KeyError, ValueError) as ex:
                self.report.errors.append(f"emphasis {n}: {ex}")
                continue
            if e <= s:
                self.report.errors.append(f"emphasis {n}: end <= start")
                continue
            text = " ".join(str(em.get("text", "")).split())
            mode = em.get("style", "punch")
            rows = wrap(text, max_em)
            if len(rows) > 2:
                self.report.warnings.append(f"emphasis {n}: longer than 2 rows")
            dur_ms = round((e - s) * 1000)
            color = em.get("color")
            head = f"{{\\fad(0,220)\\pos({x},{y})"
            head += f"\\c{inline_color(color)}}}" if color else "}"

            if mode == "typewriter":
                chars = list("\n".join(rows))
                step = min(70, max(25, (dur_ms * 0.5) // max(1, len(chars))))
                parts = []
                for i, ch in enumerate(chars):
                    if ch == "\n":
                        parts.append("\\N")
                        continue
                    t0 = i * step
                    parts.append(f"{{\\alpha&HFF&\\t({t0},{t0+60},\\alpha&H00&)}}{esc(ch)}")
                body = "".join(parts)
            elif mode == "slide":
                dx = round(self.W * 0.06)
                head = (f"{{\\fad(180,220)\\move({x - dx},{y},{x},{y},0,320)"
                        + (f"\\c{inline_color(color)}" if color else "") + "}")
                body = "\\N".join(esc(r) for r in rows)
            else:  # punch: word-by-word pop
                if mode != "punch":
                    self.report.warnings.append(
                        f"emphasis {n}: unknown style '{mode}', used punch")
                words = []
                for ri, r in enumerate(rows):
                    if ri:
                        words.append(None)
                    words.extend(r.split(" "))
                real = [w for w in words if w is not None]
                step = min(220, max(80, (dur_ms * 0.45) // max(1, len(real))))
                parts, k = [], 0
                for w in words:
                    if w is None:
                        parts.append("\\N")
                        continue
                    t0 = k * step
                    parts.append(
                        f"{{\\alpha&HFF&\\fscx70\\fscy70\\t({t0},{t0+90},\\alpha&H00&"
                        f"\\fscx112\\fscy112)\\t({t0+90},{t0+200},\\fscx100\\fscy100)}}"
                        f"{esc(w)} ")
                    k += 1
                body = "".join(parts).rstrip()
            self.events.append(Event(2, s, e, "Emph", head + body, "emphasis", text[:30]))
            windows.append((s, e))
        return windows

    # 3. keyword cards ------------------------------------------------------
    def build_cards(self, mentions, emph_windows):
        x = self.W // 2
        y = round(self.H * self.st["card_y"])
        gy = y + round(self.fs("card_scale") * 0.95)
        seen, busy_until, shown, dropped = set(), -1.0, [], []
        dur = self.st["card_duration"]
        explicit = [(parse_time(c["start"]), c) for c in self.cues.get("cards", [])]

        queue = []
        for t, kw, n in sorted(mentions, key=lambda m: m[0]):
            if not kw["card"]:
                continue
            if self.st["keyword_once"] and kw["term"] in seen:
                continue
            seen.add(kw["term"])
            queue.append((t, kw["term"], kw["gloss"]))
        for t, c in explicit:
            queue.append((t, c["term"], c.get("gloss", "")))
        queue.sort(key=lambda q: q[0])

        for t, term, gloss in queue:
            start = max(t, busy_until)
            # never sit on top of an emphasis phrase
            for es, ee in emph_windows:
                if start < ee and start + dur > es:
                    start = ee
            if start - t > self.st["card_max_delay"]:
                dropped.append(term)
                continue
            end = start + dur
            self.events.append(Event(
                1, start, end, "Card",
                f"{{\\pos({x},{y})\\fad(0,250)\\alpha&HFF&\\fscx40\\fscy40"
                f"\\t(0,110,\\alpha&H00&)\\t(0,170,\\fscx112\\fscy112)"
                f"\\t(170,300,\\fscx100\\fscy100)}}{esc(term)}",
                "card", term))
            if gloss:
                self.events.append(Event(
                    1, start + 0.18, end, "Gloss",
                    f"{{\\pos({x},{gy})\\fad(220,250)}}{esc(gloss)}", "gloss", term))
            busy_until = end + 0.15
            shown.append(term)

        listed = {k["term"] for k in self.keywords}
        mentioned = {m[1]["term"] for m in mentions}
        for term in sorted(listed - mentioned):
            self.report.warnings.append(
                f"keyword '{term}' never appears in any line (check spelling/aliases)")
        if dropped:
            self.report.warnings.append(
                "cards dropped (too crowded, add explicit 'cards' or space them): "
                + ", ".join(dropped))
        self.report.info["cards"] = shown

    # all -------------------------------------------------------------------
    def build(self) -> str:
        if not self.cues.get("lines"):
            self.report.errors.append("no 'lines' in cue sheet")
        mentions = self.build_captions()
        windows = self.build_emphasis()
        self.build_cards(mentions, windows)
        self.events.sort(key=lambda e: (e.start, e.layer))
        self.report.info.update({
            "resolution": f"{self.W}x{self.H}",
            "captions": sum(e.kind == "caption" for e in self.events),
            "emphasis": sum(e.kind == "emphasis" for e in self.events),
            "duration": round(max((e.end for e in self.events), default=0), 2),
        })
        body = "".join(
            f"Dialogue: {e.layer},{ass_time(e.start)},{ass_time(e.end)},{e.style},"
            f",0,0,0,,{e.text}\n" for e in self.events)
        return self.header() + body

    def preview_times(self) -> list[tuple[float, str]]:
        """Moments worth looking at: each card/emphasis at full size."""
        out = []
        for e in self.events:
            if e.kind == "card":
                out.append((min(e.start + 0.7, e.end - 0.05), f"card:{e.label}"))
            elif e.kind == "emphasis":  # after every word has landed
                out.append((max(e.start, e.end - 0.4), f"emphasis:{e.label}"))
        caps = [e for e in self.events if e.kind == "caption"]
        if caps:  # the longest caption, for line wrapping
            c = max(caps, key=lambda e: len(e.text))
            out.append(((c.start + c.end) / 2, "caption:longest"))
        return sorted(out)


# ---------------------------------------------------------------- render
def render(ass_path, src, dst, frames_dir, times):
    fontsdir = "/usr/share/fonts/opentype/noto"
    vf = f"ass={ass_path}" + (f":fontsdir={fontsdir}" if os.path.isdir(fontsdir) else "")
    tmp = dst + ".part.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vf", vf,
           "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
           "-pix_fmt", "yuv420p", "-c:a", "copy", tmp]
    subprocess.run(cmd, check=True)
    os.replace(tmp, dst)
    paths = []
    if frames_dir:
        os.makedirs(frames_dir, exist_ok=True)
        for i, (t, label) in enumerate(times, 1):
            safe = re.sub(r"[^\w가-힣]+", "_", label)[:40]
            p = os.path.join(frames_dir, f"{i:02d}_{t:06.2f}s_{safe}.jpg")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}",
                            "-i", dst, "-frames:v", "1", "-q:v", "3", p], check=True)
            paths.append(p)
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cues", help="cue sheet JSON")
    ap.add_argument("-o", "--out", help="ASS file to write")
    ap.add_argument("--check", action="store_true", help="validate only")
    ap.add_argument("--render", nargs=2, metavar=("IN", "OUT"), help="burn into video")
    ap.add_argument("--frames", help="directory for preview frames (with --render)")
    ap.add_argument("--strict", action="store_true", help="warnings fail too")
    a = ap.parse_args(argv)

    with open(a.cues, encoding="utf-8") as f:
        cues = json.load(f)
    b = Builder(cues)
    ass = b.build()
    rep = b.report
    print(json.dumps({"errors": rep.errors, "warnings": rep.warnings, **rep.info},
                     ensure_ascii=False, indent=2))
    if not rep.ok() or (a.strict and rep.warnings):
        return 1
    if a.check:
        return 0
    out = a.out or os.path.splitext(a.cues)[0] + ".ass"
    with open(out, "w", encoding="utf-8-sig") as f:
        f.write(ass)
    print(f"ASS: {out}")
    if a.render:
        frames = render(out, a.render[0], a.render[1], a.frames, b.preview_times())
        print(f"VIDEO: {a.render[1]}")
        for p in frames:
            print(f"FRAME: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
