"""Deterministic pipeline tests on synthetic fixtures with planted defects.

    cd <skill> && python3 -m pytest -q tests
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SKILL / "tests"))
import make_fixtures  # noqa: E402


def run(*args):
    r = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, timeout=600)
    return r


@pytest.fixture(scope="session")
def wd(tmp_path_factory):
    base = tmp_path_factory.mktemp("rt")
    fx = base / "fx"
    fx.mkdir()
    make_fixtures.make_presentation(fx / "한빛은행_DC이전_제안발표.pptx")
    make_fixtures.make_rfp_docx(fx / "한빛은행_제안요청서.docx")
    make_fixtures.make_proposal_docx(fx / "한빛은행_기술제안서.docx")
    before = {p.name: p.read_bytes() for p in fx.iterdir()}
    w = base / "wd"
    r = run(SCRIPTS / "ingest.py", fx, "--out", w)
    assert r.returncode == 0, r.stderr
    after = {p.name: p.read_bytes() for p in fx.iterdir()}
    assert before == after, "originals must never be modified"
    return w


def test_manifest_roles(wd):
    m = {f["name"]: f for f in json.loads((wd / "manifest.json").read_text())["files"]}
    assert m["한빛은행_DC이전_제안발표.pptx"]["role_guess"] == "presentation"
    assert m["한빛은행_제안요청서.docx"]["role_guess"] == "rfp"
    assert m["한빛은행_기술제안서.docx"]["role_guess"] == "proposal"


def test_gm_extraction(wd):
    units = {u["uid"]: u for u in json.loads((wd / "docmodel.json").read_text())["units"]}
    assert units["F1#S002"]["gm"].startswith("KT는 차별화된")
    # S08 has no title placeholder: GM must come from the 28pt text box
    assert "확보합니디" in units["F1#S008"]["gm"]
    assert units["F1#S008"]["gm_source"].startswith("largest_font_top")
    assert units["F1#S010"]["hidden"] is True
    assert "Cutover 당일" in units["F1#S004"]["notes"]
    assert (wd / "units" / "F1" / "S004.md").exists()


def test_cross_check_finds_planted(wd):
    r = run(SCRIPTS / "cross_check.py", wd, "--customer", "한빛은행")
    assert r.returncode == 0, r.stderr
    cc = json.loads((wd / "cross_check.json").read_text())
    nc = {(c["anchor"], c["unit"]): set(c["values"]) for c in cc["number_conflicts"]}
    assert nc[("투입인력", "명")] == {"45", "42"}, nc  # 22명(이전 인력) must not be attributed to 투입인력
    assert {"2", "4"} <= nc[("RTO", "시간")]
    assert any(o["name"] == "신한은행" for o in cc["other_customers"])
    assert not any(o["name"] == "한빛은행" for o in cc["other_customers"])
    terms = [set(t["forms"]) for t in cc["term_variants"]]
    assert {"DR 센터", "DR센터"} in terms


def test_rfp_split(wd):
    r = run(SCRIPTS / "rfp_split.py", wd)
    assert r.returncode == 0, r.stderr
    req = {x["req_id"]: x for x in json.loads((wd / "rfp_requirements.json").read_text())["requirements"]}
    for rid in ("ECR-001", "PER-001", "SER-001", "PMR-001", "NER-001"):
        assert rid in req, req.keys()
    assert req["SER-001"]["mandatory"] and req["SER-001"]["category"] == "보안"
    assert "평가" not in req["NER-001"]["text"], "criteria table must not be absorbed into last requirement"


def test_report_guards(wd):
    findings = {
        "meta": {"customer": "한빛은행", "mode": "Presentation", "files": ["F1"]},
        "executive": {"overall_assessment": "x", "top5": [{"title": "t", "where": ["F1#S002"], "why": "w", "fix": "국내 1위 37개 금융사 실적 강조"}]},
        "findings": [
            {"id": "RT-01", "location": "F1#S002", "severity": "MUST FIX", "category": "Differentiation",
             "current": "c", "issue": "i", "revised": "A금융사 1,180대 이전, 99.99% 가용성 (KB국민은행 실적)"},
            {"id": "RT-02", "location": "F1#S008", "severity": "ENHANCEMENT", "category": "hygiene",
             "current": "확보합니디", "revised": "확보합니다"},
            {"id": "RT-03", "location": "", "severity": "CRITICAL", "category": "Visual"},
        ],
        "evidence_ledger": [{"claim": "차별화된 역량", "claim_loc": "F1#S002", "type": "—", "evidence": "", "evidence_loc": "", "status": "SUPPORTED"}],
        "compliance": [{"req_id": "PER-001", "requirement": "RTO 4h", "status": "CONFLICT", "findability": "MEDIUM", "risk": "MUST FIX"}],
    }
    (wd / "findings.json").write_text(json.dumps(findings, ensure_ascii=False))
    r = run(SCRIPTS / "report.py", wd)
    assert r.returncode == 2  # schema errors present (RT-03)
    slide = (wd / "02_slide_review.md").read_text()
    assert "원문에 없는 수치 '99.99%'" in slide
    assert "원문에 없는 금융사명 'KB국민은행'" in slide
    assert "'1,180대'" not in slide  # 1,180 exists in source → not flagged
    assert slide.index("RT-01") < slide.index("# Hygiene")
    ex = (wd / "01_executive.md").read_text()
    assert "원문에 없는 수치 '37개'" in ex
    assert "UNSUBSTANTIATED" in (wd / "04_evidence_ledger.md").read_text()
    assert (wd / "03_rfp_compliance.xlsx").exists()
    guard = (wd / "guard_report.md").read_text()
    assert "RT-03: unknown severity" in guard and "RT-03: missing location" in guard


@pytest.mark.skipif(not shutil.which("soffice"), reason="LibreOffice not installed")
def test_render(wd):
    r = run(SCRIPTS / "render.py", wd, "--files", "F1")
    assert r.returncode == 0, r.stderr
    pngs = sorted(p.name for p in (wd / "renders" / "F1").glob("S*.png"))
    assert "S010.png" not in pngs and "S011.png" in pngs  # hidden slide skipped, numbering preserved
    assert list((wd / "renders" / "F1").glob("F1_sheet_*.png"))
