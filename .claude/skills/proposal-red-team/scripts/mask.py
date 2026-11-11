#!/usr/bin/env python3
"""Pseudonymize a work folder before any text reaches the LLM, and restore the final reports.

Usage:
    python3 mask.py <workdir> --customer "한빛은행" [--alias "한빛,HB은행"] [--terms "홍길동,프로젝트X"]
    python3 mask.py <workdir> --restore          # after report.py: put real names back into 0*_*.md/.xlsx

What is masked (consistently, same value -> same token):
    customer name + aliases      -> [CUSTOMER]
    other financial institutions -> [ORG-01], [ORG-02] ...
    money amounts (억원/만원/원)   -> [AMT-01] ...
    e-mail, phone numbers        -> [EMAIL-01], [PHONE-01]
    extra --terms (people, project code names, product names) -> [TERM-01] ...

Files rewritten in place inside the work folder (originals are never touched):
    docmodel.json, gm_outline.md, units/**/*.md, cross_check.json/.md, rfp_requirements.json/.md
The mapping is stored in <workdir>/_vault/mask_map.json — that folder must never be read into the
conversation or sent anywhere; only --restore reads it, locally.

Limits: rendered PNGs still contain the real text. In mask mode, either skip image-based visual review
or accept that slide images are seen by the model (render.py writes them to renders/).
Numbers other than money (인력, 일정, RTO ...) are NOT masked — the review needs them to judge consistency.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cross_check import FIN  # noqa: E402

AMT = re.compile(r"\d[\d,]*(?:\.\d+)?\s?(?:조|억)\s?(?:\d[\d,]*\s?만)?\s?원?|\d[\d,]*(?:\.\d+)?\s?천\s?만?\s?원|\d[\d,]*(?:\.\d+)?\s?만?\s?원|\d[\d,]*(?:\.\d+)?\s?만\s?원")
SUFFIXES = ("금융지주", "은행", "생명", "화재", "손해보험", "손보", "증권", "투자증권", "카드", "캐피탈", "저축은행", "금융")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\d)(?:0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4})(?!\d)")
TEXT_FILES = ["docmodel.json", "gm_outline.md", "cross_check.json", "cross_check.md",
              "rfp_requirements.json", "rfp_requirements.md", "manifest.json", "render_report.json"]


class Masker:
    def __init__(self, customer: list[str], terms: list[str]):
        self.fwd: dict[str, str] = {}
        self.counters: dict[str, int] = {}
        names = {c.strip() for c in customer if c and c.strip()}
        for c in list(names):  # "한빛은행" -> also "한빛" (catches line-wrapped "한빛은 / 행")
            for suf in SUFFIXES:
                if c.endswith(suf) and len(c) - len(suf) >= 2:
                    names.add(c[: -len(suf)])
        self.customer = sorted(names, key=len, reverse=True)
        self.terms = sorted({t for t in terms if t}, key=len, reverse=True)

    def token(self, kind: str, value: str) -> str:
        if value not in self.fwd:
            self.counters[kind] = self.counters.get(kind, 0) + 1
            self.fwd[value] = f"[{kind}-{self.counters[kind]:02d}]"
        return self.fwd[value]

    def mask(self, s: str) -> str:
        for c in self.customer:
            s = re.sub(r"\s?".join(map(re.escape, c.replace(" ", ""))), "[CUSTOMER]", s)
            self.fwd.setdefault(c, "[CUSTOMER]")
        for name in sorted(FIN, key=len, reverse=True):
            if name in s and not any(name in c or c in name for c in self.customer):
                s = s.replace(name, self.token("ORG", name))
        for t in self.terms:
            if t in s:
                s = s.replace(t, self.token("TERM", t))
        s = EMAIL.sub(lambda m: self.token("EMAIL", m.group(0)), s)
        s = PHONE.sub(lambda m: self.token("PHONE", m.group(0)), s)
        s = AMT.sub(lambda m: self.token("AMT", m.group(0).strip()), s)
        return s


def walk_json(obj, fn):
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, list):
        return [walk_json(x, fn) for x in obj]
    if isinstance(obj, dict):
        return {k: walk_json(v, fn) for k, v in obj.items()}
    return obj


def do_mask(wd: Path, m: Masker):
    vault = wd / "_vault"
    if (vault / "mask_map.json").exists():
        sys.exit("already masked (_vault/mask_map.json exists)")
    changed = 0
    for name in TEXT_FILES:
        p = wd / name
        if not p.exists():
            continue
        if p.suffix == ".json":
            data = json.loads(p.read_text(encoding="utf-8"))
            if name == "manifest.json":  # keep real paths (scripts need them); mask display names
                for f in data.get("files", []):
                    f["name"] = m.mask(f.get("name", ""))
                    f["role_reason"] = m.mask(f.get("role_reason", ""))
            else:
                data = walk_json(data, m.mask)
            p.write_text(json.dumps(data, ensure_ascii=False, indent=None if name == "docmodel.json" else 1), encoding="utf-8")
        else:
            p.write_text(m.mask(p.read_text(encoding="utf-8")), encoding="utf-8")
        changed += 1
    for p in (wd / "units").rglob("*.md"):
        p.write_text(m.mask(p.read_text(encoding="utf-8")), encoding="utf-8")
        changed += 1
    vault.mkdir(exist_ok=True)
    rev = {}
    for k, v in m.fwd.items():
        rev.setdefault(v, k)
    (vault / "mask_map.json").write_text(json.dumps({"forward": m.fwd, "reverse": rev}, ensure_ascii=False, indent=1), encoding="utf-8")
    (vault / "README.txt").write_text("LOCAL ONLY. Do not read into an AI conversation, upload, or commit.\n", encoding="utf-8")
    summary = {}
    for v in m.fwd.values():
        kind = v.strip("[]").split("-")[0]
        summary[kind] = summary.get(kind, 0) + 1
    print(json.dumps({"masked_files": changed, "tokens": summary,
                      "note": "renders/*.png still contain real text"}, ensure_ascii=False))


def do_restore(wd: Path):
    rev = json.loads((wd / "_vault" / "mask_map.json").read_text(encoding="utf-8"))["reverse"]
    keys = sorted(rev, key=len, reverse=True)

    def restore(s: str) -> str:
        for k in keys:
            s = s.replace(k, rev[k])
        return s

    out = []
    for p in sorted(wd.glob("0*_*.md")) + [wd / "guard_report.md"]:
        if p.exists():
            p.write_text(restore(p.read_text(encoding="utf-8")), encoding="utf-8")
            out.append(p.name)
    for p in wd.glob("0*_*.xlsx"):
        from openpyxl import load_workbook
        wb = load_workbook(p)
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for c in row:
                    if isinstance(c.value, str):
                        c.value = restore(c.value)
        wb.save(p)
        out.append(p.name)
    print(json.dumps({"restored": out}, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workdir")
    ap.add_argument("--customer", default="")
    ap.add_argument("--alias", default="")
    ap.add_argument("--terms", default="", help="extra sensitive strings (people, code names), comma separated")
    ap.add_argument("--restore", action="store_true")
    a = ap.parse_args()
    wd = Path(a.workdir).resolve()
    if a.restore:
        do_restore(wd)
    else:
        if not a.customer:
            sys.exit("--customer is required for masking")
        do_mask(wd, Masker([a.customer] + a.alias.split(","), a.terms.split(",")))


if __name__ == "__main__":
    main()
