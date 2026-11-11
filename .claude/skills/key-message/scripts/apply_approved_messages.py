# -*- coding: utf-8 -*-
"""Apply Engine — 사람이 승인한 메시지만 원본에 반영 (APPLY / AUTO).

  python apply_approved_messages.py Original.pptx Approved_KeyMessage_Review.xlsx
      → Original_KeyMessage_v2.pptx  (+ Original_KeyMessage_v2_apply_log.json)
  python apply_approved_messages.py Original.xlsx Review.xlsx            (XLSX: XML 단위 수정, 서식·수식·차트 보존)
  python apply_approved_messages.py Original.pptx Review.xlsx --auto     (AUTO: 결정 빈칸 → RED/YELLOW는 ACCEPT)

규칙
  ACCEPT   → AI Recommended
  EDIT     → Human Final (비어 있으면 Warning, 반영 안 함)
  KEEP     → 원문 유지
  ESCALATE → 원문 유지 (+ 추가 Evidence 필요)
  빈칸     → 원문 유지 + Warning   (--auto 일 때만 자동 결정)

안전장치
  - 원본 파일은 절대 덮어쓰지 않는다 (같은 경로면 중단, 기존 v2가 있으면 v3, v4 …)
  - 원본의 현재 텍스트가 Review의 Original과 다르면 반영하지 않는다 (Stale 방지)
  - ACCEPT안에 Fact Guard ERROR(새 숫자)가 있으면 반영하지 않는다 (--force 로만 허용)
  - 텍스트 Overflow: ① 축약 권고 ② 박스 내 Fit 확인 ③ 최대 10%·2pt까지만 폰트 축소 ④ 그래도 넘치면 Warning
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import math
import re
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_messages import DEFAULT_LEARNING_LOG  # noqa: E402
from km_common import DECISIONS, cmp_key, dump_json, fact_guard, norm_text, safe_output_path, text_units  # noqa: E402

A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


# ============================================================ Review 읽기
def read_review(path: Path) -> tuple[list[dict], dict]:
    import openpyxl

    wb = openpyxl.load_workbook(str(path), data_only=True)
    if "Message Review" not in wb.sheetnames:
        raise SystemExit("[ERROR] 'Message Review' 시트가 없습니다. key-message Review Excel이 맞는지 확인하세요.")
    ws = wb["Message Review"]
    headers = {}
    for c in range(1, ws.max_column + 1):
        v = ws.cell(1, c).value
        if v:
            headers[str(v).strip()] = c
    need = ["Original", "AI Recommended", "Human Final", "Decision", "Source File"]
    miss = [n for n in need if n not in headers]
    uid_col = next((c for h, c in headers.items() if h.startswith("Unit ID")), None)
    if miss or not uid_col:
        raise SystemExit(f"[ERROR] Review 시트 필수 컬럼 누락: {miss + ([] if uid_col else ['Unit ID'])}")
    rows = []
    for r in range(2, ws.max_row + 1):
        uid = ws.cell(r, uid_col).value
        if not uid:
            continue
        row = {h: ws.cell(r, c).value for h, c in headers.items()}
        row["_row"] = r
        row["Unit ID"] = str(uid)
        rows.append(row)
    meta = {}
    if "_meta" in wb.sheetnames:
        mw = wb["_meta"]
        s = "".join(str(mw.cell(i, 1).value or "") for i in range(1, mw.max_row + 1))
        try:
            meta = json.loads(s)
        except Exception:
            meta = {}
    return rows, meta


def resolve_decision(row: dict, auto: bool, force: bool, corpus: set | None = None) -> tuple[str | None, str, list[str]]:
    """→ (new_text or None, decision, warnings). corpus = 분석 자료 전체의 숫자(Review와 같은 기준으로 Fact Guard)"""
    w = []
    d = str(row.get("Decision") or "").strip().upper()
    status = str(row.get("Status") or "").strip().upper()
    ai = norm_text(row.get("AI Recommended") or "")
    hf = norm_text(row.get("Human Final") or "")
    orig = norm_text(row.get("Original") or "")
    qa = str(row.get("QA Check") or "")
    if not d:
        if auto:
            if status in ("RED", "YELLOW") and ai and "Fact Guard ERROR" not in qa:
                d = "ACCEPT"
            else:
                d = "KEEP"
            w.append(f"AUTO 결정: {d}")
        else:
            return None, "(blank)", ["Decision 빈칸 → 원문 유지"]
    if d not in DECISIONS:
        return None, d, [f"알 수 없는 Decision '{d}' → 원문 유지"]
    if d in ("KEEP", "ESCALATE"):
        return None, d, w
    if d == "ACCEPT":
        if not ai:
            return None, d, w + ["ACCEPT인데 AI Recommended가 비어 있음 → 원문 유지"]
        fg = fact_guard(orig, ai, corpus)
        if fg["level"] == "ERROR" and not force:
            return None, d, w + ["Fact Guard ERROR → 반영 안 함: " + "; ".join(fg["messages"])]
        if fg["level"] != "OK":
            w.append(f"Fact Guard {fg['level']}: " + "; ".join(fg["messages"]))
        new = ai
    else:  # EDIT
        if not hf:
            return None, d, w + ["EDIT인데 Human Final이 비어 있음 → 원문 유지 (Warning)"]
        fg = fact_guard(orig, hf, corpus)
        if fg["level"] != "OK":
            w.append(f"Human Final Fact 확인 필요({fg['level']}): " + "; ".join(fg["messages"]))
        new = hf
    if cmp_key(new) == cmp_key(orig):
        return None, d, w + ["수정안이 원문과 동일 → 변경 없음"]
    return new, d, w


# ============================================================ PPTX
def find_shape(shapes, path):
    for shp in shapes:
        if shp.shape_id == path[0]:
            if len(path) == 1:
                return shp
            if hasattr(shp, "shapes"):
                return find_shape(shp.shapes, path[1:])
    return None


def iter_text_shapes(shapes):
    for shp in shapes:
        if shp.shape_type is not None and "GROUP" in str(shp.shape_type):
            yield from iter_text_shapes(shp.shapes)
        elif getattr(shp, "has_text_frame", False) and shp.has_text_frame:
            yield shp


def set_paragraph_text(par, new_text: str):
    """첫 Run의 서식(rPr)을 유지하고 텍스트만 교체. 나머지 run/br/fld 제거."""
    p = par._p
    runs = p.findall(f"{{{A_NS}}}r")
    if not runs:
        r = par.add_run()
        r.text = new_text
        return
    first = runs[0]
    for el in list(p):
        tag = el.tag.split("}")[-1]
        if tag in ("r", "br", "fld") and el is not first:
            p.remove(el)
    segs = new_text.split("\n")
    first.find(f"{{{A_NS}}}t").text = segs[0]
    anchor = first
    rpr = first.find(f"{{{A_NS}}}rPr")
    for seg in segs[1:]:
        br = p.makeelement(f"{{{A_NS}}}br", {})
        if rpr is not None:
            br.append(copy.deepcopy(rpr))
        anchor.addnext(br)
        nr = copy.deepcopy(first)
        nr.find(f"{{{A_NS}}}t").text = seg
        br.addnext(nr)
        anchor = nr


def para_size(par, default):
    for r in par.runs:
        if r.font.size:
            return r.font.size.pt
    if par.font.size:
        return par.font.size.pt
    return default


def estimate_height(tf, width_pt, default_size, override=None):
    """텍스트 프레임 전체 높이 추정 (pt). override={par_index: size}"""
    h = 0.0
    for i, par in enumerate(tf.paragraphs):
        size = (override or {}).get(i) or para_size(par, default_size)
        txt = par.text.replace("\v", "\n")
        lines = 0
        for seg in txt.split("\n") or [""]:
            per_line = max(1.0, width_pt / size)
            lines += max(1, math.ceil(text_units(seg) / per_line)) if seg else 1
        h += lines * size * 1.2
    return h


def frame_box(shp):
    from pptx.util import Emu
    bp = shp.text_frame._txBody.find(f"{{{A_NS}}}bodyPr")
    def ins(name, dflt):
        v = bp.get(name) if bp is not None else None
        return int(v) if v else dflt
    w = (shp.width or 0) - ins("lIns", 91440) - ins("rIns", 91440)
    h = (shp.height or 0) - ins("tIns", 45720) - ins("bIns", 45720)
    autofit = None
    if bp is not None:
        if bp.find(f"{{{A_NS}}}spAutoFit") is not None:
            autofit = "shape"
        elif bp.find(f"{{{A_NS}}}normAutofit") is not None:
            autofit = "shrink"
    return Emu(max(w, 1)).pt, Emu(max(h, 1)).pt, autofit


def fit_single_line(shp, pi, default_size, before_w):
    """줄바꿈 없는(wrap=none) 한 줄 박스: 폭 기준. 허용 폭 = max(박스 폭, 원문 폭)"""
    from pptx.util import Emu, Pt
    par = shp.text_frame.paragraphs[pi]
    size = para_size(par, default_size)
    limit = max(Emu(shp.width or 0).pt, before_w)
    need = text_units(par.text) * size
    if need <= limit * 1.05:
        return None, None
    min_size = max(size - 2.0, size * 0.9, 9.0)
    s = size
    while s - 0.5 >= min_size - 1e-6:
        s -= 0.5
        if text_units(par.text) * s <= limit * 1.05:
            for r in par.runs:
                r.font.size = Pt(s)
            return f"한 줄 박스 — 폰트 {size:g}→{s:g}pt 최소 조정", None
    return None, f"한 줄 박스 폭 초과 (추정 {need:.0f}pt > 허용 {limit:.0f}pt, 약 {int(limit / size)}자) — 문장 축약 필요, 폰트는 유지"


def fit_paragraph(shp, pi, default_size, before_h):
    """Overflow 처리. → (note, warning)"""
    from pptx.util import Pt
    tf = shp.text_frame
    w_pt, h_pt, autofit = frame_box(shp)
    after_h = estimate_height(tf, w_pt, default_size)
    limit = max(h_pt, before_h)  # 원래도 넘쳤다면 원래 높이까지는 허용
    if after_h <= limit * 1.02:
        return None, None
    if autofit == "shape":
        return "박스 자동 확장(spAutoFit) — 겹침 여부 육안 확인", None
    par = tf.paragraphs[pi]
    orig_size = para_size(par, default_size)
    min_size = max(orig_size - 2.0, orig_size * 0.9, 9.0)
    s = orig_size
    while s - 0.5 >= min_size - 1e-6:
        s -= 0.5
        if estimate_height(tf, w_pt, default_size, {pi: s}) <= limit * 1.02:
            for r in par.runs:
                r.font.size = Pt(s)
            return f"폰트 {orig_size:g}→{s:g}pt 최소 조정", None
    return None, f"Overflow 가능 (추정 {after_h:.0f}pt > 박스 {limit:.0f}pt) — 문장 축약 필요, 폰트는 유지"


def apply_pptx(orig: Path, out: Path, rows: list[dict], meta: dict, auto: bool, force: bool) -> dict:
    from pptx import Presentation

    prs = Presentation(str(orig))
    log = {"applied": [], "skipped": [], "warnings": []}
    locs = meta.get("locators", {})
    styles = meta.get("styles", {})
    for row in rows:
        uid = row["Unit ID"]
        new, d, warns = resolve_decision(row, auto, force, set(meta.get("corpus_numbers", [])))
        entry = {"no": row.get("No"), "unit_id": uid, "location": row.get("Source Location"), "decision": d,
                 "original": row.get("Original"), "new": new, "warnings": warns}
        if new is None:
            (log["skipped"]).append(entry)
            if any("Warning" in x or "빈칸" in x or "ERROR" in x or "비어" in x or "알 수 없는" in x for x in warns):
                log["warnings"].append(entry)
            continue
        loc = locs.get(uid) or {}
        if not loc:
            loc = parse_uid(uid)
        slide_no = loc.get("slide") or loc.get("page")
        if not slide_no or slide_no > len(prs.slides):
            entry["warnings"].append("슬라이드 위치를 찾을 수 없음")
            log["skipped"].append(entry)
            log["warnings"].append(entry)
            continue
        slide = prs.slides[slide_no - 1]
        target = None  # (shape, paragraph_index, mode)
        okey = cmp_key(row.get("Original"))
        if loc.get("type") == "pptx":
            shp = find_shape(slide.shapes, loc["shape_path"])
            if shp is not None and shp.has_text_frame and loc["para"] < len(shp.text_frame.paragraphs):
                if cmp_key(shp.text_frame.paragraphs[loc["para"]].text) == okey:
                    target = (shp, loc["para"], "para")
        elif loc.get("type") == "pptx_table":
            shp = find_shape(slide.shapes, loc["shape_path"])
            if shp is not None and shp.has_table:
                cell = shp.table.cell(loc["row"], loc["col"])
                if loc["para"] < len(cell.text_frame.paragraphs) and cmp_key(cell.text_frame.paragraphs[loc["para"]].text) == okey:
                    target = (cell, loc["para"], "cell")
        if target is None:
            # PDF Review 또는 위치 변경 → 같은 장표에서 원문 텍스트로 매칭
            for shp in iter_text_shapes(slide.shapes):
                pars = shp.text_frame.paragraphs
                for pi, par in enumerate(pars):
                    if cmp_key(par.text) == okey and okey:
                        target = (shp, pi, "para")
                        break
                if target:
                    break
                if okey and cmp_key(shp.text_frame.text) == okey and len(pars) > 1:
                    target = (shp, 0, "shape")
                    break
            if target and loc.get("type") in ("pptx", "pptx_table"):
                entry["warnings"].append("원래 위치에서 텍스트가 달라 같은 장표의 동일 문장으로 매칭")
        if target is None:
            entry["warnings"].append("원본의 현재 텍스트가 Review Original과 달라 반영하지 않음 (Stale)")
            log["skipped"].append(entry)
            log["warnings"].append(entry)
            continue
        obj, pi, mode = target
        default_size = (styles.get(uid) or {}).get("size") or 18.0
        tf = obj.text_frame
        is_shape = mode != "cell" and hasattr(obj, "width") and hasattr(obj, "shape_id")
        before_h = estimate_height(tf, frame_box(obj)[0], default_size) if is_shape else 0
        bp = tf._txBody.find(f"{{{A_NS}}}bodyPr")
        one_line = is_shape and bp is not None and bp.get("wrap") == "none"
        before_w = text_units(tf.paragraphs[pi].text) * para_size(tf.paragraphs[pi], default_size) if one_line else 0
        if mode == "shape":
            pars = tf.paragraphs
            set_paragraph_text(pars[0], new)
            for extra in pars[1:]:
                extra._p.getparent().remove(extra._p)
        else:
            set_paragraph_text(tf.paragraphs[pi], new)
        if is_shape:
            note, warn = (fit_single_line(obj, pi, default_size, before_w) if one_line
                          else fit_paragraph(obj, pi, default_size, before_h))
            if note:
                entry["warnings"].append(note)
            if warn:
                entry["warnings"].append(warn)
                log["warnings"].append(entry)
        log["applied"].append(entry)
    prs.save(str(out))
    return log


def parse_uid(uid: str) -> dict:
    m = re.search(r"\|S(\d+)\|sh([\d.]+)\|r(\d+)c(\d+)\|p(\d+)$", uid)
    if m:
        return {"type": "pptx_table", "slide": int(m.group(1)), "shape_path": [int(x) for x in m.group(2).split(".")],
                "row": int(m.group(3)), "col": int(m.group(4)), "para": int(m.group(5))}
    m = re.search(r"\|S(\d+)\|sh([\d.]+)\|p(\d+)$", uid)
    if m:
        return {"type": "pptx", "slide": int(m.group(1)), "shape_path": [int(x) for x in m.group(2).split(".")],
                "para": int(m.group(3))}
    m = re.search(r"\|P(\d+)\|b(\d+)$", uid)
    if m:
        return {"type": "pdf", "page": int(m.group(1)), "block": int(m.group(2))}
    m = re.search(r"\|(.+)!([A-Z]+\d+)$", uid)
    if m:
        return {"type": "xlsx", "sheet": m.group(1), "cell": m.group(2)}
    m = re.search(r"\|para(\d+)$", uid)
    if m:
        return {"type": "docx", "para": int(m.group(1))}
    m = re.search(r"\|L(\d+)$", uid)
    if m:
        return {"type": "txt", "line": int(m.group(1))}
    return {}


# ============================================================ XLSX (XML 단위)
NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"


def apply_xlsx(orig: Path, out: Path, rows: list[dict], meta: dict, auto: bool, force: bool) -> dict:
    from lxml import etree

    log = {"applied": [], "skipped": [], "warnings": []}
    zin = zipfile.ZipFile(str(orig))
    parts = {n: zin.read(n) for n in zin.namelist()}
    wb = etree.fromstring(parts["xl/workbook.xml"])
    rels = etree.fromstring(parts["xl/_rels/workbook.xml.rels"])
    rid2target = {r.get("Id"): r.get("Target") for r in rels.findall(f"{{{NS_PKG_REL}}}Relationship")}
    sheet2part = {}
    for s in wb.find(f"{{{NS_MAIN}}}sheets"):
        tgt = rid2target.get(s.get(f"{{{NS_REL}}}id"), "")
        tgt = tgt.lstrip("/")
        sheet2part[s.get("name")] = tgt if tgt.startswith("xl/") else "xl/" + tgt
    sst = etree.fromstring(parts["xl/sharedStrings.xml"]) if "xl/sharedStrings.xml" in parts else None
    sis = sst.findall(f"{{{NS_MAIN}}}si") if sst is not None else []
    sheets_xml = {}

    def si_text(si):
        return "".join(t.text or "" for t in si.iter(f"{{{NS_MAIN}}}t"))

    locs = meta.get("locators", {})
    for row in rows:
        uid = row["Unit ID"]
        new, d, warns = resolve_decision(row, auto, force, set(meta.get("corpus_numbers", [])))
        entry = {"no": row.get("No"), "unit_id": uid, "location": row.get("Source Location"), "decision": d,
                 "original": row.get("Original"), "new": new, "warnings": warns}
        if new is None:
            log["skipped"].append(entry)
            if any("빈칸" in x or "ERROR" in x or "비어" in x or "알 수 없는" in x for x in warns):
                log["warnings"].append(entry)
            continue
        loc = locs.get(uid) or parse_uid(uid)
        if loc.get("type") != "xlsx":
            entry["warnings"].append("XLSX 위치가 아님 → 반영 안 함")
            log["skipped"].append(entry)
            log["warnings"].append(entry)
            continue
        part = sheet2part.get(loc["sheet"])
        if not part or part not in parts:
            entry["warnings"].append(f"시트 '{loc['sheet']}' 없음")
            log["skipped"].append(entry)
            log["warnings"].append(entry)
            continue
        if part not in sheets_xml:
            sheets_xml[part] = etree.fromstring(parts[part])
        sx = sheets_xml[part]
        cell = sx.find(f".//{{{NS_MAIN}}}c[@r='{loc['cell']}']")
        if cell is None:
            entry["warnings"].append("셀 없음")
            log["skipped"].append(entry)
            log["warnings"].append(entry)
            continue
        t = cell.get("t")
        if cell.find(f"{{{NS_MAIN}}}f") is not None:
            entry["warnings"].append("수식 셀 → 수식 보존, 반영 안 함")
            log["skipped"].append(entry)
            log["warnings"].append(entry)
            continue
        if t == "s":
            idx = int(cell.find(f"{{{NS_MAIN}}}v").text)
            cur = si_text(sis[idx])
        elif t == "inlineStr":
            cur = "".join(x.text or "" for x in cell.iter(f"{{{NS_MAIN}}}t"))
        else:
            entry["warnings"].append("문자열 셀 아님 → 반영 안 함")
            log["skipped"].append(entry)
            log["warnings"].append(entry)
            continue
        if cmp_key(cur) != cmp_key(row.get("Original")):
            entry["warnings"].append("셀의 현재 값이 Review Original과 다름 (Stale) → 반영 안 함")
            log["skipped"].append(entry)
            log["warnings"].append(entry)
            continue
        if sst is not None:
            si = etree.SubElement(sst, f"{{{NS_MAIN}}}si")
            te = etree.SubElement(si, f"{{{NS_MAIN}}}t")
            te.text = new
            te.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            sis.append(si)
            for child in list(cell):
                if child.tag in (f"{{{NS_MAIN}}}v", f"{{{NS_MAIN}}}is"):
                    cell.remove(child)
            v = etree.SubElement(cell, f"{{{NS_MAIN}}}v")
            v.text = str(len(sis) - 1)
            cell.set("t", "s")
        else:
            for child in list(cell):
                if child.tag in (f"{{{NS_MAIN}}}v", f"{{{NS_MAIN}}}is"):
                    cell.remove(child)
            is_ = etree.SubElement(cell, f"{{{NS_MAIN}}}is")
            te = etree.SubElement(is_, f"{{{NS_MAIN}}}t")
            te.text = new
            cell.set("t", "inlineStr")
        log["applied"].append(entry)
    if sst is not None:
        sst.set("uniqueCount", str(len(sis)))
        parts["xl/sharedStrings.xml"] = etree.tostring(sst, xml_declaration=True, encoding="UTF-8", standalone=True)
    for part, sx in sheets_xml.items():
        parts[part] = etree.tostring(sx, xml_declaration=True, encoding="UTF-8", standalone=True)
    with zipfile.ZipFile(str(out), "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            zout.writestr(info, parts[info.filename])
    zin.close()
    return log


# ============================================================ DOCX / MD / TXT (보조)
def apply_docx(orig: Path, out: Path, rows, meta, auto, force):
    import docx
    d = docx.Document(str(orig))
    log = {"applied": [], "skipped": [], "warnings": []}
    locs = meta.get("locators", {})
    for row in rows:
        new, dec, warns = resolve_decision(row, auto, force, set(meta.get("corpus_numbers", [])))
        entry = {"no": row.get("No"), "unit_id": row["Unit ID"], "location": row.get("Source Location"), "decision": dec,
                 "original": row.get("Original"), "new": new, "warnings": warns}
        loc = locs.get(row["Unit ID"]) or parse_uid(row["Unit ID"])
        if new is None or loc.get("type") != "docx":
            log["skipped"].append(entry)
            continue
        p = d.paragraphs[loc["para"]]
        if cmp_key(p.text) != cmp_key(row.get("Original")):
            entry["warnings"].append("Stale → 반영 안 함")
            log["skipped"].append(entry)
            log["warnings"].append(entry)
            continue
        runs = p.runs
        if runs:
            runs[0].text = new
            for r in runs[1:]:
                r._r.getparent().remove(r._r)
        else:
            p.add_run(new)
        log["applied"].append(entry)
    d.save(str(out))
    return log


def apply_text(orig: Path, out: Path, rows, meta, auto, force):
    lines = orig.read_text(encoding="utf-8").splitlines(keepends=True)
    log = {"applied": [], "skipped": [], "warnings": []}
    locs = meta.get("locators", {})
    for row in rows:
        new, dec, warns = resolve_decision(row, auto, force, set(meta.get("corpus_numbers", [])))
        entry = {"no": row.get("No"), "unit_id": row["Unit ID"], "location": row.get("Source Location"), "decision": dec,
                 "original": row.get("Original"), "new": new, "warnings": warns}
        loc = locs.get(row["Unit ID"]) or parse_uid(row["Unit ID"])
        if new is None or loc.get("type") not in ("md", "txt"):
            log["skipped"].append(entry)
            continue
        i = loc["line"] - 1
        line = lines[i]
        okey = cmp_key(row.get("Original"))
        m = re.match(r"^(\s*(?:#{1,6}\s+|>\s+|[-*+]\s+|\d+\.\s+|[•·▪■□○◦\-–—*※▶►◆●]\s*)?)(.*?)(\s*)$", line, re.S)
        prefix, body, tail = m.group(1), m.group(2), m.group(3)
        if cmp_key(re.sub(r"\*\*(.+?)\*\*", r"\1", body)) != okey:
            entry["warnings"].append("Stale → 반영 안 함")
            log["skipped"].append(entry)
            log["warnings"].append(entry)
            continue
        lines[i] = prefix + new + tail
        log["applied"].append(entry)
    out.write_text("".join(lines), encoding="utf-8")
    return log


# ============================================================ Learning Loop
def append_learning(rows: list[dict], meta: dict, log_path: Path, project: str):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(log_path, "a", encoding="utf-8") as f:
        for row in rows:
            d = str(row.get("Decision") or "").strip().upper()
            if d not in DECISIONS:
                continue
            final = {"ACCEPT": row.get("AI Recommended"), "EDIT": row.get("Human Final")}.get(d) or row.get("Original")
            rec = {
                "ts": dt.datetime.now().isoformat(timespec="seconds"), "project": project,
                "domain": meta.get("domains") or [], "industry": meta.get("industry") or [],
                "audience": row.get("Audience"), "message_type": row.get("Message Type"),
                "status": row.get("Status"), "category": row.get("Category"), "decision": d,
                "original": row.get("Original"), "ai_recommended": row.get("AI Recommended"),
                "human_final": row.get("Human Final"), "final": final,
                "reason": row.get("Reason"), "comment": row.get("Comment"),
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser(description="키 메시지: 승인 메시지 반영 (APPLY/AUTO)")
    ap.add_argument("original", help="원본 PPTX/XLSX (DOCX/MD/TXT 보조 지원)")
    ap.add_argument("review", help="사람이 Decision을 채운 Review Excel")
    ap.add_argument("-o", "--out", help="출력 경로 (기본: 원본명_KeyMessage_v2.확장자)")
    ap.add_argument("--auto", action="store_true", help="AUTO 모드: 빈 Decision을 자동 결정 (내부 초안용)")
    ap.add_argument("--force", action="store_true", help="Fact Guard ERROR인 ACCEPT도 반영 (권장하지 않음)")
    ap.add_argument("--learning-log", default=str(DEFAULT_LEARNING_LOG))
    ap.add_argument("--no-learning", action="store_true")
    a = ap.parse_args()

    orig = Path(a.original).resolve()
    if not orig.exists():
        raise SystemExit(f"[ERROR] 원본 없음: {orig}")
    rows, meta = read_review(Path(a.review))
    # Multi-source Review: 이 원본에 해당하는 행만. PDF Review → 같은 이름의 PPTX 원본 허용
    def match(row):
        sf = str(row.get("Source File") or "")
        return sf == orig.name or Path(sf).stem == orig.stem
    mine = [r for r in rows if match(r)]
    if not mine:
        raise SystemExit(f"[ERROR] Review에 '{orig.name}' 행이 없습니다. Source File 컬럼을 확인하세요.")
    out = safe_output_path(orig, "_KeyMessage_v2", out=a.out)
    ext = orig.suffix.lower()
    if ext == ".pptx":
        log = apply_pptx(orig, out, mine, meta, a.auto, a.force)
    elif ext in (".xlsx", ".xlsm"):
        log = apply_xlsx(orig, out, mine, meta, a.auto, a.force)
    elif ext == ".docx":
        log = apply_docx(orig, out, mine, meta, a.auto, a.force)
    elif ext in (".md", ".txt"):
        log = apply_text(orig, out, mine, meta, a.auto, a.force)
    elif ext == ".pdf":
        raise SystemExit("[STOP] PDF는 REVIEW 전용입니다. 원본 PPTX를 지정하면 PDF Review 결과를 PPTX에 반영합니다.")
    else:
        raise SystemExit(f"[ERROR] 지원하지 않는 형식: {ext}")
    log.update({"original": str(orig), "output": str(out), "review": str(Path(a.review).resolve()),
                "mode": "AUTO" if a.auto else "APPLY", "time": dt.datetime.now().isoformat(timespec="seconds")})
    # PPTX/XLSX: <수정본>_apply_log.json (validate_output 기본값) / 보조 형식은 확장자를 붙여 이름 충돌 방지
    log_path = out.with_name(out.stem + ("_apply_log.json" if ext in (".pptx", ".xlsx", ".xlsm") else f"_{ext.lstrip('.')}_apply_log.json"))
    dump_json(log, log_path)
    if not a.no_learning and not a.auto:
        n = append_learning(mine, meta, Path(a.learning_log), orig.stem)
        print(f"[OK] Learning Loop: {n}건 → {a.learning_log}")
    print(f"[OK] {log['mode']}: applied={len(log['applied'])} skipped={len(log['skipped'])} warnings={len(log['warnings'])}")
    for e in log["applied"]:
        print(f"   ✔ #{e['no']} [{e['decision']}] {e.get('location')}: {str(e['original'])[:30]} → {str(e['new'])[:40]}"
              + (f"  ({'; '.join(e['warnings'])})" if e["warnings"] else ""))
    for e in log["warnings"]:
        if e not in log["applied"]:
            print(f"   ⚠ #{e['no']} [{e['decision']}] {e.get('location')}: {'; '.join(e['warnings'])}")
    print(f"[OK] 수정본 → {out}\n[OK] 로그 → {log_path}")


if __name__ == "__main__":
    main()
