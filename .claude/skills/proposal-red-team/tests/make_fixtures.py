#!/usr/bin/env python3
"""Build synthetic, fully fictional test fixtures with planted defects.

    python3 make_fixtures.py <outdir> [--pdf]

Customer "한빛은행" and every project/number here are fictional. Planted defects are listed in
PLANTED (used by tests and by the eval graders) so the review's recall can be checked.
--pdf also converts the docx files to PDF with LibreOffice (RFP is usually a PDF in real life).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt

PLANTED = {
    "presentation": {
        "generic_claim": "S02 — 'KT는 차별화된 금융 Cloud 역량을 보유하고 있습니다' (경쟁사 교체 가능, Evidence 없음)",
        "headcount_conflict": "투입인력 45명 (S05) vs 42명 (S09)",
        "rto_conflict": "RTO 2시간 (S04) vs RTO 4시간 (S08)",
        "other_customer": "S07 본문에 '신한은행' (Reference 장표 아님 → 복사 오류)",
        "storyline_break": "S06 'KT 그룹 소개'가 실행계획 중간에 끼어 있음",
        "no_title_placeholder": "S08 제목이 placeholder가 아닌 큰 텍스트박스",
        "dense_text": "S07 텍스트 과밀 (작은 글씨 12줄)",
        "ai_phrase": "S07 '혁신적이고 획기적인 최적의 솔루션을 통해 시너지를 극대화'",
        "typo": "S08 '확보합니디'",
        "term_variant": "'DR센터' vs 'DR 센터'",
        "weak_pm": "S09 PM 소개에 금융·유사사업 경험 없음",
        "strong_slide": "S04 Evidence+How가 연결된 장표 (PASS 기대)",
        "hidden_slide": "S10 숨김",
    },
    "proposal_vs_rfp": {
        "missing_req": "SER-001 (개인정보·신용정보 암호화) 대응 없음",
        "hard_to_find": "PMR-001 (PM 상주) 대응이 '부록 C. 기타'에만 있음",
        "conflict": "PER-001 RTO 4시간 이내 요구 vs 제안서 'RTO 6시간'",
        "compliant": "ECR-001 서버 이전 대수 1,180대 명시",
    },
}


def tb(slide, text, x, y, w, h, size, bold=False):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.name = "맑은 고딕"
    return box


def slide_title(prs, title, body_lines, size=16, notes=""):
    s = prs.slides.add_slide(prs.slide_layouts[5])  # title only
    s.shapes.title.text = title
    for p in s.shapes.title.text_frame.paragraphs:
        for r in p.runs:
            r.font.size = Pt(26)
    if body_lines:
        tb(s, "\n".join(body_lines), 0.6, 1.6, 12.0, 5.2, size)
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    return s


def make_presentation(path: Path):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    # S01 cover
    s = prs.slides.add_slide(prs.slide_layouts[0])
    s.shapes.title.text = "한빛은행 차세대 데이터센터 이전 및 네트워크 고도화 사업"
    s.placeholders[1].text = "제안발표 | KT | 2026.11"
    # S02 generic claim
    slide_title(prs, "KT는 차별화된 금융 Cloud 역량을 보유하고 있습니다",
                ["Network, Cloud, Data Center, AI 역량을 모두 보유한 유일한 사업자", "다양한 금융 고객 경험", "최고의 전문 인력"])
    # S03 customer issue
    slide_title(prs, "한빛은행의 과제: 무중단 이전과 DR센터 전환시간 단축",
                ["현행 IDC 노후화(2009년 구축) — 상면·전력 한계", "주말 계획정지 허용시간: 10시간",
                 "감독규정 대응을 위한 DR 전환 훈련 결과 개선 필요", "회선 전환과 서버 이전 일정이 분리 관리되어 Cutover 리스크 존재"])
    # S04 strong slide
    slide_title(prs, "서버 이전과 회선 Cutover를 하나의 Migration Plan으로 통제해 계획정지 8시간 내 전환",
                ["Evidence: 2024년 A금융사 데이터센터 이전 — 서버 1,180대, 계획정지 8시간 내 Cutover 완료",
                 "How: KT 네트워크 운영조직과 DC 이전 PM을 단일 War-room으로 통합, 회선 개통-서버 이전 Dependency를 하나의 Runbook으로 관리",
                 "Impact: 한빛은행 주말 계획정지 10시간 대비 2시간 여유 확보, RTO 2시간 목표"],
                notes="여기서 PM이 A금융사 Cutover 당일 회선 지연 대응 사례를 30초 설명")
    # S05 plan with headcount
    slide_title(prs, "3단계 이전 전략: 비핵심 → 정보계 → 계정계",
                ["1단계(2027.03~05) 비핵심 시스템 / 2단계(2027.06~08) 정보계 / 3단계(2027.09~10) 계정계",
                 "투입인력 45명 (이전 22명, 네트워크 12명, 보안 5명, PMO 6명)", "사업기간 8개월"])
    # S06 storyline break
    slide_title(prs, "KT 그룹 소개",
                ["매출 26조원, 임직원 2만명", "국내 최대 통신 인프라", "KT cloud, KT DS 등 그룹사 보유"])
    # S07 dense + other customer + AI phrase
    slide_title(prs, "네트워크 고도화 방안",
                ["- 혁신적이고 획기적인 최적의 솔루션을 통해 시너지를 극대화합니다",
                 "- 신한은행 고객님께 최적화된 이중화 회선 구성을 제공합니다",
                 "- 백본 이중화 및 L4/L7 이중화", "- DR 센터 회선 별도 구성", "- 망분리 환경 유지",
                 "- SD-WAN 도입 검토", "- 대외계 회선 재설계", "- 영업점 회선 단계적 전환", "- 모니터링 체계 고도화",
                 "- 장애 대응 프로세스 개선", "- 보안장비 재배치", "- 회선 사업자 이원화 검토"], size=11)
    # S08 no title placeholder, typo, RTO conflict
    s = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    tb(s, "DR 체계: 이중화 구성으로 안정성을 확보합니디", 0.6, 0.4, 12, 1.0, 28, bold=True)
    tb(s, "- DR센터 상시 동기화\n- RTO 4시간, RPO 0\n- 연 2회 전환 훈련", 0.6, 1.8, 12, 4, 16)
    # S09 PM weak + headcount conflict
    slide_title(prs, "수행조직 및 PM",
                ["PM: 홍길동 부장 (경력 20년, 정보통신기술사)", "투입인력 42명", "본사 기술지원 조직 Back-up"])
    # S10 hidden
    s = slide_title(prs, "(내부검토용) 가격 시뮬레이션", ["제안금액 검토 중"])
    s._element.set("show", "0")
    # S11 closing
    slide_title(prs, "감사합니다", [])
    prs.save(path)


def make_rfp_docx(path: Path):
    import docx
    d = docx.Document()
    d.add_heading("한빛은행 차세대 데이터센터 이전 사업 제안요청서", 0)
    d.add_heading("1. 사업 개요", 1)
    d.add_paragraph("본 사업은 노후화된 현행 IDC를 신규 데이터센터로 이전하고 네트워크를 고도화하는 사업이다.")
    d.add_heading("2. 제안서 작성 지침", 1)
    d.add_paragraph("제안서는 A4 100페이지 이내로 작성하여야 한다.")
    d.add_paragraph("제안발표는 20분 이내로 하여야 한다.")
    d.add_heading("3. 요구사항", 1)
    t = d.add_table(rows=1, cols=3)
    t.rows[0].cells[0].text, t.rows[0].cells[1].text, t.rows[0].cells[2].text = "요구사항 ID", "요구사항명", "세부내용"
    rows = [
        ("ECR-001", "서버 이전", "현행 서버 1,180대를 신규 센터로 이전하여야 한다."),
        ("PER-001", "DR 전환", "재해 발생 시 RTO 4시간 이내, RPO 0을 보장하여야 한다."),
        ("SER-001", "데이터 암호화", "개인정보 및 신용정보는 이전 과정 전 구간에서 암호화하여야 한다."),
        ("PMR-001", "PM 상주", "PM은 사업 전 기간 한빛은행에 상주하여야 하며 금융권 유사사업 수행경험을 제시할 것."),
        ("NER-001", "회선 이중화", "대외계 회선은 이원화된 사업자로 구성할 것."),
    ]
    for r in rows:
        c = t.add_row().cells
        for i, v in enumerate(r):
            c[i].text = v
    d.add_heading("4. 평가기준", 1)
    t2 = d.add_table(rows=1, cols=3)
    t2.rows[0].cells[0].text, t2.rows[0].cells[1].text, t2.rows[0].cells[2].text = "평가항목", "평가요소", "배점"
    for r in [("사업이해도", "현황 및 요구사항 이해", "10"), ("이전방안", "무중단 이전 전략, Cutover 계획", "30"),
              ("DR/보안", "DR 체계, 암호화, 접근통제", "20"), ("수행조직", "PM 역량, 유사사업 경험", "20"), ("가격", "가격 평가", "20")]:
        c = t2.add_row().cells
        for i, v in enumerate(r):
            c[i].text = v
    d.save(path)


def make_proposal_docx(path: Path):
    import docx
    d = docx.Document()
    d.add_heading("한빛은행 차세대 데이터센터 이전 사업 기술제안서", 0)
    d.add_heading("I. 사업 이해", 1)
    d.add_paragraph("한빛은행의 현행 IDC는 2009년 구축되어 상면과 전력이 한계에 도달하였다.")
    d.add_heading("II. 이전 방안", 1)
    d.add_paragraph("현행 서버 1,180대를 3단계로 이전한다. 서버 이전과 회선 Cutover를 단일 Runbook으로 관리한다.")
    d.add_heading("III. DR 방안", 1)
    d.add_paragraph("DR센터는 상시 동기화하며 RTO 6시간, RPO 0을 목표로 한다.")
    d.add_heading("IV. 네트워크 방안", 1)
    d.add_paragraph("대외계 회선은 KT와 타 사업자로 이원화하여 구성한다.")
    d.add_heading("부록 C. 기타", 1)
    d.add_paragraph("PM은 사업기간 중 고객사에 상주한다.")
    d.save(path)


def to_pdf(src: Path):
    soffice = shutil.which("soffice")
    if not soffice:
        print("soffice missing; skipping pdf", file=sys.stderr)
        return
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(src.parent), str(src)],
                   check=True, capture_output=True, timeout=300)
    src.unlink()


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "fixtures_out")
    out.mkdir(parents=True, exist_ok=True)
    make_presentation(out / "한빛은행_DC이전_제안발표.pptx")
    make_rfp_docx(out / "한빛은행_제안요청서.docx")
    make_proposal_docx(out / "한빛은행_기술제안서.docx")
    if "--pdf" in sys.argv:
        to_pdf(out / "한빛은행_제안요청서.docx")
        to_pdf(out / "한빛은행_기술제안서.docx")
    (out / "PLANTED.json").write_text(json.dumps(PLANTED, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"fixtures → {out}")


if __name__ == "__main__":
    main()
