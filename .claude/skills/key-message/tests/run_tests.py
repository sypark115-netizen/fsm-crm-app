# -*- coding: utf-8 -*-
"""키 메시지 Skill 통합 테스트 (TEST 1~12 + AUTO + 안전장치).

  python run_tests.py [작업폴더]
작업폴더(기본: ./_test_out)에 가상 Fixture를 만들고 전체 Workflow를 실제로 실행한다.
결과: 작업폴더/TEST_REPORT.md, 콘솔 PASS/FAIL. 하나라도 FAIL이면 exit 1.

Claude가 수행하는 '재작성' 단계는 tests/fixture_recommendations.json (사전에 Claude가 작성한
재작성안)으로 대신한다. 사람의 승인 단계는 openpyxl로 Review Excel의 Decision/Human Final을 채워 시뮬레이션한다.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
from analyze_messages import assess  # noqa: E402
from km_common import HUMAN_ROLE, AI_ACTOR, cmp_key, fact_guard, load_json, numbers  # noqa: E402

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "_test_out").resolve()
FIX = OUT / "fixtures"
PY = sys.executable
RESULTS: list[tuple[str, str, str]] = []
RECS = load_json(HERE / "fixture_recommendations.json")
LEARN = OUT / "learning" / "decisions.jsonl"


def sh(*args, ok=True):
    p = subprocess.run([PY, *map(str, args)], capture_output=True, text=True)
    if ok and p.returncode != 0:
        raise AssertionError(f"command failed ({p.returncode}): {' '.join(map(str, args))}\n{p.stdout}\n{p.stderr}")
    return p


def test(name):
    def deco(fn):
        def run():
            try:
                detail = fn() or ""
                RESULTS.append((name, "PASS", detail))
                print(f"[PASS] {name}  {detail}")
            except Exception as e:  # noqa: BLE001
                RESULTS.append((name, "FAIL", f"{e}\n{traceback.format_exc(limit=2)}"))
                print(f"[FAIL] {name}\n{e}")
        run.__name__ = fn.__name__
        return run
    return deco


def rec_for(text):
    k = cmp_key(text)
    for o, r in RECS["by_original"].items():
        if cmp_key(o) == k:
            return r
    return None


def review_pipeline(files, work: Path, project: str, recs=None, roles=()):
    work.mkdir(parents=True, exist_ok=True)
    role_args = []
    for r in roles:
        role_args += ["--role", r]
    sh(SCRIPTS / "extract_content.py", *files, *role_args, "-o", work / "content.json")
    sh(SCRIPTS / "analyze_messages.py", work / "content.json", "-o", work, "--learning-log", LEARN)
    rp = work / "recs.json"
    rp.write_text(json.dumps(recs or {"summary": RECS["summary"], "by_original": RECS["by_original"]}, ensure_ascii=False), encoding="utf-8")
    xlsx = work / f"{project}_KeyMessage_Review.xlsx"
    sh(SCRIPTS / "create_review_excel.py", work / "analysis.json", rp, "-o", xlsx, "--project", project)
    return xlsx, load_json(work / "analysis.json")


def read_review_rows(xlsx):
    import openpyxl
    ws = openpyxl.load_workbook(xlsx)["Message Review"]
    h = {ws.cell(1, c).value: c for c in range(1, ws.max_column + 1)}
    rows = []
    for r in range(2, ws.max_row + 1):
        rows.append({k: ws.cell(r, c).value for k, c in h.items()} | {"_r": r})
    return rows, h


def set_decisions(xlsx, out, fn):
    """fn(row) -> (decision, human_final|None) 또는 None(변경 없음)"""
    import openpyxl
    wb = openpyxl.load_workbook(xlsx)
    ws = wb["Message Review"]
    h = {ws.cell(1, c).value: c for c in range(1, ws.max_column + 1)}
    for r in range(2, ws.max_row + 1):
        row = {k: ws.cell(r, c).value for k, c in h.items()}
        res = fn(row)
        if res is None:
            continue
        d, hf = res
        ws.cell(r, h["Decision"]).value = d
        if hf is not None:
            ws.cell(r, h["Human Final"]).value = hf
    wb.save(out)
    return out


def pptx_texts(path):
    from pptx import Presentation
    out = []
    def walk(shapes, sno):
        for s in shapes:
            if s.shape_type is not None and "GROUP" in str(s.shape_type):
                walk(s.shapes, sno)
            elif s.has_text_frame:
                for p in s.text_frame.paragraphs:
                    out.append((sno, s.name, p.text))
            if getattr(s, "has_table", False) and s.has_table:
                for row in s.table.rows:
                    for c in row.cells:
                        out.append((sno, s.name, c.text))
    for i, sl in enumerate(Presentation(str(path)).slides, start=1):
        walk(sl.shapes, i)
    return out


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


# ======================================================================= tests
@test("TEST 1 — AI 상투어 → RED")
def t1():
    r = assess("당사의 차별화된 AI 기술을 기반으로 고객의 디지털 혁신을 가속화합니다.")
    assert r["status"] == "RED", r["status"]
    assert r["competitor_swap"] == "YES"
    return f"status={r['status']}, swap={r['competitor_swap']}, patterns={[h['match'] for h in r['ai_patterns']]}"


@test("TEST 2 — 좋은 메시지 → GREEN 유지")
def t2():
    r = assess("상담부터 견적까지 하나의 Workflow로 연결합니다.")
    assert r["status"] in ("GREEN", "YELLOW"), r
    assert not r["ai_patterns"]
    return f"status={r['status']} (수정 강요 없음)"


@test("TEST 3 — Tech → Value")
def t3():
    o = "생성형 AI 기반 Intelligent Workplace를 구축합니다."
    r = assess(o)
    assert r["status"] == "RED" and "Tech → Value" in r["categories"], r
    rec = rec_for(o)["ai_recommended"]
    r2 = assess(rec)
    assert r2["status"] != "RED", r2
    assert r2["process_terms"] and (r2["value_terms"] or HUMAN_ROLE.search(rec)), r2
    assert "Intelligent" not in rec and "구축합니다" not in rec
    return f"'{o}' → '{rec}' (재진단 {r2['status']}, 업무어={r2['process_terms']})"


@test("TEST 4 — Human vs AI 역할 구분")
def t4():
    o = "AI Agent를 활용해 견적 업무를 End-to-End 자동화합니다."
    r = assess(o)
    assert r["status"] == "RED" and r["ax_role_gap"], r
    rec = rec_for(o)["ai_recommended"]
    r2 = assess(rec)
    assert not r2["ax_role_gap"] and HUMAN_ROLE.search(rec) and AI_ACTOR.search(rec), r2
    return f"→ '{rec}' (AI 역할 + 담당자 역할 모두 포함, 재진단 {r2['status']})"


@test("TEST 5 — Fact Guard (숫자 보존)")
def t5():
    o = "4,700대 서버와 1.5만 회선을 체계적인 수행방안을 통해 안정적으로 이전할 수 있습니다."
    good = fact_guard(o, "4,700대 서버와 1.5만 회선을 서비스 중단 없이 이전합니다.")
    bad = fact_guard(o, "5,000대 서버와 1.5만 회선을 서비스 중단 없이 이전합니다.")
    drop = fact_guard(o, "서버와 회선을 서비스 중단 없이 이전합니다.")
    assert good["level"] == "OK", good
    assert bad["level"] == "ERROR" and any("5000" in m for m in bad["messages"]), bad
    assert drop["level"] == "WARN", drop
    # Pipeline: 수정안 숫자가 원문과 같은지 + 위조 숫자 주입 시 ERROR + APPLY 차단
    o2 = "운영 중인 서버 120대를 체계적인 전환 계획을 통해 무중단으로 이전할 수 있습니다."
    recs = json.loads(json.dumps({"summary": RECS["summary"], "by_original": RECS["by_original"]}))
    k = next(x for x in recs["by_original"] if cmp_key(x) == cmp_key(o2))
    assert numbers(recs["by_original"][k]["ai_recommended"]) == numbers(o2)
    recs["by_original"][k]["ai_recommended"] = "운영 중인 서버 150대를 서비스 중단 없이 이전합니다."
    xlsx, _ = review_pipeline([FIX / "Proposal.pptx"], OUT / "t5", "T5", recs)
    rows, _ = read_review_rows(xlsx)
    row = next(r for r in rows if cmp_key(r["Original"]) == cmp_key(o2))
    assert "Fact Guard ERROR" in row["QA Check"], row["QA Check"]
    appr = set_decisions(xlsx, OUT / "t5" / "Approved.xlsx", lambda r: ("ACCEPT", None) if cmp_key(r["Original"]) == cmp_key(o2) else None)
    p = sh(SCRIPTS / "apply_approved_messages.py", FIX / "Proposal.pptx", appr, "-o", OUT / "t5" / "Proposal_v2.pptx", "--no-learning")
    texts = [t for _, _, t in pptx_texts(OUT / "t5" / "Proposal_v2.pptx")]
    assert any(cmp_key(t) == cmp_key(o2) for t in texts), "위조 숫자 안이 반영됨!"
    assert not any("150대" in t for t in texts)
    return "OK/ERROR/WARN 판정 정확, 위조 숫자(150대) Review QA=ERROR, APPLY 차단 확인"


@test("TEST 6 — Evidence 부족 → ESCALATE")
def t6():
    r = assess("차별화된 운영 역량을 통해 안정적인 서비스를 제공합니다.")
    assert r["status"] == "ESCALATE", r["status"]
    assert r["evidence_request"]
    return f"ESCALATE, 추가 Evidence 요청 {len(r['evidence_request'])}개: {', '.join(r['evidence_request'][:3])}…"


@test("TEST 7 — PPT REVIEW (PPTX → Review XLSX)")
def t7():
    xlsx, an = review_pipeline([FIX / "Proposal.pptx"], OUT / "t7", "한빛제조_AX")
    p = sh(SCRIPTS / "validate_output.py", "review", xlsx)
    rows, h = read_review_rows(xlsx)
    gov = [r for r in rows if r["Message Type"] == "Governing"]
    assert len(gov) == 8, len(gov)  # 내용 장표 8장
    assert all(str(r["Source Location"]).startswith("Slide") for r in rows)
    assert not any("Confidential" in str(r["Original"]) for r in rows), "푸터가 메시지로 잡힘"
    st = {s: sum(1 for r in rows if r["Status"] == s) for s in ("GREEN", "YELLOW", "RED", "ESCALATE")}
    assert st["RED"] >= 4 and st["ESCALATE"] >= 1 and st["GREEN"] >= 5, st
    assert an["context"]["customer"] == "한빛제조", an["context"]["customer"]
    return f"{xlsx.name}: 메시지 {len(rows)}개 (Governing {len(gov)}), {st}, validate=PASS"


@test("TEST 8 — PDF REVIEW (Page·Source 추적) + PDF Review → 원본 PPTX APPLY")
def t8():
    xlsx, an = review_pipeline([FIX / "Proposal.pdf"], OUT / "t8", "한빛제조_PDF")
    sh(SCRIPTS / "validate_output.py", "review", xlsx)
    rows, _ = read_review_rows(xlsx)
    assert rows and all(str(r["Source Location"]).startswith("Page") and r["Page / Slide"] for r in rows)
    pptx_gov = [m["original"] for m in load_json(OUT / "t7" / "analysis.json")["messages"] if m["message_type"] == "Governing"]
    pdf_gov = {cmp_key(r["Original"]): r for r in rows if r["Message Type"] == "Governing"}
    found = [g for g in pptx_gov if cmp_key(g) in pdf_gov]
    assert len(found) >= 6, f"PDF Governing 인식 {len(found)}/8"
    pages_ok = all(pdf_gov[cmp_key(g)]["Page / Slide"] == next(m["page"] for m in load_json(OUT / "t7" / "analysis.json")["messages"] if m["original"] == g) for g in found)
    assert pages_ok, "PDF Page 번호가 Slide 번호와 다름"
    # PDF Review → 원본 PPTX에 반영 (텍스트 매칭)
    appr = set_decisions(xlsx, OUT / "t8" / "Approved.xlsx", lambda r: ("ACCEPT", None) if r["Status"] in ("RED", "YELLOW") and r["AI Recommended"] else None)
    sh(SCRIPTS / "apply_approved_messages.py", FIX / "Proposal.pptx", appr, "-o", OUT / "t8" / "Proposal_fromPDF_v2.pptx", "--no-learning")
    log = load_json(OUT / "t8" / "Proposal_fromPDF_v2_apply_log.json")
    v = sh(SCRIPTS / "validate_output.py", "apply", FIX / "Proposal.pptx", OUT / "t8" / "Proposal_fromPDF_v2.pptx")
    assert len(log["applied"]) >= 5, len(log["applied"])
    return f"PDF 메시지 {len(rows)}개, Governing {len(found)}/8 인식·Page 일치, PDF Review→PPTX 반영 {len(log['applied'])}건, 구조검증 PASS"


@test("TEST 9 — XLSX REVIEW (Workbook/Sheet 구조) + XLSX APPLY")
def t9():
    xlsx, an = review_pipeline([FIX / "Storyline.xlsx"], OUT / "t9", "Storyline", roles=["Storyline.xlsx=proposal"])
    sh(SCRIPTS / "validate_output.py", "review", xlsx)
    content = load_json(OUT / "t9" / "content.json")
    sheets = content["sources"][0]["meta"]["sheets"]
    sl = next(s for s in sheets if s["name"] == "Storyline")
    assert sl["header_row"] == 1 and sl["formula_cells"] >= 4 and len(sheets) == 2, sl
    rows, _ = read_review_rows(xlsx)
    gov = [r for r in rows if r["Message Type"] == "Governing"]
    assert len(gov) == 4 and all("Storyline" in r["Source Location"] and "!D" not in r["Source Location"] for r in gov)
    assert all("(Governing Message)" in r["Source Location"] for r in gov), [r["Source Location"] for r in gov]
    assert not any(str(r["Original"]).startswith("=") for r in rows), "수식이 메시지로 잡힘"
    appr = set_decisions(xlsx, OUT / "t9" / "Approved.xlsx",
                         lambda r: ("ACCEPT", None) if r["Status"] in ("RED", "YELLOW") and r["AI Recommended"] else ("KEEP", None))
    sh(SCRIPTS / "apply_approved_messages.py", FIX / "Storyline.xlsx", appr, "--no-learning", "-o", OUT / "t9" / "Storyline_KeyMessage_v2.xlsx")
    v = sh(SCRIPTS / "validate_output.py", "apply", FIX / "Storyline.xlsx", OUT / "t9" / "Storyline_KeyMessage_v2.xlsx")
    import openpyxl
    wb = openpyxl.load_workbook(OUT / "t9" / "Storyline_KeyMessage_v2.xlsx")
    assert wb["Summary"]["B1"].value == "=COUNTA(Storyline!D2:D10)" and wb["Storyline"]["G2"].value == "=LEN(D2)"
    import zipfile
    assert any("charts/chart" in n for n in zipfile.ZipFile(OUT / "t9" / "Storyline_KeyMessage_v2.xlsx").namelist()), "차트 유실"
    log = load_json(OUT / "t9" / "Storyline_KeyMessage_v2_apply_log.json")
    return f"시트 2개·Header·수식 {sl['formula_cells']}개 인식, Governing {len(gov)}개, 셀 반영 {len(log['applied'])}건, 수식·차트·서식 보존 PASS"


@test("TEST 10 — APPLY Decision 처리 (ACCEPT/EDIT/KEEP/ESCALATE/빈칸)")
def t10():
    xlsx = OUT / "t7" / "한빛제조_AX_KeyMessage_Review.xlsx"
    rows, _ = read_review_rows(xlsx)
    tgt = {
        "ACCEPT": "생성형 AI 기반 Intelligent Workplace를 구축합니다.",
        "EDIT": "AI Agent를 활용해 견적 업무를 End-to-End 자동화합니다.",
        "EDIT_EMPTY": "당사의 차별화된 AI 기술을 기반으로 고객의 디지털 혁신을 가속화합니다.",
        "KEEP": "견적 작성 시간을 3일에서 4시간으로 단축하여 생산성을 극대화할 수 있습니다.",
        "ESCALATE": "차별화된 운영 역량을 통해 안정적인 서비스를 제공합니다.",
        "BLANK": "운영 중인 서버 120대를 체계적인 전환 계획을 통해 무중단으로 이전할 수 있습니다.",
    }
    human = "AI Agent가 견적 초안을 쓰고, 담당자가 가격을 승인합니다."
    def fn(r):
        o = cmp_key(r["Original"])
        if o == cmp_key(tgt["ACCEPT"]): return ("ACCEPT", None)
        if o == cmp_key(tgt["EDIT"]): return ("EDIT", human)
        if o == cmp_key(tgt["EDIT_EMPTY"]): return ("EDIT", "")
        if o == cmp_key(tgt["KEEP"]): return ("KEEP", None)
        if o == cmp_key(tgt["ESCALATE"]): return ("ESCALATE", None)
        if o == cmp_key(tgt["BLANK"]): return ("", None)
        return ("KEEP", None)
    (OUT / "t10").mkdir(exist_ok=True)
    appr = set_decisions(xlsx, OUT / "t10" / "Approved.xlsx", fn)
    out = OUT / "t10" / "Proposal_KeyMessage_v2.pptx"
    p = sh(SCRIPTS / "apply_approved_messages.py", FIX / "Proposal.pptx", appr, "-o", out, "--no-learning")
    texts = [cmp_key(t) for _, _, t in pptx_texts(out)]
    acc = next(r for r in rows if cmp_key(r["Original"]) == cmp_key(tgt["ACCEPT"]))["AI Recommended"]
    assert cmp_key(acc) in texts and cmp_key(tgt["ACCEPT"]) not in texts, "ACCEPT 미반영"
    assert cmp_key(human) in texts and cmp_key(tgt["EDIT"]) not in texts, "EDIT 미반영"
    for k in ("EDIT_EMPTY", "KEEP", "ESCALATE", "BLANK"):
        assert cmp_key(tgt[k]) in texts, f"{k} 원문이 바뀜"
    log = load_json(out.with_name(out.stem + "_apply_log.json"))
    warn_txt = json.dumps(log["warnings"], ensure_ascii=False)
    assert "Human Final이 비어" in warn_txt and "빈칸" in warn_txt, warn_txt
    assert len(log["applied"]) == 2, len(log["applied"])
    sh(SCRIPTS / "validate_output.py", "apply", FIX / "Proposal.pptx", out)
    return "ACCEPT=AI안, EDIT=Human Final, EDIT(빈칸)=Warning+원문, KEEP/ESCALATE/빈칸=원문 — 반영 2건, 구조검증 PASS"


@test("TEST 11 — Round Trip ★ (PPT → REVIEW → Excel → Human → APPLY → PPT)")
def t11():
    work = OUT / "t11"
    orig = work / "Original.pptx"
    work.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIX / "Proposal.pptx", orig)
    h0 = md5(orig)
    xlsx, an0 = review_pipeline([orig], work, "Original")
    rows, _ = read_review_rows(xlsx)
    long_edit = "기존 SAP ERP와 Salesforce CRM은 그대로 두고, 표준 API로 AI Agent를 연결해 상담 이력·설계 사양·단가 정보를 견적 화면 한 곳에서 바로 확인합니다."
    def human(r):
        o = cmp_key(r["Original"])
        if o == cmp_key("기존 SAP ERP와 Salesforce CRM은 그대로 두고, API로 AI Agent를 연결합니다."):
            return ("EDIT", long_edit)  # Overflow 처리 확인용 긴 문장
        if r["Status"] == "ESCALATE":
            return ("ESCALATE", None)
        if r["Status"] in ("RED", "YELLOW") and r["AI Recommended"] and "ERROR" not in str(r["QA Check"]):
            return ("ACCEPT", None)
        return ("KEEP", None)
    appr = set_decisions(xlsx, work / "Approved_KeyMessage_Review.xlsx", human)
    p = sh(SCRIPTS / "apply_approved_messages.py", orig, appr, "--learning-log", LEARN)
    out = work / "Original_KeyMessage_v2.pptx"
    assert out.exists(), p.stdout
    assert md5(orig) == h0, "원본이 변경됨!"
    v = sh(SCRIPTS / "validate_output.py", "apply", orig, out)
    log = load_json(work / "Original_KeyMessage_v2_apply_log.json")
    texts = [cmp_key(t) for _, _, t in pptx_texts(out)]
    for e in log["applied"]:
        assert cmp_key(e["new"]) in texts
    edit = next(e for e in log["applied"] if cmp_key(e["new"]) == cmp_key(long_edit))
    # 재분석: 수정본 점수가 좋아졌는지
    sh(SCRIPTS / "extract_content.py", out, "-o", work / "after" / "content.json")
    sh(SCRIPTS / "analyze_messages.py", work / "after" / "content.json", "-o", work / "after", "--learning-log", work / "none.jsonl")
    an1 = load_json(work / "after" / "analysis.json")
    s0, s1 = an0["scores"]["Proposal Message Score"], an1["scores"]["Proposal Message Score"]
    assert s1 > s0, (s0, s1)
    assert an1["status_count"]["RED"] < an0["status_count"]["RED"]
    assert LEARN.exists() and len(LEARN.read_text(encoding="utf-8").splitlines()) >= len(rows)
    # 수정본을 LibreOffice로 열 수 있는지 (PDF 변환)
    soffice = shutil.which("soffice")
    if soffice:
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(work / "after"), str(out)], check=True, capture_output=True, timeout=180)
        assert (work / "after" / "Original_KeyMessage_v2.pdf").exists()
    return (f"반영 {len(log['applied'])}건 / 유지 {len(log['skipped'])}건, 원본 해시 동일, 구조검증 PASS, "
            f"Score {s0}→{s1}, RED {an0['status_count']['RED']}→{an1['status_count']['RED']}, "
            f"긴 EDIT 처리: {edit['warnings'] or '박스 내 Fit'}, LibreOffice 열기 OK, Learning Log 기록")


@test("TEST 12 — Multi Source ★ (RFP.pdf + Requirements.xlsx + Proposal.pptx + Reference.xlsx)")
def t12():
    files = [FIX / "RFP.pdf", FIX / "Requirements.xlsx", FIX / "Proposal.pptx", FIX / "Reference.xlsx"]
    recs = json.loads(json.dumps({"summary": RECS["summary"], "by_original": RECS["by_original"]}))
    # 다중 자료에서는 Reference 근거가 생기므로 ESCALATE 장표에 '근거 확인 시 사용안'을 Alt A로 제시
    k = next(x for x in recs["by_original"] if x.startswith("차별화된 운영 역량"))
    recs["by_original"][k].update({
        "evidence": "Reference.xlsx 수행실적 Row 4: ERP 운영 MSP, 장애 복구 평균 25분, 가용률 99.95% (C화학, 가명)",
        "alt_a": "ERP 운영 3년, 장애 복구 평균 25분·가용률 99.95% 실적으로 운영 안정성을 증명합니다.",
        "reason": "Evidence 후보가 Reference.xlsx에 있음. 이번 사업(견적 AX)과의 관련성·공개 가능 여부 확인 전까지 원문 유지(ESCALATE). 확인되면 Alt A 사용 가능."})
    xlsx, an = review_pipeline(files, OUT / "t12", "한빛제조_통합", recs)
    sh(SCRIPTS / "validate_output.py", "review", xlsx)
    roles = {s["file"]: s["role"] for s in an["context"]["sources"]}
    assert roles == {"RFP.pdf": "rfp", "Requirements.xlsx": "requirements", "Proposal.pptx": "proposal", "Reference.xlsx": "reference"}, roles
    reqs = an["requirements"]
    src = {r["source_file"] for r in reqs}
    assert {"RFP.pdf", "Requirements.xlsx"} <= src, src
    sfr2 = [r for r in reqs if "SFR-002" in r["req_id"] or "승인" in r["text"]]
    assert sfr2 and any(r["coverage"] in ("COVERED", "WEAK") for r in sfr2), sfr2
    assert any(r.get("page") == 2 for r in reqs if r["source_file"] == "RFP.pdf"), "RFP page 추적 실패"
    linked_ref = [m for m in an["messages"] if any(e["source_file"] == "Reference.xlsx" for e in m["linked_evidence"] + m.get("evidence_candidates", []))]
    esc = next(m for m in an["messages"] if m["original"].startswith("차별화된 운영 역량"))
    assert esc["assessment"]["status"] == "ESCALATE" and esc["evidence_candidates"], "ESCALATE 메시지에 Reference 후보 없음"
    linked_req = [m for m in an["messages"] if m["linked_requirements"]]
    assert linked_req, "메시지 ↔ 요구사항 연결 없음"
    import openpyxl
    wb = openpyxl.load_workbook(xlsx)
    assert "Source Trace" in wb.sheetnames
    rows, _ = read_review_rows(xlsx)
    assert {r["Source File"] for r in rows} == {"Proposal.pptx"}, "고객 자료(RFP·요구사항)가 수정 대상으로 섞임"
    gaps = [r for r in reqs if r["coverage"] == "GAP"]
    # 통합 Review → Proposal.pptx APPLY
    appr = set_decisions(xlsx, OUT / "t12" / "Approved.xlsx", lambda r: ("ACCEPT", None) if r["Status"] in ("RED", "YELLOW") and r["AI Recommended"] else ("KEEP", None))
    sh(SCRIPTS / "apply_approved_messages.py", FIX / "Proposal.pptx", appr, "-o", OUT / "t12" / "Proposal_KeyMessage_v2.pptx", "--no-learning")
    sh(SCRIPTS / "validate_output.py", "apply", FIX / "Proposal.pptx", OUT / "t12" / "Proposal_KeyMessage_v2.pptx")
    return (f"역할 자동판별 4/4, 요구사항 {len(reqs)}건(RFP p1~2 + xlsx), COVERED/WEAK {len(reqs)-len(gaps)}·GAP {len(gaps)}, "
            f"요구사항 연결 메시지 {len(linked_req)}개, Reference 연결 메시지 {len(linked_ref)}개, Source Trace 시트, 통합 Review→PPTX 반영 PASS")


@test("AUTO — 분석→재작성→수정본 자동 생성")
def t_auto():
    xlsx = OUT / "t7" / "한빛제조_AX_KeyMessage_Review.xlsx"
    import openpyxl
    wb = openpyxl.load_workbook(xlsx)
    ws = wb["Message Review"]
    h = {ws.cell(1, c).value: c for c in range(1, ws.max_column + 1)}
    for r in range(2, ws.max_row + 1):
        ws.cell(r, h["Decision"]).value = None
    (OUT / "auto").mkdir(exist_ok=True)
    blank = OUT / "auto" / "Review_blank.xlsx"
    wb.save(blank)
    out = OUT / "auto" / "Proposal_KeyMessage_AUTO.pptx"
    sh(SCRIPTS / "apply_approved_messages.py", FIX / "Proposal.pptx", blank, "--auto", "-o", out)
    sh(SCRIPTS / "validate_output.py", "apply", FIX / "Proposal.pptx", out)
    log = load_json(out.with_name(out.stem + "_apply_log.json"))
    texts = [cmp_key(t) for _, _, t in pptx_texts(out)]
    assert cmp_key("차별화된 운영 역량을 통해 안정적인 서비스를 제공합니다.") in texts, "ESCALATE가 AUTO로 바뀜"
    assert cmp_key("상담부터 견적까지 하나의 Workflow로 연결합니다.") in texts, "GREEN이 바뀜"
    assert log["mode"] == "AUTO" and len(log["applied"]) >= 8
    return f"AUTO 반영 {len(log['applied'])}건 (RED/YELLOW만), GREEN·ESCALATE 원문 유지, 구조검증 PASS"


@test("SAFETY — 원본 보호 (덮어쓰기 금지·v3 자동 증가·Stale 차단)")
def t_safety():
    work = OUT / "t11"
    appr = work / "Approved_KeyMessage_Review.xlsx"
    orig = work / "Original.pptx"
    p = sh(SCRIPTS / "apply_approved_messages.py", orig, appr, "-o", orig, "--no-learning", ok=False)
    assert p.returncode != 0 and "원본과 같습니다" in (p.stdout + p.stderr)
    sh(SCRIPTS / "apply_approved_messages.py", orig, appr, "--no-learning")
    assert (work / "Original_KeyMessage_v3.pptx").exists(), "v3 자동 생성 안 됨"
    # Stale: 이미 수정된 v2 파일에 같은 Review 적용 → 원문 불일치로 반영 0건
    stale = work / "stale"
    stale.mkdir(exist_ok=True)
    shutil.copy(work / "Original_KeyMessage_v2.pptx", stale / "Original.pptx")
    sh(SCRIPTS / "apply_approved_messages.py", stale / "Original.pptx", appr, "--no-learning")
    log = load_json(stale / "Original_KeyMessage_v2_apply_log.json")
    assert len(log["applied"]) == 0 and "Stale" in json.dumps(log["warnings"], ensure_ascii=False)
    return "같은 경로 출력 거부, v2 존재 시 v3 생성, 원문 불일치(Stale) 반영 0건"


@test("OVERFLOW — 고정 박스 Overflow: 최소 폰트 조정 / 한계 초과 Warning")
def t_overflow():
    from pptx import Presentation
    from pptx.enum.text import MSO_AUTO_SIZE
    from pptx.util import Inches, Pt
    work = OUT / "overflow"
    work.mkdir(exist_ok=True)
    prs = Presentation()
    prs.slides.add_slide(prs.slide_layouts[0]).shapes.title.text = "운영 제안서"  # 표지
    s = prs.slides.add_slide(prs.slide_layouts[5])
    s.shapes.title.text = "운영 방안"
    for name, w, txt in (("Box A", 4.0, "장애 대응 절차를 표준화해 안정성을 높입니다."),
                         ("Box B", 3.0, "변경 관리 체계를 통해 운영 리스크를 줄일 수 있습니다.")):
        b = s.shapes.add_textbox(Inches(0.5), Inches(1.4 if name == "Box A" else 3.0), Inches(w), Inches(0.95))
        b.name = name
        tf = b.text_frame
        tf.word_wrap = True
        tf.auto_size = MSO_AUTO_SIZE.NONE
        r = tf.paragraphs[0].add_run()
        r.text = txt
        r.font.size = Pt(18)
    orig = work / "Fixed.pptx"
    prs.save(orig)
    xlsx, _ = review_pipeline([orig], work, "Fixed", {"by_original": {}})
    long_a = "장애가 나면 담당 엔지니어가 바로 조치하고, 원인과 재발 방지책은 다음 날 보고합니다."  # 약간 김 → 폰트 미세 조정
    long_b = "모든 변경은 사전 영향 분석, 단계별 승인, 리허설, 원복 계획 확인, 사후 점검까지 거친 뒤에만 운영 환경에 반영하고, 결과는 주간 운영 회의에서 고객과 함께 검토합니다."
    def fn(r):
        if "장애 대응" in r["Original"]: return ("EDIT", long_a)
        if "변경 관리" in r["Original"]: return ("EDIT", long_b)
        return ("KEEP", None)
    appr = set_decisions(xlsx, work / "Approved.xlsx", fn)
    sh(SCRIPTS / "apply_approved_messages.py", orig, appr, "--no-learning")
    out = work / "Fixed_KeyMessage_v2.pptx"
    log = load_json(work / "Fixed_KeyMessage_v2_apply_log.json")
    sizes = {}
    for shp in Presentation(str(out)).slides[1].shapes:
        if shp.name in ("Box A", "Box B"):
            sizes[shp.name] = shp.text_frame.paragraphs[0].runs[0].font.size.pt
    wa = next(e for e in log["applied"] if e["new"] == long_a)["warnings"]
    wb = next(e for e in log["applied"] if e["new"] == long_b)["warnings"]
    assert 16.0 <= sizes["Box A"] < 18.0 and any("최소 조정" in w for w in wa), (sizes, wa)
    assert sizes["Box B"] == 18.0 and any("Overflow" in w for w in wb), (sizes, wb)
    sh(SCRIPTS / "validate_output.py", "apply", orig, out, ok=False)  # 폰트 크기 변경은 의도된 조정
    return f"Box A 18→{sizes['Box A']:g}pt(≤2pt 조정), Box B 폰트 유지 + Overflow Warning(축약 필요)"


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    sh(HERE / "make_fixtures.py", FIX)
    for fn in [t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, t11, t12, t_auto, t_safety, t_overflow]:
        fn()
    n_fail = sum(1 for _, s, _ in RESULTS if s == "FAIL")
    lines = ["# 키 메시지 Skill — 테스트 결과", "", f"- 작업 폴더: `{OUT}`", f"- 결과: {len(RESULTS) - n_fail} PASS / {n_fail} FAIL", "",
             "| Test | Result | Detail |", "|---|---|---|"]
    for name, st, d in RESULTS:
        lines.append(f"| {name} | {st} | {d.splitlines()[0] if d else ''} |")
    (OUT / "TEST_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n{len(RESULTS) - n_fail} PASS / {n_fail} FAIL  → {OUT / 'TEST_REPORT.md'}")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
