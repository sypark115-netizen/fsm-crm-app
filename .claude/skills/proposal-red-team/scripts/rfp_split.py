#!/usr/bin/env python3
"""Split an RFP into requirement candidates and evaluation-criteria pages.

Usage:
    python3 rfp_split.py <workdir> [--file F1]

Uses the units from ingest.py for the file(s) whose role_guess is "rfp" (or --file).
Writes <workdir>/rfp_requirements.json and rfp_requirements.md:

  requirements[]  {req_id, id_source, category, text, uid, mandatory}
  criteria_pages  units that look like 평가기준/배점표 (read these yourself)
  writing_rules   lines about 제안서 작성지침 (page limits, 목차, 서식) — violations are 감점

Two strategies, merged:
  1. Explicit IDs used in Korean public/financial RFPs (SFR-001, PER-002, SER-...)
     — the block until the next ID is one requirement.
  2. Obligation sentences without IDs ("~하여야 한다", "~할 것", "~제시", "필수") — one line each,
     auto-numbered R-###.
This is recall-oriented: the model reviews and merges/drops candidates.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ID_CATS = {
    "SFR": "기능", "FUR": "기능", "PER": "성능", "SIR": "인터페이스", "INR": "인터페이스", "DAR": "데이터",
    "TER": "테스트", "SER": "보안", "QUR": "품질", "COR": "제약", "PMR": "프로젝트관리", "PSR": "프로젝트지원",
    "ECR": "장비구성", "SWR": "SW", "HWR": "HW", "NER": "네트워크", "OPR": "운영", "MAR": "유지관리",
    "REQ": "요구사항", "TR": "기술", "MR": "관리", "SR": "보안/서비스",
}
ID_RE = re.compile(r"\b(" + "|".join(sorted(ID_CATS, key=len, reverse=True)) + r")[-_ ]?(\d{2,4})(?:[-_](\d{1,3}))?\b")
OBLIG = re.compile(
    r"(하여야\s?(?:한다|함|하며)|해야\s?(?:한다|함|하며)|할\s?것|하도록\s?(?:한다|할 것)|제시(?:할 것|하여야|해야|하시오)|"
    r"기술(?:할 것|하시오)|포함(?:할 것|하여야|되어야)|준수(?:할 것|하여야|해야)|제출(?:할 것|하여야)|"
    r"필수|반드시|의무|제안하시오|바람\.?$|요망)")
MANDATORY = re.compile(r"(필수|반드시|의무|하여야|해야|준수|할\s?것)")
CRITERIA = re.compile(r"(평가\s?항목|평가\s?요소|평가\s?기준|배점|정량\s?평가|정성\s?평가|기술\s?평가|세부\s?평가)")
WRITING = re.compile(r"(제안서\s?작성|작성\s?지침|작성\s?요령|페이지|매\s?이내|쪽\s?이내|분량|목차|글자\s?크기|폰트|서식|A4|발표\s?시간|분\s?이내)")
CAT_HINTS = [("보안", "보안"), ("개인정보", "보안"), ("DR", "DR/BCP"), ("재해", "DR/BCP"), ("백업", "DR/BCP"),
             ("성능", "성능"), ("응답", "성능"), ("가용", "성능"), ("인력", "프로젝트관리"), ("PM", "프로젝트관리"),
             ("일정", "프로젝트관리"), ("교육", "프로젝트지원"), ("유지", "운영"), ("운영", "운영"), ("장애", "운영"),
             ("데이터", "데이터"), ("연계", "인터페이스"), ("테스트", "테스트"), ("품질", "품질"), ("클라우드", "인프라"),
             ("네트워크", "네트워크"), ("회선", "네트워크"), ("서버", "인프라"), ("이관", "이관/전환"), ("전환", "이관/전환")]


def unit_lines(u):
    if u.get("lines"):
        return [l["t"] for l in u["lines"]]
    lines = []
    for b in u.get("blocks", []):
        lines += b.get("text", "").splitlines()
    for t in u.get("tables", []):
        lines += [" | ".join(r) for r in t]
    return [l.strip() for l in lines if l.strip()]


def guess_cat(text):
    for k, c in CAT_HINTS:
        if k in text:
            return c
    return "기타"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workdir")
    ap.add_argument("--file", help="file id of the RFP (default: every file with role_guess=rfp)")
    args = ap.parse_args()
    wd = Path(args.workdir).resolve()
    manifest = json.loads((wd / "manifest.json").read_text(encoding="utf-8"))["files"]
    fids = [args.file] if args.file else [m["file_id"] for m in manifest if m.get("role_guess") == "rfp"]
    if not fids:
        raise SystemExit("no RFP file found — pass --file F# (see manifest.json)")
    units = [u for u in json.loads((wd / "docmodel.json").read_text(encoding="utf-8"))["units"] if u["file_id"] in fids]

    reqs, criteria, writing = [], [], []
    cur = None
    auto = 0
    for u in units:
        lines = unit_lines(u)
        joined = "\n".join(lines)
        if len(CRITERIA.findall(joined)) >= 2:
            criteria.append({"uid": u["uid"], "gm": u.get("gm"), "preview": joined[:300]})
        for line in lines:
            if WRITING.search(line) and OBLIG.search(line):
                writing.append({"uid": u["uid"], "text": line})
            m = ID_RE.search(line)
            if m:
                rid = f"{m.group(1)}-{m.group(2)}" + (f"-{m.group(3)}" if m.group(3) else "")
                if cur and cur["req_id"] == rid:
                    continue
                cur = {"req_id": rid, "id_source": "rfp", "category": ID_CATS.get(m.group(1), "기타"),
                       "text": line[m.end():].strip(" :|-"), "uid": u["uid"], "mandatory": False}
                reqs.append(cur)
                continue
            if cur and cur["id_source"] == "rfp" and (re.match(r"^(?:[IVX]+|\d{1,2})[.)]\s*\S", line) or CRITERIA.search(line)):
                cur = None  # a new heading / criteria table ends the requirement block
            if cur and cur["id_source"] == "rfp" and len(cur["text"]) < 1500:
                cur["text"] += " " + line
                continue
            if OBLIG.search(line) and len(line) >= 12:
                auto += 1
                reqs.append({"req_id": f"R-{auto:03d}", "id_source": "auto", "category": guess_cat(line),
                             "text": line, "uid": u["uid"], "mandatory": False})
        cur = cur if cur and cur["id_source"] == "rfp" else None
    for r in reqs:
        r["text"] = re.sub(r"\s+", " ", r["text"]).strip()
        r["mandatory"] = bool(MANDATORY.search(r["text"]))
        if r["id_source"] == "auto" and WRITING.search(r["text"]):
            r["category"] = "작성지침"
        elif r["category"] == "기타":
            r["category"] = guess_cat(r["text"])
    # dedupe identical auto texts
    seen, uniq = set(), []
    for r in reqs:
        k = r["text"][:120]
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)

    res = {"rfp_files": fids, "requirements": uniq, "criteria_pages": criteria, "writing_rules": writing}
    (wd / "rfp_requirements.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    md = [f"# RFP 요구사항 후보 ({len(uniq)}건, ID 명시 {sum(r['id_source']=='rfp' for r in uniq)}건)\n",
          "> 후보 목록이다. 병합·삭제·누락 보완 후 Compliance 판정에 사용한다.\n",
          f"## 평가기준/배점 페이지 후보: {', '.join(c['uid'] for c in criteria) or '없음 — RFP 본문 또는 별첨 확인 필요'}\n",
          f"## 제안서 작성지침 ({len(writing)})"]
    md += [f"- {w['uid']}: {w['text']}" for w in writing[:40]]
    md.append("\n## 요구사항\n| ID | 분류 | 필수 | 위치 | 내용 |\n|---|---|---|---|---|")
    for r in uniq:
        md.append(f"| {r['req_id']} | {r['category']} | {'●' if r['mandatory'] else ''} | {r['uid']} | {r['text'][:180].replace('|','/')} |")
    (wd / "rfp_requirements.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"requirements": len(uniq), "with_rfp_id": sum(r['id_source'] == 'rfp' for r in uniq),
                      "criteria_pages": [c["uid"] for c in criteria], "writing_rules": len(writing)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
