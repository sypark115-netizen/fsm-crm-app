"""Tests for kinetic_subs.py.  Run: python3 -m unittest discover -s scripts"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import kinetic_subs as ks  # noqa: E402

EXAMPLE = os.path.join(os.path.dirname(__file__), "..", "examples", "interview_cues.json")


def load():
    with open(EXAMPLE, encoding="utf-8") as f:
        return json.load(f)


class Helpers(unittest.TestCase):
    def test_color_is_bgr(self):
        self.assertEqual(ks.ass_color("#FFC93C"), "&H003CC9FF")
        self.assertEqual(ks.inline_color("#112233"), "&H332211&")

    def test_time(self):
        self.assertEqual(ks.ass_time(3725.456), "1:02:05.46")
        self.assertEqual(ks.parse_time("01:02.5"), 62.5)
        self.assertEqual(ks.parse_time("00:00:03,200"), 3.2)

    def test_escape_blocks_override_injection(self):
        self.assertNotIn("{", ks.esc("a{\\pos(0,0)}b"))

    def test_wrap_balances_and_keeps_words(self):
        rows = ks.wrap("PRD가 합의되면 기능 명세서로 화면 단위 동작을 정의합니다 그리고 더", 14)
        self.assertEqual(len(rows), 2)
        self.assertEqual(" ".join(rows).split(), "PRD가 합의되면 기능 명세서로 화면 단위 동작을 정의합니다 그리고 더".split())


class Build(unittest.TestCase):
    def test_example_is_clean(self):
        b = ks.Builder(load())
        ass = b.build()
        self.assertEqual(b.report.errors, [])
        self.assertEqual(b.report.warnings, [])
        self.assertEqual(b.report.info["cards"], ["SSOT", "PRD", "기능 명세서", "유저 플로우"])
        self.assertIn("PlayResX: 1920", ass)
        self.assertIn("허재혁 대표", ass)

    def test_keyword_highlight_and_pulse(self):
        ass = ks.Builder(load()).build()
        line = next(l for l in ass.splitlines() if "하나에 모읍니다" in l)
        self.assertIn("\\c&H3CC9FF&", line)      # accent colour
        self.assertIn("\\fscx116", line)          # pulse
        self.assertIn("SSOT", line)

    def test_alias_matches_longest_first(self):
        cues = load()
        cues["lines"] = [{"start": 0, "end": 3, "speaker": "guest", "text": "기능명세서를 씁니다"}]
        cues["emphasis"] = []
        b = ks.Builder(cues)
        b.build()
        self.assertEqual(b.report.info["cards"], ["기능 명세서"])

    def test_card_once_per_keyword(self):
        ass = ks.Builder(load()).build()
        prd_cards = [l for l in ass.splitlines() if ",Card," in l and l.endswith("PRD")]
        self.assertEqual(len(prd_cards), 1)

    def test_cards_never_overlap_each_other_or_emphasis(self):
        cues = load()
        cues["lines"] = [{"start": 0, "end": 4, "speaker": "guest",
                          "text": "SSOT PRD 기능 명세서 유저 플로우 전부"}]
        cues["emphasis"] = [{"start": 1.0, "end": 2.0, "text": "강조"}]
        b = ks.Builder(cues)
        b.build()
        cards = sorted((e.start, e.end) for e in b.events if e.kind == "card")
        for (s1, e1), (s2, _) in zip(cards, cards[1:]):
            self.assertGreaterEqual(s2, e1)
        for s, e in cards:
            self.assertFalse(s < 2.0 and e > 1.0)
        self.assertTrue(any("cards dropped" in w for w in b.report.warnings))

    def test_validation_errors(self):
        cues = load()
        cues["lines"] = [
            {"start": 0, "end": 2, "speaker": "guest", "text": "a"},
            {"start": 1.5, "end": 1.0, "speaker": "nobody", "text": "b"},
            {"start": 1.8, "end": 3, "speaker": "nobody", "text": "c"},
        ]
        b = ks.Builder(cues)
        b.build()
        joined = " ".join(b.report.errors)
        self.assertIn("end <= start", joined)
        self.assertIn("overlaps", joined)
        self.assertIn("unknown speaker", joined)

    def test_reading_speed_and_missing_keyword_warn(self):
        cues = load()
        cues["lines"] = [{"start": 0, "end": 1, "speaker": "host",
                          "text": "아주 빠르게 지나가는 긴 문장을 일초에 다 읽으라고요"}]
        cues["emphasis"] = []
        b = ks.Builder(cues)
        b.build()
        w = " ".join(b.report.warnings)
        self.assertIn("chars/s", w)
        self.assertIn("never appears", w)

    def test_vertical_video_scales(self):
        cues = load()
        cues["video"] = {"width": 1080, "height": 1920}
        b = ks.Builder(cues)
        ass = b.build()
        self.assertIn("PlayResY: 1920", ass)
        self.assertIn(f"Caption,Noto Sans CJK KR,{round(1080*1.15*0.052)}", ass)
        self.assertEqual(b.report.errors, [])
        self.assertFalse(any("too long" in w for w in b.report.warnings))
        # long lines really break into rows on a narrow frame
        line = next(l for l in ass.splitlines() if "정의합니다" in l)
        self.assertEqual(line.count("\\N"), 2)  # speaker tag + one row break

    def test_keyword_split_across_rows_still_highlighted(self):
        cues = load()
        cues["video"] = {"width": 1080, "height": 1920}
        cues["lines"] = [{"start": 0, "end": 4, "speaker": "guest",
                          "text": "우리가 지금부터 이야기할 것은 기능 명세서 입니다"}]
        cues["emphasis"] = []
        b = ks.Builder(cues)
        b.build()
        self.assertIn("기능 명세서", b.report.info["cards"])


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
class Render(unittest.TestCase):
    def test_burns_and_frames_differ_from_source(self):
        d = tempfile.mkdtemp()
        src = os.path.join(d, "src.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                        "color=c=0x223344:s=640x360:d=9", "-pix_fmt", "yuv420p", src],
                       check=True)
        cues = load()
        cues["video"] = {"width": 640, "height": 360}
        cues["lines"] = cues["lines"][:3]
        cues["emphasis"] = []
        cj = os.path.join(d, "c.json")
        with open(cj, "w", encoding="utf-8") as f:
            json.dump(cues, f, ensure_ascii=False)
        out = os.path.join(d, "out.mp4")
        rc = ks.main([cj, "-o", os.path.join(d, "c.ass"), "--render", src, out,
                      "--frames", os.path.join(d, "f")])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.getsize(out) > 0)
        frames = sorted(os.listdir(os.path.join(d, "f")))
        self.assertTrue(frames)
        # a frame with a card must not be the flat background colour
        blank = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", "5.5", "-i", src,
                                "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                               capture_output=True, check=True).stdout
        burnt = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", "5.5", "-i", out,
                                "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                               capture_output=True, check=True).stdout
        changed = sum(1 for a, b in zip(blank, burnt) if abs(a - b) > 40)
        self.assertGreater(changed, 2000)
        shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
