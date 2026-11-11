# -*- coding: utf-8 -*-
"""산출물 검증.

  python validate_output.py review  Proposal_KeyMessage_Review.xlsx
      → 시트·컬럼·Decision 검증·Freeze·Filter, EDIT인데 Human Final 빈칸, Fact Guard 재검사

  python validate_output.py apply   Original.pptx Original_KeyMessage_v2.pptx --log Original_KeyMessage_v2_apply_log.json
      → 승인된 텍스트만 바뀌었는지, 디자인 요소(Slide Size·Layout·Shape 위치·이미지·차트·표·폰트)가 그대로인지
  python validate_output.py apply   Original.xlsx Original_KeyMessage_v2.xlsx --log ..._apply_log.json
      → 승인 셀 외 값·수식·시트·차트 파트가 그대로인지

종료 코드: 0 = PASS, 1 = FAIL
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from km_common import DECISIONS, cmp_key, fact_guard, load_json, norm_text  # noqa: E402

REQUIRED_SHEETS = ["Executive Summary", "Message Map", "Message Review"]
REQUIRED_REVIEW_COLS = ["Source Type", "Source File", "Source Location", "Page / Slide", "Section", "Audience",
                        "Message Type", "Status", "Original", "Problem", "Customer Value", "Evidence",
                        "AI Recommended", "Alternative A", "Alternative B", "Reason", "Human Final", "Decision", "Comment"]
REQUIRED_MAP_COLS = ["Page / Slide / Source Location", "Section", "Audience", "Role", "Original Governing Message",
                     "Recommended Governing Message", "Customer Value", "Story Connection", "Evidence", "Status"]


def validate_review(path: Path) -> dict:
    import openpyxl
    rep = {"target": str(path), "errors": [], "warnings": [], "info": {}}
    wb = openpyxl.load_workbook(str(path))
    for s in REQUIRED_SHEETS:
        if s not in wb.sheetnames:
            rep["errors"].append(f"시트 없음: {s}")
    if rep["errors"]:
        return rep
    ws = wb["Message Review"]
    heads = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    for c in REQUIRED_REVIEW_COLS:
        if c not in heads:
            rep["errors"].append(f"Message Review 컬럼 없음: {c}")
    mh = [wb["Message Map"].cell(1, c).value for c in range(1, wb["Message Map"].max_column + 1)]
    for c in REQUIRED_MAP_COLS:
        if c not in mh:
            rep["errors"].append(f"Message Map 컬럼 없음: {c}")
    if not ws.freeze_panes:
        rep["errors"].append("Freeze Header 없음")
    if not ws.auto_filter.ref:
        rep["errors"].append("Filter 없음")
    dvs = [dv for dv in ws.data_validations.dataValidation if "ACCEPT" in (dv.formula1 or "")]
    if not dvs:
        rep["errors"].append("Decision Data Validation 없음")
    col = {h: i + 1 for i, h in enumerate(heads) if h}
    wrap_ok = ws.cell(2, col["Original"]).alignment.wrap_text if ws.max_row >= 2 else True
    if not wrap_ok:
        rep["warnings"].append("Original 컬럼 Wrap Text 미적용")
    n, by_status, by_dec = 0, {}, {}
    for r in range(2, ws.max_row + 1):
        if not ws.cell(r, col["Original"]).value:
            continue
        n += 1
        st = ws.cell(r, col["Status"]).value
        by_status[st] = by_status.get(st, 0) + 1
        d = (ws.cell(r, col["Decision"]).value or "").strip().upper()
        by_dec[d or "(blank)"] = by_dec.get(d or "(blank)", 0) + 1
        if d and d not in DECISIONS:
            rep["errors"].append(f"Row {r}: Decision 값 오류 '{d}'")
        if d == "EDIT" and not norm_text(ws.cell(r, col["Human Final"]).value):
            rep["warnings"].append(f"Row {r}: EDIT인데 Human Final 비어 있음")
        if d == "ACCEPT" and not norm_text(ws.cell(r, col["AI Recommended"]).value):
            rep["warnings"].append(f"Row {r}: ACCEPT인데 AI Recommended 비어 있음")
        o, ai = ws.cell(r, col["Original"]).value, ws.cell(r, col["AI Recommended"]).value
        if ai:
            fg = fact_guard(o, ai)
            if fg["level"] == "ERROR":
                (rep["errors"] if d == "ACCEPT" else rep["warnings"]).append(f"Row {r}: AI Recommended Fact Guard ERROR — {'; '.join(fg['messages'])}")
        if st == "ESCALATE" and ai and d == "ACCEPT":
            rep["warnings"].append(f"Row {r}: ESCALATE 메시지를 ACCEPT — Evidence 확인 필요")
    rep["info"] = {"messages": n, "status": by_status, "decision": by_dec, "sheets": wb.sheetnames}
    return rep


# ------------------------------------------------------------------ PPTX 비교
def pptx_snapshot(path: Path) -> dict:
    from pptx import Presentation
    prs = Presentation(str(path))
    snap = {"slide_w": prs.slide_width, "slide_h": prs.slide_height, "masters": len(prs.slide_masters),
            "layouts": [s.slide_layout.name for s in prs.slides], "slides": []}

    def walk(shapes, prefix, out):
        for shp in shapes:
            key = prefix + [shp.shape_id]
            rec = {"id": ".".join(map(str, key)), "name": shp.name, "type": str(shp.shape_type),
                   "box": (shp.left, shp.top, shp.width, shp.height), "paras": [], "fonts": []}
            if shp.shape_type is not None and "GROUP" in str(shp.shape_type):
                out.append(rec)
                walk(shp.shapes, key, out)
                continue
            if getattr(shp, "has_text_frame", False) and shp.has_text_frame:
                for p in shp.text_frame.paragraphs:
                    rec["paras"].append(norm_text(p.text))
                    r0 = p.runs[0] if p.runs else None
                    rec["fonts"].append(None if r0 is None else (r0.font.name, r0.font.bold, r0.font.italic,
                                                                 str(r0.font.color.rgb) if r0.font.color and r0.font.color.type is not None and hasattr(r0.font.color, "rgb") and r0.font.color.type == 1 else None,
                                                                 p.alignment))
            if getattr(shp, "has_table", False) and shp.has_table:
                rec["table"] = [[norm_text(c.text) for c in row.cells] for row in shp.table.rows]
            if getattr(shp, "has_chart", False) and shp.has_chart:
                rec["chart"] = str(shp.chart.chart_type)
            out.append(rec)

    for s in prs.slides:
        shapes = []
        walk(s.shapes, [], shapes)
        snap["slides"].append({"bg": s.background.fill.type if s.follow_master_background is False else "master",
                               "shapes": shapes})
    return snap


def validate_apply_pptx(orig: Path, rev: Path, log: dict) -> dict:
    rep = {"target": str(rev), "errors": [], "warnings": [], "info": {}}
    a, b = pptx_snapshot(orig), pptx_snapshot(rev)
    for k in ("slide_w", "slide_h", "masters", "layouts"):
        if a[k] != b[k]:
            rep["errors"].append(f"{k} 변경됨: {a[k]} → {b[k]}")
    if len(a["slides"]) != len(b["slides"]):
        rep["errors"].append("슬라이드 수 변경")
        return rep
    expected = {}  # (slide, shape_id) → {para_idx: new}  / 원문 텍스트로 확인
    applied = log.get("applied", [])
    exp_new = [cmp_key(e["new"]) for e in applied]
    exp_orig = [cmp_key(e["original"]) for e in applied]
    changed_paras, unexpected = 0, []
    font_changes = 0
    for si, (sa, sb) in enumerate(zip(a["slides"], b["slides"]), start=1):
        if sa["bg"] != sb["bg"]:
            rep["errors"].append(f"Slide {si}: 배경 변경")
        if len(sa["shapes"]) != len(sb["shapes"]):
            rep["errors"].append(f"Slide {si}: Shape 수 변경 {len(sa['shapes'])}→{len(sb['shapes'])}")
            continue
        for xa, xb in zip(sa["shapes"], sb["shapes"]):
            for k in ("id", "name", "type", "box"):
                if xa[k] != xb[k]:
                    rep["errors"].append(f"Slide {si} shape {xa['name']}: {k} 변경")
            if xa.get("chart") != xb.get("chart"):
                rep["errors"].append(f"Slide {si} shape {xa['name']}: 차트 변경")
            pa, pb = xa["paras"], xb["paras"]
            if xa.get("table") != xb.get("table"):
                # 표 셀 변경도 승인 목록과 대조
                for ra, rb in zip(xa.get("table") or [], xb.get("table") or []):
                    for ca, cb in zip(ra, rb):
                        if ca != cb:
                            changed_paras += 1
                            if cmp_key(cb) not in exp_new:
                                unexpected.append(f"Slide {si} table: '{ca}' → '{cb}'")
            if pa == pb:
                continue
            # 문단 병합(mode=shape) 허용
            if len(pa) != len(pb):
                joined = cmp_key(" ".join(pa))
                if joined in exp_orig and cmp_key(" ".join(pb)) in exp_new:
                    changed_paras += 1
                    continue
                unexpected.append(f"Slide {si} {xa['name']}: 문단 수 변경")
                continue
            for i, (ta, tb) in enumerate(zip(pa, pb)):
                if ta == tb:
                    if xa["fonts"][i] != xb["fonts"][i]:
                        rep["errors"].append(f"Slide {si} {xa['name']} ¶{i+1}: 텍스트 그대로인데 서식 변경")
                    continue
                changed_paras += 1
                if cmp_key(tb) not in exp_new or cmp_key(ta) not in exp_orig:
                    unexpected.append(f"Slide {si} {xa['name']} ¶{i+1}: '{ta[:30]}' → '{tb[:30]}'")
                fa, fb = xa["fonts"][i], xb["fonts"][i]
                if fa and fb and fa[:4] != fb[:4]:
                    font_changes += 1
                    rep["errors"].append(f"Slide {si} {xa['name']} ¶{i+1}: 첫 Run 서식(폰트/굵기/색) 변경 {fa} → {fb}")
                if fa and fb and fa[4] != fb[4]:
                    rep["errors"].append(f"Slide {si} {xa['name']} ¶{i+1}: 정렬 변경")
    for u in unexpected:
        rep["errors"].append("승인되지 않은 텍스트 변경: " + u)
    if changed_paras != len(applied):
        rep["warnings"].append(f"변경 문단 수({changed_paras}) ≠ 반영 로그({len(applied)})")
    # 적용 결과 텍스트가 실제로 있는지
    all_b = [cmp_key(p) for s in b["slides"] for x in s["shapes"] for p in x["paras"]] + \
            [cmp_key(c) for s in b["slides"] for x in s["shapes"] for r in (x.get("table") or []) for c in r]
    for e in applied:
        if cmp_key(e["new"]) not in all_b:
            rep["errors"].append(f"반영 로그의 새 문장이 수정본에 없음: {e['new'][:40]}")
    for e in log.get("warnings", []):
        for w in e.get("warnings", []):
            rep["warnings"].append(f"#{e.get('no')} {w}")
    rep["info"] = {"slides": len(b["slides"]), "changed_paragraphs": changed_paras, "applied": len(applied),
                   "skipped": len(log.get("skipped", []))}
    return rep


def validate_apply_xlsx(orig: Path, rev: Path, log: dict) -> dict:
    import openpyxl
    rep = {"target": str(rev), "errors": [], "warnings": [], "info": {}}
    za, zb = zipfile.ZipFile(str(orig)), zipfile.ZipFile(str(rev))
    na, nb = set(za.namelist()), set(zb.namelist())
    if na != nb:
        rep["errors"].append(f"패키지 파트 변경: -{sorted(na - nb)} +{sorted(nb - na)}")
    changed_parts = [n for n in na & nb if za.read(n) != zb.read(n)]
    allowed = [n for n in changed_parts if n.startswith("xl/worksheets/") or n == "xl/sharedStrings.xml"]
    for n in set(changed_parts) - set(allowed):
        rep["errors"].append(f"텍스트 외 파트 변경: {n}")
    wa, wb_ = openpyxl.load_workbook(str(orig)), openpyxl.load_workbook(str(rev))
    if wa.sheetnames != wb_.sheetnames:
        rep["errors"].append("시트 구성 변경")
    exp = {}
    for e in log.get("applied", []):
        uid = e["unit_id"]
        sheet, cell = uid.split("|", 1)[1].rsplit("!", 1)
        exp[(sheet, cell)] = e["new"]
    changed = 0
    for s in wa.sheetnames:
        a, b = wa[s], wb_[s]
        if (a.max_row, a.max_column) != (b.max_row, b.max_column):
            rep["errors"].append(f"{s}: 크기 변경")
        for row in a.iter_rows():
            for c in row:
                vb = b[c.coordinate].value
                if c.value != vb:
                    changed += 1
                    if (s, c.coordinate) not in exp or cmp_key(vb) != cmp_key(exp[(s, c.coordinate)]):
                        rep["errors"].append(f"승인되지 않은 셀 변경: {s}!{c.coordinate}")
                if isinstance(c.value, str) and c.value.startswith("=") and c.value != vb:
                    rep["errors"].append(f"수식 변경: {s}!{c.coordinate}")
                if c.has_style and tuple(c._style) != tuple(b[c.coordinate]._style):
                    rep["errors"].append(f"서식 변경: {s}!{c.coordinate}")
    if changed != len(exp):
        rep["warnings"].append(f"변경 셀 수({changed}) ≠ 반영 로그({len(exp)})")
    rep["info"] = {"changed_cells": changed, "applied": len(exp), "changed_parts": changed_parts}
    return rep


def main():
    ap = argparse.ArgumentParser(description="키 메시지: 산출물 검증")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("review")
    r.add_argument("xlsx")
    p = sub.add_parser("apply")
    p.add_argument("original")
    p.add_argument("revised")
    p.add_argument("--log", help="apply_log.json (기본: 수정본명_apply_log.json)")
    ap.add_argument("--json", help="검증 결과 JSON 저장 경로")
    a = ap.parse_args()
    if a.cmd == "review":
        rep = validate_review(Path(a.xlsx))
    else:
        rev = Path(a.revised)
        log_path = Path(a.log) if a.log else rev.with_name(rev.stem + "_apply_log.json")
        log = load_json(log_path) if log_path.exists() else {"applied": []}
        if rev.suffix.lower() == ".pptx":
            rep = validate_apply_pptx(Path(a.original), rev, log)
        elif rev.suffix.lower() in (".xlsx", ".xlsm"):
            rep = validate_apply_xlsx(Path(a.original), rev, log)
        else:
            raise SystemExit("pptx/xlsx만 구조 검증을 지원합니다")
    rep["result"] = "PASS" if not rep["errors"] else "FAIL"
    if a.json:
        Path(a.json).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{rep['result']}] {rep['target']}")
    print("   info:", json.dumps(rep["info"], ensure_ascii=False, default=str))
    for e in rep["errors"]:
        print("   ✖", e)
    for w in rep["warnings"]:
        print("   ⚠", w)
    sys.exit(0 if rep["result"] == "PASS" else 1)


if __name__ == "__main__":
    main()
