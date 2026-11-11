# -*- coding: utf-8 -*-
"""Review Excel 생성 (Human Approval Interface).

입력 : analysis.json + recommendations.json (Claude가 채운 재작성안)
출력 : <프로젝트명>_KeyMessage_Review.xlsx
  1. Executive Summary
  2. Message Map        — Governing Message만 읽어도 Story가 이해되는지
  3. Message Review     — ★ 사람이 판단하는 시트 (Decision / Human Final / Comment)
  4. Source Trace       — 고객 요구사항 ↔ 메시지 ↔ Evidence (자료가 있을 때)
  5. Guide              — Status / Decision 규칙
  _meta (숨김)          — APPLY 용 메타데이터

이 단계에서 Fact Guard와 재진단(AI Recommended를 엔진으로 다시 평가)을 수행해 QA Check 컬럼에 남긴다.

사용:
  python create_review_excel.py work/analysis.json work/recommendations.json -o out/ --project 한빛제조_AX
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_messages import assess  # noqa: E402
from km_common import DECISIONS, SCHEMA_VERSION, cmp_key, fact_guard, load_json, norm_text  # noqa: E402

from openpyxl import Workbook  # noqa: E402
from openpyxl.formatting.rule import FormulaRule  # noqa: E402
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402
from openpyxl.worksheet.datavalidation import DataValidation  # noqa: E402

NAVY = "1F3864"
HUMAN = "C55A11"
STATUS_FILL = {"GREEN": "C6EFCE", "YELLOW": "FFEB9C", "RED": "FFC7CE", "ESCALATE": "D9D2E9"}
STATUS_FONT = {"GREEN": "006100", "YELLOW": "7F6000", "RED": "9C0006", "ESCALATE": "3F1F7F"}
INPUT_FILL = "FFF9E5"
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="top", wrap_text=True)

REVIEW_COLUMNS = [
    # (header, width, human-column?)
    ("No", 5, False),
    ("Source Type", 8, False),
    ("Source File", 18, False),
    ("Source Location", 22, False),
    ("Page / Slide", 7, False),
    ("Section", 14, False),
    ("Audience", 14, False),
    ("Message Type", 10, False),
    ("Status", 10, False),
    ("Original", 42, True),
    ("Problem", 34, False),
    ("Customer Value", 28, False),
    ("Evidence", 32, False),
    ("AI Recommended", 42, True),
    ("Alternative A", 32, False),
    ("Alternative B", 32, False),
    ("Reason", 34, False),
    ("Human Final", 38, True),
    ("Decision", 11, True),
    ("Comment", 26, True),
    ("QA Check", 30, False),
    ("Category", 16, False),
    ("Unit ID (수정 금지)", 14, False),
]
MAP_COLUMNS = [
    ("Page / Slide / Source Location", 22), ("Section", 14), ("Audience", 14), ("Role", 9),
    ("Original Governing Message", 44), ("Recommended Governing Message", 44), ("Customer Value", 30),
    ("Story Connection", 30), ("Evidence", 32), ("Status", 10),
]


def hdr(ws, row, cols, human_idx=()):
    for i, (name, width, *rest) in enumerate(cols, start=1):
        c = ws.cell(row, i, name)
        is_h = rest[0] if rest else False
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=HUMAN if is_h else NAVY)
        c.alignment = CENTER
        c.border = BORDER
        ws.column_dimensions[get_column_letter(i)].width = width


def est_height(values_widths, base=15):
    lines = 1
    for v, w in values_widths:
        if not v:
            continue
        s = str(v)
        n = 0
        for part in s.split("\n"):
            # 한글 1자 ≈ 2 폭 단위, 영문 1자 ≈ 1
            units = sum(2 if ord(ch) > 0x2E80 else 1 for ch in part)
            n += max(1, math.ceil(units / max(1, (w * 1.1))))
        lines = max(lines, n)
    return min(240, base * lines + 4)


def status_cell(c, st):
    if st in STATUS_FILL:
        c.fill = PatternFill("solid", fgColor=STATUS_FILL[st])
        c.font = Font(bold=True, color=STATUS_FONT[st])
    c.alignment = CENTER


def build_rows(an: dict, rec: dict) -> list[dict]:
    items = dict((rec or {}).get("items", {}))
    # recommendations는 Unit ID 키(items) 또는 원문 키(by_original) 둘 다 허용
    by_orig = {cmp_key(k): v for k, v in ((rec or {}).get("by_original") or {}).items()}
    corpus_numbers = set(an.get("corpus_numbers", []))
    corpus_text = "\n".join(
        [m["original"] for m in an["messages"]]
        + [e for m in an["messages"] for e in m.get("slide_evidence", [])]
        + [e["text"] for e in an.get("evidence", [])]
        + [r["text"] for r in an.get("requirements", [])]
    )
    rows = []
    for m in an["messages"]:
        a = m["assessment"]
        def filled(x):
            return bool(x) and any(x.get(k) for k in ("ai_recommended", "problem", "reason", "customer_value"))
        r_item, r_orig = items.get(m["id"]) or {}, by_orig.get(cmp_key(m["original"])) or {}
        r = r_item if filled(r_item) else (r_orig or r_item)
        if not filled(r) and r.get("status") == r.get("engine_status"):
            r = {}  # 빈 템플릿 → 엔진 판정 사용
        status = (r.get("status") or a["status"]).upper()
        if status not in STATUS_FILL:
            status = a["status"]
        ai_rec = norm_text(r.get("ai_recommended", ""))
        alt_a, alt_b = norm_text(r.get("alt_a", "")), norm_text(r.get("alt_b", ""))
        if status == "GREEN" and not ai_rec:
            ai_rec = ""  # 유지
        problem = r.get("problem") or " / ".join(a["problems"]) or ("문제 없음 — 유지" if status == "GREEN" else "")
        ev_auto = []
        if m.get("slide_evidence"):
            ev_auto.append("장표 내: " + " / ".join(e[:60] for e in m["slide_evidence"][:3]))
        if m.get("linked_evidence"):
            ev_auto.append("연결: " + " / ".join(f"{e['source_file']} {e['source_location']}" for e in m["linked_evidence"][:2]))
        if m.get("evidence_candidates"):
            ev_auto.append("후보(확인 필요): " + " / ".join(f"{e['source_file']} {e['source_location']}" for e in m["evidence_candidates"]))
        evidence = r.get("evidence") or ("; ".join(ev_auto) if ev_auto else "없음")
        reason = r.get("reason", "")
        if status == "ESCALATE":
            req = a.get("evidence_request") or []
            if req and "추가 검토 가능한 Evidence" not in reason:
                reason = (reason + "\n" if reason else "") + "ESCALATE — 추가 검토 가능한 Evidence:\n- " + "\n- ".join(req)
        # QA: Fact Guard + 재진단
        qa = []
        level = "OK"
        for label, txt in (("AI", ai_rec), ("A", alt_a), ("B", alt_b)):
            if not txt:
                continue
            fg = fact_guard(m["original"], txt, corpus_numbers, corpus_text)
            if fg["level"] != "OK":
                qa.append(f"[{fg['level']}·{label}] " + "; ".join(fg["messages"]))
                if fg["level"] == "ERROR" or level == "OK":
                    level = fg["level"] if fg["level"] == "ERROR" else ("WARN" if level == "OK" else level)
        if ai_rec:
            ra = assess(ai_rec, {"message_type": m["message_type"], "slide_evidence": m.get("slide_evidence", []),
                                 "linked_evidence": m.get("linked_evidence", []), "audience": m["audience"]})
            qa.append(f"재진단: {ra['status']} (원문 {a['status']}, 점수 {a['overall']}→{ra['overall']})")
            if ra["status"] == "RED":
                qa.append("⚠ 수정안도 RED — 다시 검토")
                level = "WARN" if level == "OK" else level
        if status in ("RED", "YELLOW") and not ai_rec:
            qa.append("⚠ RED/YELLOW인데 AI Recommended 없음")
        qa_text = (f"Fact Guard {level}" + ("\n" + "\n".join(qa) if qa else ""))
        default_decision = {"GREEN": "KEEP", "ESCALATE": "ESCALATE"}.get(status, "")
        if level == "ERROR":
            default_decision = ""
        rows.append({
            "No": m["seq"], "Source Type": m["source_type"], "Source File": m["source_file"],
            "Source Location": m["source_location"], "Page / Slide": m["page"], "Section": m["section"],
            "Audience": r.get("audience") or m["audience"], "Message Type": m["message_type"], "Status": status,
            "Original": m["original"], "Problem": problem, "Customer Value": r.get("customer_value", ""),
            "Evidence": evidence, "AI Recommended": ai_rec, "Alternative A": alt_a, "Alternative B": alt_b,
            "Reason": reason, "Human Final": "", "Decision": default_decision, "Comment": "",
            "QA Check": qa_text, "Category": r.get("category") or a["categories"][0],
            "Unit ID (수정 금지)": m["id"],
            "_guard": level, "_m": m, "_r": r,
        })
    return rows


def sheet_summary(wb, an, rec, rows, project):
    ws = wb.active
    ws.title = "Executive Summary"
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 14
    ws.column_dimensions["D"].width = 70
    c = an["context"]
    ws["A1"] = f"키 메시지 Review — {project}"
    ws["A1"].font = Font(bold=True, size=16, color=NAVY)
    ws.merge_cells("A1:D1")
    info = [
        ("고객", c.get("customer") or "(미확인)"),
        ("사업", c.get("project") or project),
        ("산업 / 도메인", f"{', '.join(c.get('industry') or []) or '-'} / {', '.join(c.get('domains') or [])}"),
        ("분석 자료", "; ".join(f"{s['file']} ({s['type']}, {s['role']})" for s in c["sources"])),
        ("생성일", dt.datetime.now().strftime("%Y-%m-%d %H:%M")),
    ]
    r = 3
    for k, v in info:
        ws.cell(r, 1, k).font = Font(bold=True)
        ws.cell(r, 1).alignment = WRAP
        ws.cell(r, 2, v).alignment = WRAP
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        ws.row_dimensions[r].height = est_height([(v, 95)])
        r += 1
    r += 1
    total = an["scores"]["Proposal Message Score"]
    ws.cell(r, 1, "Proposal Message Score").font = Font(bold=True, size=13)
    sc = ws.cell(r, 2, total)
    sc.font = Font(bold=True, size=14, color=NAVY)
    ws.cell(r, 3, "/ 100")
    r += 2
    for i, h in enumerate(["진단 항목", "점수 (1~5)", "100점 환산", "해석"], start=1):
        cc = ws.cell(r, i, h)
        cc.font = Font(bold=True, color="FFFFFF")
        cc.fill = PatternFill("solid", fgColor=NAVY)
        cc.border = BORDER
    r += 1
    interp = {
        "Customer Relevance": "고객 업무·사업 관점으로 쓰였는가",
        "Governing Message": "장표마다 고객이 기억할 한 문장이 있는가",
        "Key Message": "Key가 Why/How/Evidence 역할을 나눠 맡는가",
        "Tech-to-Value": "기술 → 업무 변화 → 가치로 이어지는가",
        "Audience Fit": "읽는 사람(경영진/IT/현업) 관점에 맞는가",
        "Specificity": "업무·대상·수치가 구체적인가",
        "Differentiation": "경쟁사 이름으로 바꿔도 통하는 일반론이 아닌가",
        "Evidence": "주장을 숫자·실적·Reference로 증명하는가",
        "Story Flow": "Why→What→Why Us→How→Evidence→Value 흐름",
        "AI Naturalness": "AI 상투어·번역투가 적은가",
        "One Message": "한 문장에 하나의 주장인가",
    }
    for k, v in an["scores"]["dimensions"].items():
        ws.cell(r, 1, k).border = BORDER
        c2 = ws.cell(r, 2, v if v is not None else "-")
        c2.border = BORDER
        c2.alignment = CENTER
        c3 = ws.cell(r, 3, round(v * 20) if v is not None else "-")
        c3.border = BORDER
        c3.alignment = CENTER
        if v is not None:
            col = "C6EFCE" if v >= 4 else "FFEB9C" if v >= 3 else "FFC7CE"
            c2.fill = PatternFill("solid", fgColor=col)
        ws.cell(r, 4, interp.get(k, "")).border = BORDER
        r += 1
    r += 1
    ws.cell(r, 1, "제안서 핵심 진단").font = Font(bold=True, size=13)
    r += 1
    diag = ((rec or {}).get("summary") or {}).get("diagnosis") or auto_diagnosis(an)
    cd = ws.cell(r, 1, diag)
    cd.alignment = WRAP
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    ws.row_dimensions[r].height = est_height([(diag, 120)])
    r += 2
    ws.cell(r, 1, "가장 중요한 문제").font = Font(bold=True, size=13)
    r += 1
    issues = ((rec or {}).get("summary") or {}).get("top_issues") or an["top_issues"]
    for i, t in enumerate(issues[:5], start=1):
        ws.cell(r, 1, f"{i}.").alignment = Alignment(horizontal="right", vertical="top")
        cc = ws.cell(r, 2, t)
        cc.alignment = WRAP
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        ws.row_dimensions[r].height = est_height([(t, 95)])
        r += 1
    r += 1
    ws.cell(r, 1, "Status").font = Font(bold=True, size=13)
    r += 1
    cnt = {s: sum(1 for x in rows if x["Status"] == s) for s in STATUS_FILL}
    meaning = {"GREEN": "이미 좋은 메시지 → 유지", "YELLOW": "의미는 좋음, 표현 최소 수정",
               "RED": "추상·상투·가치 부족·차별성 부족 → 적극 수정", "ESCALATE": "Evidence/Fact 부족 → 원문 유지 + 정보 요청"}
    for s, n in cnt.items():
        a = ws.cell(r, 1, s)
        status_cell(a, s)
        ws.cell(r, 2, n).alignment = CENTER
        ws.cell(r, 4, meaning[s])
        r += 1
    guard_err = sum(1 for x in rows if x["_guard"] == "ERROR")
    guard_warn = sum(1 for x in rows if x["_guard"] == "WARN")
    r += 1
    ws.cell(r, 1, "Fact Guard").font = Font(bold=True)
    ws.cell(r, 2, f"ERROR {guard_err} / WARN {guard_warn}")
    r += 2
    ws.cell(r, 1, "검토 방법").font = Font(bold=True, size=13)
    for line in [
        "① 'Message Review' 시트에서 Original ↔ AI Recommended 를 비교합니다.",
        "② Decision 을 고릅니다: ACCEPT(AI안 사용) / EDIT(Human Final 사용) / KEEP(원문 유지) / ESCALATE(원문 유지+근거 보완).",
        "③ EDIT 는 Human Final 에 최종 문장을 직접 씁니다. 비어 있으면 반영되지 않습니다.",
        "④ QA Check 에 Fact Guard ERROR 가 있으면 ACCEPT 하지 마세요(숫자·고유명사 변경).",
        "⑤ 저장 후 '승인한 키 메시지 Excel 기준으로 원본 PPT 수정해줘' 라고 요청하면 APPLY 합니다.",
    ]:
        r += 1
        ws.cell(r, 1, line)
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)


def auto_diagnosis(an):
    sc = an["status_count"]
    d = an["scores"]["dimensions"]
    weak = sorted([(v, k) for k, v in d.items() if v is not None])[:3]
    tot = sum(sc.values())
    return (f"검토 메시지 {tot}개 중 RED {sc['RED']}개, ESCALATE {sc['ESCALATE']}개입니다. "
            f"약한 항목은 {', '.join(k for _, k in weak)} 입니다. "
            + (f"Story 단계 중 {', '.join(an['story']['missing_roles'])} 가 보이지 않습니다. " if an['story']['missing_roles'] else "")
            + "기술 설명을 고객 업무의 변화로 바꾸고, 주장에는 원문 Evidence를 붙이는 것이 우선입니다.")


def sheet_map(wb, an, rows):
    ws = wb.create_sheet("Message Map")
    hdr(ws, 1, [(n, w) for n, w in MAP_COLUMNS])
    by_id = {x["Unit ID (수정 금지)"]: x for x in rows}
    content = [s for s in an["slides"] if s["kind"] == "content"]
    r = 2
    for i, s in enumerate(content):
        prev_role = content[i - 1]["story_role"] if i > 0 else None
        next_role = content[i + 1]["story_role"] if i + 1 < len(content) else None
        row = by_id.get(s["governing_id"]) if s["governing_id"] else None
        if row:
            rec_gov = row["AI Recommended"] if row["AI Recommended"] and row["Status"] in ("RED", "YELLOW") else row["Original"]
            vals = [f"{s['source_file']} p{s['page']}" if s["page"] else f"{s['source_file']} / {row['Source Location']}",
                    s["section"] or "", s["audience"], s["story_role"] or "-", row["Original"], rec_gov,
                    row["Customer Value"], "", row["Evidence"], row["Status"]]
            m = row["_m"]
            reqs = ", ".join(x["req_id"] for x in m.get("linked_requirements", [])[:3])
        else:
            vals = [f"{s['source_file']} p{s['page']}", s["section"] or "", s["audience"], s["story_role"] or "-",
                    f"(Governing 없음) 제목: {s['title']}", "⚠ 고객이 기억할 한 문장을 추가해야 합니다", "", "", "", "RED"]
            reqs = ""
        conn = f"{prev_role or '시작'} → [{s['story_role'] or '?'}] → {next_role or '끝'}"
        if reqs:
            conn += f"\n요구사항: {reqs}"
        vals[7] = conn
        for ci, v in enumerate(vals, start=1):
            c = ws.cell(r, ci, v)
            c.alignment = WRAP
            c.border = BORDER
        status_cell(ws.cell(r, 10), vals[9])
        ws.row_dimensions[r].height = est_height([(vals[4], 44), (vals[5], 44), (vals[8], 32), (vals[7], 30)])
        r += 1
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(MAP_COLUMNS))}{max(2, r - 1)}"


def sheet_review(wb, rows):
    ws = wb.create_sheet("Message Review")
    hdr(ws, 1, REVIEW_COLUMNS)
    names = [c[0] for c in REVIEW_COLUMNS]
    human = {c[0] for c in REVIEW_COLUMNS if c[2]}
    widths = {c[0]: c[1] for c in REVIEW_COLUMNS}
    for ri, row in enumerate(rows, start=2):
        for ci, n in enumerate(names, start=1):
            c = ws.cell(ri, ci, row.get(n, ""))
            c.alignment = CENTER if n in ("No", "Source Type", "Page / Slide", "Message Type", "Decision") else WRAP
            c.border = BORDER
            if n in ("Human Final", "Decision", "Comment"):
                c.fill = PatternFill("solid", fgColor=INPUT_FILL)
            if n == "Unit ID (수정 금지)":
                c.font = Font(color="808080", size=8)
            if n == "QA Check" and row["_guard"] == "ERROR":
                c.font = Font(color="C00000", bold=True)
            if n == "AI Recommended" and row["AI Recommended"]:
                c.font = Font(bold=True, color="1F3864")
            if n == "Original":
                c.font = Font(color="404040")
        status_cell(ws.cell(ri, names.index("Status") + 1), row["Status"])
        ws.row_dimensions[ri].height = est_height([(row.get(n), widths[n]) for n in ("Original", "AI Recommended", "Problem", "Reason", "Evidence", "QA Check", "Alternative A")])
    last = max(2, len(rows) + 1)
    dcol = get_column_letter(names.index("Decision") + 1)
    dv = DataValidation(type="list", formula1='"' + ",".join(DECISIONS) + '"', allow_blank=True,
                        showErrorMessage=True, errorTitle="Decision", error="ACCEPT / EDIT / KEEP / ESCALATE 중 선택",
                        promptTitle="Decision", prompt="ACCEPT=AI안, EDIT=Human Final, KEEP=원문, ESCALATE=원문+근거보완")
    dv.add(f"{dcol}2:{dcol}{last + 200}")
    ws.add_data_validation(dv)
    # EDIT인데 Human Final 비어 있으면 빨간색 경고
    hcol = get_column_letter(names.index("Human Final") + 1)
    ws.conditional_formatting.add(f"{hcol}2:{hcol}{last + 200}",
                                  FormulaRule(formula=[f'AND(${dcol}2="EDIT",LEN(TRIM(${hcol}2))=0)'],
                                              fill=PatternFill("solid", fgColor="FF9999")))
    ws.conditional_formatting.add(f"{dcol}2:{dcol}{last + 200}",
                                  FormulaRule(formula=[f'${dcol}2="ACCEPT"'], fill=PatternFill("solid", fgColor="C6EFCE")))
    ws.conditional_formatting.add(f"{dcol}2:{dcol}{last + 200}",
                                  FormulaRule(formula=[f'${dcol}2="EDIT"'], fill=PatternFill("solid", fgColor="BDD7EE")))
    ws.freeze_panes = ws.cell(2, names.index("Status") + 2)  # 헤더 + Status까지 고정
    ws.auto_filter.ref = f"A1:{get_column_letter(len(names))}{last}"
    # 덜 보는 컬럼은 Outline으로 접기
    for n in ("Source Type", "Source File"):
        ws.column_dimensions[get_column_letter(names.index(n) + 1)].outlineLevel = 1


def sheet_trace(wb, an):
    reqs, evs = an.get("requirements", []), an.get("evidence", [])
    if not reqs and not evs:
        return
    ws = wb.create_sheet("Source Trace")
    r = 1
    if reqs:
        cols = [("Req ID", 12), ("Customer Requirement", 50), ("Source File", 20), ("Source Location", 24),
                ("Coverage", 11), ("Covered by (Proposal)", 26), ("Message", 44)]
        hdr(ws, r, cols)
        r += 1
        for q in reqs:
            vals = [q["req_id"], q["text"], q["source_file"], q["source_location"], q["coverage"],
                    q.get("covered_by") or "", q.get("covered_message") or ""]
            for ci, v in enumerate(vals, start=1):
                c = ws.cell(r, ci, v)
                c.alignment = WRAP
                c.border = BORDER
            cov = ws.cell(r, 5)
            cov.fill = PatternFill("solid", fgColor={"COVERED": "C6EFCE", "WEAK": "FFEB9C", "GAP": "FFC7CE"}[q["coverage"]])
            ws.row_dimensions[r].height = est_height([(q["text"], 50), (vals[6], 44)])
            r += 1
        ws.auto_filter.ref = f"A1:G{r - 1}"
        r += 2
    if evs:
        ws.cell(r, 1, "Evidence Inventory (원문에서 확인된 사실만)").font = Font(bold=True, size=12)
        r += 1
        cols2 = [("Kind", 12), ("Evidence", 50), ("Source File", 20), ("Source Location", 24)]
        for i, (n, w) in enumerate(cols2, start=1):
            c = ws.cell(r, i, n)
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor=NAVY)
        r += 1
        for e in evs[:400]:
            for ci, v in enumerate([e["kind"], e["text"], e["source_file"], e["source_location"]], start=1):
                c = ws.cell(r, ci, v)
                c.alignment = WRAP
                c.border = BORDER
            r += 1
    ws.freeze_panes = "A2"


def sheet_guide(wb):
    ws = wb.create_sheet("Guide")
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 90
    rows = [
        ("Status", ""), ("GREEN", "이미 좋은 메시지 → 유지 (억지로 다시 쓰지 않음)"),
        ("YELLOW", "핵심 의미는 좋음 → 표현만 최소 수정"),
        ("RED", "추상적·AI 상투어·고객 가치 부족·차별성 부족·One Message 불명확 → 적극 수정"),
        ("ESCALATE", "Evidence/Fact 부족 → 원문 유지 + 추가 정보 요청 (없는 근거를 만들지 않음)"),
        ("", ""), ("Decision", ""), ("ACCEPT", "AI Recommended 를 원본에 반영"),
        ("EDIT", "Human Final 을 원본에 반영 (비어 있으면 Warning, 반영 안 함)"),
        ("KEEP", "원문 유지"), ("ESCALATE", "원문 유지 + 추가 Evidence 필요 (Comment에 요청 내용)"),
        ("(빈칸)", "결정하지 않음 → 원문 유지 + Warning"),
        ("", ""), ("QA Check", "Fact Guard: 원문·근거에 없는 숫자 생성 = ERROR, 숫자/고유명사 누락·근거자료 인용 = WARN. 재진단: AI안을 다시 평가한 Status"),
        ("Unit ID", "원본 위치 식별자. 수정하지 마세요 (APPLY 시 위치 매칭에 사용)."),
    ]
    for i, (a, b) in enumerate(rows, start=1):
        ca = ws.cell(i, 1, a)
        ws.cell(i, 2, b).alignment = WRAP
        if a in STATUS_FILL:
            status_cell(ca, a)
        elif a and not b:
            ca.font = Font(bold=True, size=12)


def write_meta(wb, an, analysis_path):
    ws = wb.create_sheet("_meta")
    meta = {"schema_version": SCHEMA_VERSION, "tool": "key-message", "created": dt.datetime.now().isoformat(timespec="seconds"),
            "analysis": str(analysis_path), "sources": an["context"]["sources"],
            "domains": an["context"].get("domains"), "industry": an["context"].get("industry"),
            "corpus_numbers": an.get("corpus_numbers", []),
            "locators": {m["id"]: m["locator"] for m in an["messages"]},
            "styles": {m["id"]: {"size": (m.get("style") or {}).get("size"), "geom": m.get("geom")} for m in an["messages"]}}
    s = json.dumps(meta, ensure_ascii=False)
    # 셀 하나 32767자 제한 → 분할 저장
    for i in range(0, len(s), 30000):
        ws.cell(i // 30000 + 1, 1, s[i:i + 30000])
    ws.sheet_state = "hidden"


def slug(s: str) -> str:
    s = re.sub(r"[\\/:*?\"<>|\s]+", "_", s or "").strip("_")
    return s[:60] or "Proposal"


def main():
    ap = argparse.ArgumentParser(description="키 메시지: Review Excel 생성")
    ap.add_argument("analysis")
    ap.add_argument("recommendations", nargs="?")
    ap.add_argument("-o", "--out", default=".", help="출력 폴더 또는 .xlsx 경로")
    ap.add_argument("--project", help="프로젝트명 (파일명에 사용)")
    a = ap.parse_args()
    an = load_json(a.analysis)
    rec = load_json(a.recommendations) if a.recommendations and Path(a.recommendations).exists() else {}
    proposal = next((s["file"] for s in an["context"]["sources"] if s["role"] == "proposal"), "Proposal")
    project = a.project or rec.get("project") or Path(proposal).stem
    out = Path(a.out)
    if out.suffix.lower() != ".xlsx":
        out = out / f"{slug(project)}_KeyMessage_Review.xlsx"
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = build_rows(an, rec)
    wb = Workbook()
    sheet_summary(wb, an, rec, rows, project)
    sheet_map(wb, an, rows)
    sheet_review(wb, rows)
    sheet_trace(wb, an)
    sheet_guide(wb)
    write_meta(wb, an, Path(a.analysis).resolve())
    for ws in wb.worksheets:
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
    wb.active = wb.sheetnames.index("Message Review")
    wb.save(out)
    errs = [x for x in rows if x["_guard"] == "ERROR"]
    print(f"[OK] Review Excel → {out}")
    print(f"     rows={len(rows)} status=" + str({s: sum(1 for x in rows if x['Status'] == s) for s in STATUS_FILL})
          + f" fact_guard_error={len(errs)}")
    for x in errs:
        print(f"     [FACT GUARD ERROR] #{x['No']} {x['Source Location']}: {x['QA Check'].splitlines()[1] if len(x['QA Check'].splitlines())>1 else ''}")


if __name__ == "__main__":
    main()
