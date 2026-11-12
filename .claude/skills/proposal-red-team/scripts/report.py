#!/usr/bin/env python3
"""Render findings.json into the Red Team reports, with hallucination guards.

Usage:
    python3 report.py <workdir> [--findings findings.json]

Inputs : <workdir>/findings.json (schema: references/output-templates.md), docmodel.json
Outputs: 01_executive.md, 02_slide_review.md, 03_rfp_compliance.md/.xlsx (if compliance rows),
         04_evidence_ledger.md, guard_report.md

Guards (deterministic):
  * revised / recommendation text containing a number, % or a financial-institution name that
    does not appear anywhere in the source documents gets "[VERIFY: 원문에 없는 …]" appended.
  * evidence ledger rows without evidence_loc are downgraded to UNSUBSTANTIATED.
  * findings without a location or with an unknown severity are listed as schema errors.
Exit code 2 when schema errors exist (fix findings.json and re-run).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cross_check import FIN, unit_texts  # noqa: E402

SEV_ORDER = ["MUST FIX", "SHOULD FIX", "ENHANCEMENT", "PASS"]
HYGIENE_CATS = {"hygiene", "오탈자", "맞춤법", "띄어쓰기", "용어", "문장", "typo"}
NUM_IN_TEXT = re.compile(r"\d[\d,\.]*\s?(?:%|억|만|원|명|개월|년|주|일|시간|분|초|건|곳|대|개|배|TB|PB|Gbps|ms|MM|M/M|x|X)?")
UNIT_REF = re.compile(r"(?:F\d+#)?[SP]\d{3}(?:~[SP]?\d{3})?|RT-\d+|[가-나]-\d+[a-z]?|[A-Z]{2,4}-\d{2,4}")
PLACEHOLDER = re.compile(r"\[(?:VERIFY|EVIDENCE REQUIRED)[^\]]*\]")


def esc(s) -> str:
    return ("" if s is None else str(s)).replace("|", "/").replace("\n", "<br>")


def source_corpus(wd: Path) -> str:
    dm = json.loads((wd / "docmodel.json").read_text(encoding="utf-8"))["units"]
    return "\n".join(t for _, t in unit_texts(dm))


def guard_text(text: str, corpus_flat: str, corpus_nums: set[str]) -> tuple[str, list[str]]:
    if not text:
        return text, []
    body = PLACEHOLDER.sub("", text)
    body = UNIT_REF.sub("", body)  # slide/page ids (S007, F1#P022, RT-03, 가-10) are not facts
    issues = []
    for m in NUM_IN_TEXT.finditer(body):
        raw = m.group(0).strip()
        digits = re.sub(r"[^\d.]", "", raw.replace(",", ""))
        if not digits or len(digits.strip(".")) == 0:
            continue
        if len(digits) == 1 and not re.search(r"[%억만원명개월년]", raw):
            continue  # "3가지", "1단계" style counters
        if digits not in corpus_nums:
            issues.append(f"원문에 없는 수치 '{raw}'")
    flat = body.replace(" ", "")
    for name in FIN:
        if name in flat and name not in corpus_flat:
            issues.append(f"원문에 없는 금융사명 '{name}'")
    issues = sorted(set(issues))
    if issues and "[VERIFY: 원문에 없는" not in text:
        text = text + " " + " ".join(f"[VERIFY: {i}]" for i in issues)
    return text, issues


def table(rows: list[list], header: list[str]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


SEV_FILL = {"MUST FIX": "F8CBAD", "SHOULD FIX": "FFE699", "ENHANCEMENT": "DDEBF7", "PASS": "C6EFCE",
            "MISSING": "F8CBAD", "CONFLICT": "F8CBAD", "PARTIAL": "FFE699", "HARD TO FIND": "FFE699", "COMPLIANT": "C6EFCE",
            "UNSUBSTANTIATED": "F8CBAD", "WEAK": "FFE699", "VERIFY": "FFE699", "SUPPORTED": "C6EFCE"}


def write_workbook(wd: Path, meta, ex, findings, comp, ledger, count):
    """One Excel file the proposal team can filter, assign and track: 요약 / 검토의견 / 장표별 / RFP 대응 / Evidence / 제출위생."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    wb = Workbook()

    def sheet(title, head, rows, widths, color_col=None, first=False, track=False):
        ws = wb.active if first else wb.create_sheet()
        ws.title = title
        if track:
            head = head + ["담당자", "조치 상태", "조치 내용"]
            widths = widths + [10, 11, 30]
        ws.append(head)
        for r in rows:
            ws.append([("" if v is None else str(v)) for v in r] + ([""] * 3 if track else []))
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1F3864")
            c.alignment = Alignment(wrap_text=True, vertical="center")
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
            if color_col is not None:
                v = str(row[color_col].value or "")
                for k, col in SEV_FILL.items():
                    if v.startswith(k):
                        row[color_col].fill = PatternFill("solid", fgColor=col)
                        break
        for i, w in enumerate(widths):
            ws.column_dimensions[chr(65 + i) if i < 26 else "A" + chr(65 + i - 26)].width = w
        ws.freeze_panes = "B2"
        if ws.max_row > 1:
            ws.auto_filter.ref = ws.dimensions
        if track and ws.max_row > 1:
            col = chr(65 + len(head) - 2)
            dv = DataValidation(type="list", formula1='"미착수,진행중,완료,보류(사유)"', allow_blank=True)
            ws.add_data_validation(dv)
            dv.add(f"{col}2:{col}{ws.max_row}")
        return ws

    # 요약
    rows = [["고객사", meta.get("customer", "")], ["대상", meta.get("title", "")], ["Mode", meta.get("mode", "")],
            ["Domain", meta.get("domains", "")], ["검토일", meta.get("date", "")],
            ["판정 집계", " · ".join(f"{k} {v}" for k, v in count.items())],
            ["Overall Assessment", ex.get("overall_assessment", "")]]
    rows += [[f"평가위원 여정 — {k}", v] for k, v in (ex.get("evaluator_journey") or {}).items()]
    for i, t in enumerate(ex.get("top5", []), 1):
        rows.append([f"Top {i}. {t.get('title','')}", f"[위치] {', '.join(t.get('where', []))}\n[영향] {t.get('why','')}\n[수정] {t.get('fix','')}"])
    rows += [["What Works Well", w] for w in ex.get("what_works_well", [])]
    mt = ex.get("memory_test")
    if mt:
        rows.append(["Memory Test", f"기억될 것: {' / '.join(mt.get('remembered', []))}\n의도: {' / '.join(mt.get('intended', []))}\n일치: {mt.get('match','')}\n원인: {mt.get('gap_cause','')}"])
    rows += [[f"전제(ASSUMED)", a] for a in meta.get("assumptions", [])]
    sheet("요약", ["항목", "내용"], rows, [34, 120], first=True)

    # 검토의견 (one row per finding, trackable)
    head = ["ID", "위치", "Severity", "Category", "Flags", "현재 문구", "문제", "왜 중요한가", "권고", "수정 문구(안)",
            "Why KT", "Evidence", "How", "Visual 권고", "평가위원 시각"]
    rows = []
    for f in findings:
        tri = f.get("triangle") or {}
        rows.append([f.get("id"), f.get("location"), f.get("severity"), f.get("category"), ", ".join(f.get("flags", [])),
                     f.get("current"), f.get("issue"), f.get("why_it_matters"), f.get("recommendation"), f.get("revised"),
                     tri.get("why_kt"), tri.get("evidence"), tri.get("how"), f.get("visual"), f.get("evaluator")])
    sheet("검토의견", head, rows, [8, 16, 12, 14, 18, 36, 44, 34, 40, 40, 18, 22, 22, 30, 26], color_col=2, track=True)

    # 장표별 (every slide/page of the reviewed deck, with its GM and the findings that touch it)
    try:
        units = json.loads((wd / "docmodel.json").read_text(encoding="utf-8"))["units"]
        roles = {m["file_id"]: m.get("role_guess") for m in json.loads((wd / "manifest.json").read_text(encoding="utf-8"))["files"]}
    except Exception:
        units, roles = [], {}
    order = {s: i for i, s in enumerate(SEV_ORDER)}
    rows = []
    for u in units:
        if roles.get(u["file_id"]) not in ("presentation", "proposal"):
            continue
        short = u["uid"].split("#")[1]
        hits = [f for f in findings if u["uid"] in str(f.get("location", "")) or re.search(rf"(?<![0-9]){short}(?![0-9])", str(f.get("location", "")))]
        worst = min((f.get("severity") for f in hits if f.get("severity") in order), key=lambda s: order[s], default="")
        rows.append([u["uid"], u.get("gm") or "", worst, ", ".join(f.get("id", "") for f in hits),
                     " / ".join(str(f.get("issue", ""))[:80] for f in hits if f.get("severity") != "PASS")])
    if rows:
        sheet("장표별", ["장표", "Governing / Key Message", "최고 Severity", "관련 의견 ID", "주요 문제(요약)"], rows,
              [12, 60, 13, 16, 80], color_col=2, track=True)

    if comp:
        cols = ["req_id", "requirement", "req_loc", "criteria", "response", "response_loc", "evidence", "status", "findability", "risk", "recommendation"]
        sheet("RFP 대응", ["REQ", "RFP 요구사항", "RFP 위치", "평가항목", "제안 대응", "제안 위치", "Evidence", "Status", "Findability", "Risk", "권고"],
              [[c.get(k, "") for k in cols] for c in comp], [9, 46, 11, 14, 40, 16, 18, 13, 11, 26, 30], color_col=7, track=True)
    if ledger:
        sheet("Evidence 대장", ["주장", "주장 위치", "Evidence 유형", "Evidence", "Evidence 위치", "Status"],
              [[r.get("claim"), r.get("claim_loc"), r.get("type"), r.get("evidence"), r.get("evidence_loc"), r.get("status")] for r in ledger],
              [46, 12, 16, 40, 14, 16], color_col=5)

    cc = wd / "cross_check.json"
    if cc.exists():
        h = json.loads(cc.read_text(encoding="utf-8")).get("submission_hygiene") or {}
        rows = [["슬라이드 밖 개체", o["uid"], o["text"], "제출본에서 삭제"] for o in h.get("off_slide_text", [])]
        rows += [["보이는 작업메모", o["uid"], o["context"], "삭제"] for o in h.get("visible_work_notes", [])]
        rows += [["노트", o["uid"], f"{o['chars']}자 " + ", ".join(o.get("work_notes", [])), "제출본에서 노트 삭제"] for o in h.get("speaker_notes", [])]
        rows += [["주의 표현", o["uid"], o["context"], f"'{o['hit']}' — RFP 작성지침 확인"] for o in h.get("risky_wording", [])]
        if rows:
            sheet("제출위생", ["유형", "위치", "내용", "조치"], rows, [16, 12, 70, 30], track=True)

    wb.save(wd / "00_redteam_review.xlsx")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workdir")
    ap.add_argument("--findings", default="findings.json")
    args = ap.parse_args()
    wd = Path(args.workdir).resolve()
    F = json.loads((wd / args.findings).read_text(encoding="utf-8"))

    corpus = source_corpus(wd)
    corpus_flat = corpus.replace(" ", "")
    corpus_nums = {re.sub(r"[^\d.]", "", n.replace(",", "")) for n in re.findall(r"\d[\d,\.]*", corpus)}
    corpus_nums |= {n[:-2] for n in corpus_nums if n.endswith(".0")}

    meta = F.get("meta", {})
    ex = F.get("executive", {})
    findings = F.get("findings", [])
    ledger = F.get("evidence_ledger", [])
    comp = F.get("compliance", [])
    errors, guard_log = [], []

    for f in findings:
        if f.get("severity") not in SEV_ORDER:
            errors.append(f"{f.get('id')}: unknown severity {f.get('severity')!r}")
        if not f.get("location"):
            errors.append(f"{f.get('id')}: missing location")
        for key in ("revised", "recommendation"):
            new, iss = guard_text(f.get(key, ""), corpus_flat, corpus_nums)
            if iss:
                guard_log.append(f"- {f.get('id')} ({key}): " + "; ".join(iss))
                f[key] = new
    for t in ex.get("top5", []):
        new, iss = guard_text(t.get("fix", ""), corpus_flat, corpus_nums)
        if iss:
            guard_log.append(f"- Top5 '{t.get('title')}' (fix): " + "; ".join(iss))
            t["fix"] = new
    for row in ledger:
        if not row.get("evidence_loc") and row.get("status") not in ("UNSUBSTANTIATED", "EVIDENCE REQUIRED"):
            guard_log.append(f"- ledger '{row.get('claim','')[:40]}': evidence_loc 없음 → UNSUBSTANTIATED")
            row["status"] = "UNSUBSTANTIATED"

    def sev_key(f):
        return (SEV_ORDER.index(f["severity"]) if f.get("severity") in SEV_ORDER else 9, str(f.get("location")))

    def is_hyg(f):
        return str(f.get("category", "")).lower() in HYGIENE_CATS

    core = sorted([f for f in findings if not is_hyg(f)], key=sev_key)
    hyg = sorted([f for f in findings if is_hyg(f)], key=sev_key)
    count = {s: sum(1 for f in findings if f.get("severity") == s) for s in SEV_ORDER}

    # ---------------- 01 executive
    e = [f"# 01 Executive Red Team — {meta.get('customer','(고객사 미지정)')} · {meta.get('title','')}",
         f"\n> Mode: {meta.get('mode','')} · Domain: {meta.get('domains','')} · 검토일: {meta.get('date','')} · 대상: {', '.join(meta.get('files', []))}",
         f"> MUST FIX {count['MUST FIX']} · SHOULD FIX {count['SHOULD FIX']} · ENHANCEMENT {count['ENHANCEMENT']} · PASS {count['PASS']}"]
    if meta.get("assumptions"):
        e.append("> ASSUMED: " + "; ".join(meta["assumptions"]))
    e.append("\n## Overall Assessment\n")
    e.append(ex.get("overall_assessment", "(작성 필요)"))
    if ex.get("evaluator_journey"):
        e.append("\n**평가위원 여정 (SEE → UNDERSTAND → BELIEVE → TRUST → REMEMBER)**\n")
        e.append(table([[k, v] for k, v in ex["evaluator_journey"].items()], ["단계", "판정"]))
    e.append("\n## Top 5 Winning Issues\n")
    for i, t in enumerate(ex.get("top5", []), 1):
        e.append(f"### {i}. {t.get('title','')}\n- **위치**: {', '.join(t.get('where', []))}\n- **왜 수주에 영향을 주는가**: {t.get('why','')}\n- **어떻게 고치나**: {t.get('fix','')}\n")
    for sev in ("MUST FIX", "SHOULD FIX"):
        rows = [[f.get("id"), f.get("location"), f.get("category"), f.get("issue")] for f in core if f.get("severity") == sev]
        e.append(f"\n## {sev} ({len(rows)})\n")
        e.append(table(rows, ["ID", "위치", "Category", "Issue"]) if rows else "_없음_")
    e.append("\n## What Works Well\n")
    e += [f"- {w}" for w in ex.get("what_works_well", [])] or ["_(작성 필요)_"]
    mt = ex.get("memory_test")
    if mt:
        e.append("\n## Memory Test — 발표 10분 후 평가위원이 기억할 3가지\n")
        e.append(table([[i + 1, r, (mt.get("intended") or ["", "", ""])[i] if i < len(mt.get("intended") or []) else ""]
                        for i, r in enumerate(mt.get("remembered", []))], ["#", "실제로 기억될 것 (자료 기준)", "의도한 Win Theme"]))
        e.append(f"\n- **일치 여부**: {mt.get('match','')}\n- **불일치 원인**: {mt.get('gap_cause','')}")
    sl = ex.get("storyline")
    if sl:
        e.append("\n## Governing Message Storyline\n")
        e.append(table([[s.get("id"), s.get("gm"), s.get("flag", "")] for s in sl], ["Unit", "Governing Message", "Flag"]))
    sq = ex.get("success_questions")
    if sq:
        e.append("\n## Success Questions\n")
        e.append(table([[k, v] for k, v in sq.items()], ["질문", "답"]))
    if hyg:
        e.append(f"\n## Hygiene\n오탈자·표기 {len(hyg)}건은 `02_slide_review.md` 맨 뒤 Hygiene 섹션 참조.")
    (wd / "01_executive.md").write_text("\n".join(e) + "\n", encoding="utf-8")

    # ---------------- 02 slide review
    s = ["# 02 Slide-by-Slide Review\n", "> 순서: Severity → 위치. Hygiene(오탈자·표기)는 맨 뒤.\n"]
    for f in core:
        tri = f.get("triangle") or {}
        s.append(f"## {f.get('id')} · {f.get('location')} · **{f.get('severity')}** · {f.get('category')}")
        if f.get("flags"):
            s.append("`" + "` `".join(f["flags"]) + "`")
        s.append(table([
            ["Current Message", f.get("current")], ["Issue", f.get("issue")], ["Why It Matters", f.get("why_it_matters")],
            ["Recommendation", f.get("recommendation")], ["Revised Message", f.get("revised")],
            ["Why KT", tri.get("why_kt")], ["Evidence", tri.get("evidence")], ["How", tri.get("how")],
            ["Visual Recommendation", f.get("visual")], ["Evaluator Perspective", f.get("evaluator")],
        ], ["항목", "내용"]) + "\n")
    if hyg:
        s.append("\n# Hygiene (오탈자·맞춤법·표기)\n")
        s.append(table([[f.get("id"), f.get("location"), f.get("severity"), f.get("current"), f.get("revised") or f.get("recommendation")] for f in hyg],
                       ["ID", "위치", "Severity", "현재", "수정"]))
    (wd / "02_slide_review.md").write_text("\n".join(s) + "\n", encoding="utf-8")

    # ---------------- 03 compliance
    if comp:
        cols = ["req_id", "requirement", "criteria", "response", "response_loc", "evidence", "status", "findability", "risk", "recommendation"]
        head = ["REQ", "RFP Requirement", "Evaluation Criteria", "Proposal Response", "Slide/Page", "Evidence", "Status", "Findability", "Risk", "Recommendation"]
        rows = [[c.get(k, "") for k in cols] for c in comp]
        st = {}
        for c in comp:
            st[c.get("status")] = st.get(c.get("status"), 0) + 1
        md = ["# 03 RFP Compliance\n", "> 상태 집계: " + " · ".join(f"{k} {v}" for k, v in st.items()) + "\n", table(rows, head)]
        (wd / "03_rfp_compliance.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Font, PatternFill
            wb = Workbook()
            ws = wb.active
            ws.title = "Compliance"
            ws.append(head)
            for r in rows:
                ws.append([("" if v is None else str(v)) for v in r])
            fills = {"MISSING": "F8CBAD", "CONFLICT": "F8CBAD", "PARTIAL": "FFE699", "HARD TO FIND": "FFE699", "COMPLIANT": "C6EFCE"}
            for c in ws[1]:
                c.font = Font(bold=True, color="FFFFFF")
                c.fill = PatternFill("solid", fgColor="1F3864")
            for row in ws.iter_rows(min_row=2):
                for c in row:
                    c.alignment = Alignment(wrap_text=True, vertical="top")
                color = fills.get(row[6].value)
                if color:
                    row[6].fill = PatternFill("solid", fgColor=color)
            for col, w in zip("ABCDEFGHIJ", [10, 50, 20, 45, 12, 30, 13, 13, 30, 40]):
                ws.column_dimensions[col].width = w
            ws.freeze_panes = "B2"
            ws.auto_filter.ref = ws.dimensions
            wb.save(wd / "03_rfp_compliance.xlsx")
        except Exception as ex_:  # markdown still exists
            guard_log.append(f"- xlsx 생성 실패: {ex_}")

    # ---------------- 04 ledger
    if ledger:
        lrows = [[r.get("claim"), r.get("claim_loc"), r.get("type"), r.get("evidence"), r.get("evidence_loc"), r.get("status")] for r in ledger]
        (wd / "04_evidence_ledger.md").write_text(
            "# 04 Evidence Ledger\n\n> 출처(evidence_loc) 없는 Evidence는 자동으로 UNSUBSTANTIATED.\n\n"
            + table(lrows, ["Claim", "Claim 위치", "Evidence 유형", "Evidence", "Evidence 위치", "Status"]) + "\n", encoding="utf-8")

    # ---------------- 00 review workbook (all opinions in one Excel file)
    try:
        write_workbook(wd, meta, ex, core + hyg, comp, ledger, count)
    except Exception as ex_:
        guard_log.append(f"- 00_redteam_review.xlsx 생성 실패: {ex_}")

    g = ["# Guard Report\n"]
    g.append("## Schema errors\n" + ("\n".join(f"- {x}" for x in errors) if errors else "- 없음"))
    g.append("\n## Hallucination guard\n" + ("\n".join(guard_log) if guard_log else "- 없음"))
    (wd / "guard_report.md").write_text("\n".join(g) + "\n", encoding="utf-8")

    out = {"counts": count, "hygiene": len(hyg), "compliance_rows": len(comp), "ledger_rows": len(ledger),
           "schema_errors": len(errors), "guard_flags": len(guard_log),
           "files": sorted(p.name for p in wd.glob("0*_*.*")) + ["guard_report.md"]}
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(2 if errors else 0)


if __name__ == "__main__":
    main()
