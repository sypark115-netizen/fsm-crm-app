# -*- coding: utf-8 -*-
"""File Parser + Content Normalizer.

PPTX / PDF / XLSX / DOCX / MD / TXT → 공통 content.json

사용:
  python extract_content.py 고객_RFP.pdf 요구사항.xlsx 제안서.pptx -o work/content.json
  python extract_content.py 제안서.pptx --role 제안서.pptx=proposal -o work/content.json

각 unit 은 메시지 분석 로직과 무관한 '정규화된 텍스트 조각'이다.
  id, source_type, source_file, source_role, location, page, kind, text, locator, style, geom
분석(Governing/Key 판정)은 analyze_messages.py 가 한다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from km_common import SCHEMA_VERSION, dump_json, norm_text  # noqa: E402

ROLE_HINTS = [
    ("rfp", r"rfp|제안\s*요청|과업\s*지시|과업\s*내용|입찰|공고"),
    ("requirements", r"요구\s*사항|requirement|req[_\- ]|기능\s*명세"),
    ("reference", r"reference|레퍼런스|실적|사례|case"),
    ("proposal", r"제안서|proposal|발표|pt|장표|storyline|스토리라인|메시지"),
]

FOOTER_RE = re.compile(r"^(\d{1,3}|-\s*\d+\s*-|page\s*\d+|confidential|copyright.*|ⓒ.*|©.*|대외비|내부용)$", re.I)


def guess_role(path: Path, text_sample: str, ext: str) -> str:
    name = path.stem.lower()
    for role, pat in ROLE_HINTS:
        if re.search(pat, name, re.I):
            return role
    sample = text_sample[:4000]
    if re.search(r"제안\s*요청서|과업\s*내용서|제안요청", sample):
        return "rfp"
    if ext == ".pptx":
        return "proposal"
    if re.search(r"요구사항\s*(ID|번호|고유)|요구사항\s*명", sample):
        return "requirements"
    return "proposal" if ext in (".pdf", ".docx", ".md", ".txt") else "other"


# ------------------------------------------------------------------ PPTX
def body_props(tf) -> dict:
    """텍스트 박스 줄바꿈·자동맞춤 속성 (한 줄 박스 Overflow 판단용)"""
    ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
    bp = tf._txBody.find(ns + "bodyPr")
    if bp is None:
        return {}
    fit = "shape" if bp.find(ns + "spAutoFit") is not None else "shrink" if bp.find(ns + "normAutofit") is not None else None
    return {"wrap": bp.get("wrap") or "square", "autofit": fit}


def extract_pptx(path: Path, tag: str) -> tuple[list, dict]:
    from pptx import Presentation
    from pptx.util import Emu

    prs = Presentation(str(path))
    sw, sh = int(prs.slide_width or 0), int(prs.slide_height or 0)
    units = []

    def font_size_of(par, shape):
        for r in par.runs:
            if r.font.size:
                return r.font.size.pt
        if par.font.size:
            return par.font.size.pt
        try:
            if shape.is_placeholder:
                t = shape.placeholder_format.type
                if t is not None and "TITLE" in str(t):
                    return 28.0
        except Exception:
            pass
        return 18.0

    def bold_of(par):
        return any(bool(r.font.bold) for r in par.runs) or bool(par.font.bold)

    def walk(shapes, path_ids, slide_no, offset=(0, 0)):
        for shp in shapes:
            sid = shp.shape_id
            spath = path_ids + [sid]
            if shp.shape_type is not None and "GROUP" in str(shp.shape_type):
                walk(shp.shapes, spath, slide_no)
                continue
            geom = {
                "left": int(shp.left or 0), "top": int(shp.top or 0),
                "width": int(shp.width or 0), "height": int(shp.height or 0),
                "slide_w": sw, "slide_h": sh,
            }
            ph_type = None
            if getattr(shp, "is_placeholder", False):
                try:
                    ph_type = str(shp.placeholder_format.type).split(".")[-1].split(" ")[0]
                except Exception:
                    ph_type = "PLACEHOLDER"
            if getattr(shp, "has_table", False) and shp.has_table:
                tbl = shp.table
                for ri, row in enumerate(tbl.rows):
                    for ci, cell in enumerate(row.cells):
                        for pi, par in enumerate(cell.text_frame.paragraphs):
                            t = norm_text(par.text)
                            if not t:
                                continue
                            units.append({
                                "id": f"{tag}|S{slide_no}|sh{'.'.join(map(str, spath))}|r{ri}c{ci}|p{pi}",
                                "page": slide_no,
                                "location": f"Slide {slide_no} / Table '{shp.name}' R{ri+1}C{ci+1}",
                                "kind": "table_cell",
                                "text": t,
                                "locator": {"type": "pptx_table", "slide": slide_no, "shape_path": spath,
                                            "row": ri, "col": ci, "para": pi},
                                "style": {"size": font_size_of(par, shp), "bold": bold_of(par), "level": par.level},
                                "geom": geom, "shape_name": shp.name, "placeholder": None,
                            })
                continue
            if not getattr(shp, "has_text_frame", False) or not shp.has_text_frame:
                continue
            tf = shp.text_frame
            n_par = len([p for p in tf.paragraphs if norm_text(p.text)])
            for pi, par in enumerate(tf.paragraphs):
                t = norm_text(par.text)
                if not t:
                    continue
                kind = "title" if ph_type and "TITLE" in ph_type and "SUB" not in ph_type else (
                    "subtitle" if ph_type and "SUBTITLE" in ph_type else "text")
                units.append({
                    "id": f"{tag}|S{slide_no}|sh{'.'.join(map(str, spath))}|p{pi}",
                    "page": slide_no,
                    "location": f"Slide {slide_no} / Shape '{shp.name}'" + (f" ¶{pi+1}" if n_par > 1 else ""),
                    "kind": kind,
                    "text": t,
                    "locator": {"type": "pptx", "slide": slide_no, "shape_path": spath, "para": pi},
                    "style": {"size": font_size_of(par, shp), "bold": bold_of(par), "level": par.level,
                              "n_par_in_shape": n_par, **body_props(tf)},
                    "geom": geom, "shape_name": shp.name, "placeholder": ph_type,
                })

    for i, slide in enumerate(prs.slides, start=1):
        walk(slide.shapes, [], i)
        # 발표자 노트는 Context로만 사용
        if slide.has_notes_slide:
            nt = norm_text(slide.notes_slide.notes_text_frame.text if slide.notes_slide.notes_text_frame else "")
            if nt:
                units.append({"id": f"{tag}|S{i}|notes", "page": i, "location": f"Slide {i} / Notes",
                              "kind": "notes", "text": nt, "locator": {"type": "pptx_notes", "slide": i},
                              "style": {}, "geom": {}, "shape_name": "notes", "placeholder": None})
    meta = {"slides": len(prs.slides), "slide_w": sw, "slide_h": sh,
            "layouts": [s.slide_layout.name for s in prs.slides]}
    return units, meta


# ------------------------------------------------------------------ PDF
BULLET_RE = re.compile(r"^\s*([•·▪■□○◦‧\-–—*※▶▷►◆◇●]|\d+[.)]|[①-⑳]|[가-하][.)])\s*")


INCOMPLETE_END = re.compile(r"[가-힣](을|를|은|는|의|에|와|과|으로|에서|하고|하며|하여|및|이|가)$|[,·]$")
UNIT_AFTER = r"(?:건|일|년|월|대|개|명|회|시간|분|단계|인당|배|차|번|억|만|%)"


def fix_pdf_spacing(t: str) -> str:
    """대체 글꼴 때문에 생긴 '영문/숫자 + 조사·단위' 사이 공백과 문장부호 앞 공백 제거 (표시용)."""
    t = re.sub(r"(?<=[A-Za-z0-9%)\]]) (?=(?:을|를|이|가|은|는|와|과|의|로|으로|에|에서|도|만)(?![가-힣]))", "", t)
    t = re.sub(r"(?<=[0-9]) (?=" + UNIT_AFTER + r")", "", t)
    t = re.sub(r" (?=[.,)\]:;])", "", t)
    t = re.sub(r"(?<=[(\[]) ", "", t)
    t = re.sub(r" ?· ?", "·", t)
    return t


def _pdf_lines(page):
    """문자 단위로 줄을 다시 구성: 글꼴이 섞인(한글/영문 대체 글꼴) PPT Export PDF에서도 어순 유지.
    같은 높이라도 가로 간격이 크면(2단 배치) 다른 줄로 분리."""
    chars = [c for c in page.chars if c.get("text") and c["text"].strip() != "" or c.get("text") == " "]
    if not chars:
        return []
    for c in chars:
        c["_cy"] = (c["top"] + c["bottom"]) / 2
    chars.sort(key=lambda c: (c["_cy"], c["x0"]))
    rows = []
    for c in chars:
        if rows and abs(rows[-1]["cy"] - c["_cy"]) <= max(1.5, c["size"] * 0.45):
            rows[-1]["chars"].append(c)
        else:
            rows.append({"cy": c["_cy"], "chars": [c]})
    lines = []
    for r in rows:
        cs = sorted(r["chars"], key=lambda c: c["x0"])
        seg = None
        for c in cs:
            if c["text"] == " ":
                if seg is not None:
                    seg["space"] = True
                continue
            size = c["size"]
            if seg is not None and c["x0"] - seg["x1"] > size * 2.0:
                lines.append(seg)
                seg = None
            if seg is None:
                seg = {"text": c["text"], "x0": c["x0"], "x1": c["x1"], "top": c["top"], "bottom": c["bottom"],
                       "size": size, "bold": "bold" in (c.get("fontname") or "").lower(), "space": False}
                continue
            gap = c["x0"] - seg["x1"]
            if seg["space"] or gap > size * 0.22:
                seg["text"] += " "
            seg["text"] += c["text"]
            seg["space"] = False
            seg["x1"] = max(seg["x1"], c["x1"])
            seg["top"] = min(seg["top"], c["top"])
            seg["bottom"] = max(seg["bottom"], c["bottom"])
            seg["size"] = max(seg["size"], size)
            seg["bold"] = seg["bold"] or "bold" in (c.get("fontname") or "").lower()
        if seg is not None:
            lines.append(seg)
    lines.sort(key=lambda l: (round(l["top"]), l["x0"]))
    return lines


def extract_pdf(path: Path, tag: str) -> tuple[list, dict]:
    import pdfplumber

    units = []
    with pdfplumber.open(str(path)) as pdf:
        n_pages = len(pdf.pages)
        for pno, page in enumerate(pdf.pages, start=1):
            lines = _pdf_lines(page)
            if not lines:
                continue
            # 열(column) 오른쪽 끝 추정: x0가 비슷한 줄들의 최대 x1
            for ln in lines:
                ln["col_right"] = max(l["x1"] for l in lines if abs(l["x0"] - ln["x0"]) < ln["size"] * 1.5
                                      and abs(l["size"] - ln["size"]) < 0.6)
            # 문단 병합: 같은 크기·같은 열·바로 아래 줄이고, 앞줄이 열 끝까지 찼을 때(=자동 줄바꿈)만
            paras = []
            for ln in sorted(lines, key=lambda l: (round(l["x0"] / 4), l["top"])):
                t = ln["text"].strip()
                if not t:
                    continue
                merged = False
                for p in reversed(paras[-6:]):
                    same_col = abs(p["x0"] - ln["x0"]) < ln["size"] * 1.5
                    same_size = abs(p["size"] - ln["size"]) < 0.6
                    close = 0 <= ln["top"] - p["bottom"] < ln["size"] * 0.8
                    # 자동 줄바꿈 판단: 앞줄이 열 오른쪽 끝까지 찼고, 페이지 폭의 40% 이상인 긴 줄
                    full = (p["last_x1"] >= p["col_right"] - ln["size"] * 1.2
                            and (p["last_x1"] - p["x0"]) >= float(page.width) * 0.4) or bool(re.match(r"^[a-z,.)\]]", t)) \
                        or bool(INCOMPLETE_END.search(p["text"]))  # '~를', '~것이' 처럼 문장이 끝나지 않은 줄
                    if same_col and same_size and close and full and not BULLET_RE.match(t) \
                            and not p["text"].endswith((".", "다", ":", "요")):
                        p["text"] += " " + t
                        p["bottom"] = ln["bottom"]
                        p["last_x1"] = ln["x1"]
                        p["x1"] = max(p["x1"], ln["x1"])
                        p["lines"] += 1
                        merged = True
                        break
                if not merged:
                    paras.append(dict(ln, text=t, lines=1, last_x1=ln["x1"]))
            paras.sort(key=lambda p: (round(p["top"]), p["x0"]))
            for qi, p in enumerate(paras):
                t = fix_pdf_spacing(norm_text(p["text"]))
                if FOOTER_RE.match(t):
                    continue
                units.append({
                    "id": f"{tag}|P{pno}|b{qi}",
                    "page": pno,
                    "location": f"Page {pno} / Block {qi+1}",
                    "kind": "text",
                    "text": t,
                    "locator": {"type": "pdf", "page": pno, "block": qi},
                    "style": {"size": round(p["size"], 1), "bold": p["bold"], "level": 1 if BULLET_RE.match(t) else 0},
                    "geom": {"left": p["x0"], "top": p["top"], "width": p["x1"] - p["x0"],
                             "height": p["bottom"] - p["top"], "slide_w": float(page.width), "slide_h": float(page.height)},
                    "shape_name": "", "placeholder": None,
                })
    return units, {"pages": n_pages}


# ------------------------------------------------------------------ XLSX
HEADER_WORDS = re.compile(
    r"요구\s*사항|requirement|내용|설명|description|id|번호|no\.?|구분|항목|분류|"
    r"governing|key\s*message|헤드\s*메시지|메시지|장표|slide|섹션|section|"
    r"고객사|사업명|프로젝트|기간|규모|성과|결과|레퍼런스|reference|비고", re.I)


def extract_xlsx(path: Path, tag: str) -> tuple[list, dict]:
    import openpyxl

    wb_f = openpyxl.load_workbook(str(path), data_only=False)
    try:
        wb_v = openpyxl.load_workbook(str(path), data_only=True)
    except Exception:
        wb_v = wb_f
    units, sheets = [], []
    for ws in wb_f.worksheets:
        wv = wb_v[ws.title]
        info = {"name": ws.title, "max_row": ws.max_row, "max_col": ws.max_column, "header_row": None,
                "headers": {}, "formula_cells": 0}
        # Header 탐지 (상위 10행 중 Header 단어가 가장 많은 행)
        best, best_row = 0, None
        for r in range(1, min(ws.max_row, 10) + 1):
            vals = [ws.cell(r, c).value for c in range(1, ws.max_column + 1)]
            score = sum(1 for v in vals if isinstance(v, str) and HEADER_WORDS.search(v) and len(v) <= 30)
            if score > best:
                best, best_row = score, r
        if best >= 2:
            info["header_row"] = best_row
            for c in range(1, ws.max_column + 1):
                v = ws.cell(best_row, c).value
                if isinstance(v, str) and v.strip():
                    info["headers"][c] = norm_text(v)
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                if v is None:
                    continue
                is_formula = isinstance(v, str) and v.startswith("=")
                if is_formula:
                    info["formula_cells"] += 1
                    v_disp = wv[cell.coordinate].value
                    if not isinstance(v_disp, str):
                        continue
                    text, editable = v_disp, False
                elif isinstance(v, str):
                    text, editable = v, True
                else:
                    continue
                t = norm_text(text)
                if not t:
                    continue
                is_header = info["header_row"] == cell.row
                header = info["headers"].get(cell.column) if info["header_row"] and cell.row > info["header_row"] else None
                units.append({
                    "id": f"{tag}|{ws.title}!{cell.coordinate}",
                    "page": None,
                    "location": f"Sheet '{ws.title}' / {cell.coordinate}" + (f" ({header})" if header else ""),
                    "kind": "header" if is_header else "cell",
                    "text": t,
                    "locator": {"type": "xlsx", "sheet": ws.title, "cell": cell.coordinate,
                                "row": cell.row, "col": cell.column, "editable": editable},
                    "style": {"header": header, "bold": bool(cell.font and cell.font.b)},
                    "geom": {}, "shape_name": "", "placeholder": None,
                })
        # 표 형식이면 행 단위 Record 도 생성 (요구사항/Reference 매칭용)
        if info["header_row"]:
            for r in range(info["header_row"] + 1, ws.max_row + 1):
                rec = {}
                for c, h in info["headers"].items():
                    v = wv.cell(r, c).value
                    if v is not None and str(v).strip():
                        rec[h] = norm_text(str(v))
                if len(rec) >= 2:
                    units.append({
                        "id": f"{tag}|{ws.title}!R{r}",
                        "page": None,
                        "location": f"Sheet '{ws.title}' / Row {r}",
                        "kind": "row",
                        "text": " | ".join(f"{k}: {v}" for k, v in rec.items()),
                        "record": rec,
                        "locator": {"type": "xlsx_row", "sheet": ws.title, "row": r},
                        "style": {}, "geom": {}, "shape_name": "", "placeholder": None,
                    })
        sheets.append(info)
    return units, {"sheets": [{k: (v if k != "headers" else {str(a): b for a, b in v.items()}) for k, v in s.items()} for s in sheets]}


# ------------------------------------------------------------------ DOCX
def extract_docx(path: Path, tag: str) -> tuple[list, dict]:
    import docx

    d = docx.Document(str(path))
    units = []
    for i, p in enumerate(d.paragraphs):
        t = norm_text(p.text)
        if not t:
            continue
        style = (p.style.name if p.style is not None else "") or ""
        kind = "heading" if re.match(r"(Heading|제목|Title)", style, re.I) else (
            "bullet" if re.search(r"List|목록", style, re.I) or BULLET_RE.match(t) else "text")
        lvl = 0
        m = re.search(r"(\d)", style)
        if kind == "heading" and m:
            lvl = int(m.group(1))
        units.append({"id": f"{tag}|para{i}", "page": None, "location": f"Paragraph {i+1}" + (f" ({style})" if style else ""),
                      "kind": kind, "text": t, "locator": {"type": "docx", "para": i},
                      "style": {"style": style, "level": lvl, "bold": any(r.bold for r in p.runs)},
                      "geom": {}, "shape_name": "", "placeholder": None})
    for ti, tbl in enumerate(d.tables):
        for ri, row in enumerate(tbl.rows):
            for ci, cell in enumerate(row.cells):
                t = norm_text(cell.text)
                if t:
                    units.append({"id": f"{tag}|t{ti}r{ri}c{ci}", "page": None,
                                  "location": f"Table {ti+1} R{ri+1}C{ci+1}", "kind": "table_cell", "text": t,
                                  "locator": {"type": "docx_table", "table": ti, "row": ri, "col": ci},
                                  "style": {}, "geom": {}, "shape_name": "", "placeholder": None})
    return units, {"paragraphs": len(d.paragraphs), "tables": len(d.tables)}


# ------------------------------------------------------------------ MD / TXT
def extract_text(path: Path, tag: str, md: bool) -> tuple[list, dict]:
    raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    units = []
    for i, line in enumerate(raw, start=1):
        s = line.rstrip()
        if not s.strip():
            continue
        kind, level, t = "text", 0, s.strip()
        if md:
            m = re.match(r"^(#{1,6})\s+(.*)", s)
            if m:
                kind, level, t = "heading", len(m.group(1)), m.group(2)
            elif re.match(r"^\s*>\s+", s):
                kind, t = "quote", re.sub(r"^\s*>\s+", "", s)
            elif re.match(r"^\s*([-*+]|\d+\.)\s+", s):
                kind = "bullet"
                level = (len(s) - len(s.lstrip())) // 2
                t = re.sub(r"^\s*([-*+]|\d+\.)\s+", "", s)
            t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
        else:
            if BULLET_RE.match(s):
                kind, t = "bullet", BULLET_RE.sub("", s, count=1)
        units.append({"id": f"{tag}|L{i}", "page": None, "location": f"Line {i}", "kind": kind,
                      "text": norm_text(t), "locator": {"type": "md" if md else "txt", "line": i},
                      "style": {"level": level}, "geom": {}, "shape_name": "", "placeholder": None})
    return units, {"lines": len(raw)}


EXTRACTORS = {".pptx": extract_pptx, ".pdf": extract_pdf, ".xlsx": extract_xlsx, ".xlsm": extract_xlsx,
              ".docx": extract_docx}


def extract_files(paths: list[str], roles: dict[str, str] | None = None) -> dict:
    roles = roles or {}
    out = {"schema_version": SCHEMA_VERSION, "sources": [], "units": []}
    used_tags = set()
    for p in paths:
        path = Path(p)
        if not path.exists():
            raise SystemExit(f"[ERROR] 파일이 없습니다: {p}")
        ext = path.suffix.lower()
        tag = re.sub(r"[|!\s]", "_", path.stem)[:40] or "file"
        base, k = tag, 2
        while tag in used_tags:
            tag, k = f"{base}_{k}", k + 1
        used_tags.add(tag)
        if ext in EXTRACTORS:
            units, meta = EXTRACTORS[ext](path, tag)
        elif ext in (".md", ".markdown"):
            units, meta = extract_text(path, tag, md=True)
        elif ext in (".txt", ".text"):
            units, meta = extract_text(path, tag, md=False)
        else:
            print(f"[SKIP] 지원하지 않는 형식: {path.name} (지원: pptx pdf xlsx docx md txt)", file=sys.stderr)
            continue
        sample = " ".join(u["text"] for u in units[:200])
        role = roles.get(path.name) or roles.get(str(p)) or guess_role(path, sample, ext)
        stype = {".xlsm": "xlsx", ".markdown": "md", ".text": "txt"}.get(ext, ext.lstrip("."))
        for u in units:
            u["source_type"] = stype
            u["source_file"] = path.name
            u["source_role"] = role
            u["source_tag"] = tag
        out["sources"].append({"file": path.name, "path": str(path.resolve()), "type": stype, "role": role,
                               "tag": tag, "units": len(units), "meta": meta})
        out["units"].extend(units)
    return out


def main():
    ap = argparse.ArgumentParser(description="키 메시지: 다중 형식 추출기")
    ap.add_argument("files", nargs="+")
    ap.add_argument("-o", "--out", required=True, help="content.json 경로")
    ap.add_argument("--role", action="append", default=[],
                    help="파일 역할 지정: 파일명=proposal|rfp|requirements|reference|other")
    a = ap.parse_args()
    roles = {}
    for r in a.role:
        k, _, v = r.partition("=")
        roles[k] = v
    data = extract_files(a.files, roles)
    dump_json(data, a.out)
    for s in data["sources"]:
        print(f"[OK] {s['file']:<40} type={s['type']:<5} role={s['role']:<12} units={s['units']}")
    print(f"[OK] content → {a.out}")


if __name__ == "__main__":
    main()
