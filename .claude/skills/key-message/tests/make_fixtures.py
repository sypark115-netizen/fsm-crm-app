# -*- coding: utf-8 -*-
"""테스트용 가상 제안 자료 생성 (모든 고객·회사명은 가상).

  python make_fixtures.py <outdir>
생성:
  Proposal.pptx        — 가상 '한빛제조 영업·견적 AX 플랫폼' 제안서 (11장, 차트·이미지·표·푸터 포함)
  Proposal.pdf         — Proposal.pptx 를 LibreOffice로 Export (PPT에서 Export된 PDF 시나리오)
  RFP.pdf              — 고객 제안요청서 (DOCX → PDF, 2 page)
  Requirements.xlsx    — 고객 요구사항 정의서
  Reference.xlsx       — 수행 실적
  Storyline.xlsx       — 제안 Storyline 시트 (Governing/Key 컬럼, 수식·차트 포함)
"""
from __future__ import annotations

import io
import shutil
import subprocess
import sys
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Emu, Inches, Pt

KFONT = "맑은 고딕"
NAVY = RGBColor(0x1F, 0x38, 0x64)
GRAY = RGBColor(0x40, 0x40, 0x40)


def tb(slide, left, top, width, height, paras, size=16, bold=False, color=GRAY, name=None):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    if name:
        box.name = name
    tf = box.text_frame
    tf.word_wrap = True
    for i, t in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run()
        r.text = t
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.name = KFONT
        r.font.color.rgb = color
    return box


def content_slide(prs, title, head, keys, body=None, page=0):
    s = prs.slides.add_slide(prs.slide_layouts[5])  # Title Only
    s.shapes.title.text = title
    for r in s.shapes.title.text_frame.paragraphs[0].runs:
        r.font.size = Pt(24)
        r.font.name = KFONT
        r.font.color.rgb = NAVY
    if head:
        tb(s, 0.6, 1.25, 12.1, 0.7, [head], size=20, bold=True, color=NAVY, name="Head Message")
    if keys:
        tb(s, 0.6, 2.2, 6.3, 2.6, keys, size=16, name="Key Messages")
    if body:
        tb(s, 7.2, 2.2, 5.5, 3.2, body, size=13, name="Body Evidence")
    tb(s, 0.4, 7.05, 3.0, 0.3, ["Confidential"], size=9, name="Footer")
    tb(s, 12.3, 7.05, 0.6, 0.3, [str(page)], size=9, name="Slide Number")
    return s


def make_png() -> bytes:
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (240, 120), (31, 56, 100))
    d = ImageDraw.Draw(im)
    d.rectangle([10, 10, 230, 110], outline=(255, 255, 255), width=3)
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def make_pptx(out: Path):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    # 1 Cover
    s = prs.slides.add_slide(prs.slide_layouts[0])
    s.shapes.title.text = "한빛제조 영업·견적 AX 플랫폼 구축 제안서"
    s.placeholders[1].text = "2026. 11 / 세움정보기술"
    s.shapes.add_picture(io.BytesIO(make_png()), Inches(11.3), Inches(0.4), Inches(1.6), Inches(0.8)).name = "Logo"
    # 2 TOC
    s = prs.slides.add_slide(prs.slide_layouts[1])
    s.shapes.title.text = "목차"
    s.placeholders[1].text = "01 사업 이해\n02 제안 전략\n03 구축 방안\n04 기대 효과"
    # 3 Section
    s = prs.slides.add_slide(prs.slide_layouts[2])
    s.shapes.title.text = "01 사업 이해"
    # 4 배경 (Tech→Value)
    content_slide(prs, "사업 배경 및 현황", "생성형 AI 기반 Intelligent Workplace를 구축합니다.",
                  ["상담·설계·견적 시스템이 분리되어 담당자가 정보를 수작업으로 재입력합니다"],
                  ["견적 1건 작성에 평균 3일 소요 (2025년 영업본부 기준)",
                   "견적 오류로 인한 재작성 비율 18%"], page=4)
    # 5 전략 (AI 상투어 + Governing 반복 Key)
    content_slide(prs, "제안 전략", "당사의 차별화된 AI 기술을 기반으로 고객의 디지털 혁신을 가속화합니다.",
                  ["AI 기반 업무 자동화를 통한 혁신", "업무 프로세스 고도화 및 디지털 혁신 실현", "생산성 극대화를 위한 최적의 플랫폼 제공"], page=5)
    # 6 To-Be (GREEN)
    content_slide(prs, "To-Be 업무 흐름", "상담부터 견적까지 하나의 Workflow로 연결합니다.",
                  ["상담 기록을 설계 요건으로 바로 정리합니다", "설계 결과를 견적 항목에 그대로 연결합니다",
                   "담당자는 가격과 최종 견적만 승인합니다"], page=6)
    # 7 AI Agent (Human vs AI) + 표
    s = content_slide(prs, "AI Agent 적용 방안", "AI Agent를 활용해 견적 업무를 End-to-End 자동화합니다.",
                      ["고객 문의 분석 Agent", "설계 사양 추천 Agent", "견적서 초안 작성 Agent"], page=7)
    rows, cols = 4, 3
    t = s.shapes.add_table(rows, cols, Inches(7.2), Inches(2.2), Inches(5.5), Inches(2.2)).table
    data = [["Agent", "AI가 하는 일", "사람이 하는 일"],
            ["문의 분석", "요구 사양 추출", "누락 확인"],
            ["사양 추천", "유사 설계 3건 제시", "사양 확정"],
            ["견적 초안", "단가표 기준 초안 작성", "가격·할인 승인"]]
    for r in range(rows):
        for c in range(cols):
            cell = t.cell(r, c)
            cell.text = data[r][c]
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(12)
                    run.font.name = KFONT
    # 8 Section
    s = prs.slides.add_slide(prs.slide_layouts[2])
    s.shapes.title.text = "03 구축 방안"
    # 9 연동 (IT audience, 거의 GREEN)
    content_slide(prs, "시스템 구성 및 연동 방안", "기존 SAP ERP와 Salesforce CRM은 그대로 두고, API로 AI Agent를 연결합니다.",
                  ["SAP ERP 견적 모듈과 API 연동", "Salesforce CRM 상담 이력 실시간 조회",
                   "1단계 영업본부, 2단계 전 사업부로 단계적 확산"], page=9)
    # 10 수행 역량 (ESCALATE)
    content_slide(prs, "수행 역량", "차별화된 운영 역량을 통해 안정적인 서비스를 제공합니다.",
                  ["풍부한 경험과 노하우를 보유하고 있습니다", "최고의 전문가를 투입합니다"], page=10)
    # 11 인프라 전환 (Fact Guard)
    content_slide(prs, "인프라 전환 방안", "운영 중인 서버 120대를 체계적인 전환 계획을 통해 무중단으로 이전할 수 있습니다.",
                  ["주말 야간 3회 리허설 후 전환합니다", "전환 실패 시 30분 안에 원복합니다"], page=11)
    # 12 기대 효과 (숫자 + 차트)
    s = content_slide(prs, "기대 효과", "견적 작성 시간을 3일에서 4시간으로 단축하여 생산성을 극대화할 수 있습니다.",
                      ["견적 재작성 비율 18%를 5% 이하로 낮추는 것이 목표입니다", "영업 담당자 1인당 월 12시간을 고객 미팅에 씁니다"], page=12)
    cd = CategoryChartData()
    cd.categories = ["As-Is", "To-Be"]
    cd.add_series("견적 작성 시간(시간)", (72, 4))
    s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(7.4), Inches(2.3), Inches(5.2), Inches(3.4), cd).name = "Effect Chart"
    prs.save(str(out))


def make_rfp_pdf(outdir: Path):
    import docx
    from docx.enum.text import WD_BREAK
    d = docx.Document()
    st = d.styles["Normal"]
    st.font.name = KFONT
    d.add_heading("한빛제조㈜ 제안요청서", 0)
    d.add_paragraph("사업명: 한빛제조 영업·견적 AX 플랫폼 구축")
    d.add_paragraph("발주기관: 한빛제조㈜")
    d.add_heading("1. 사업 배경", 1)
    d.add_paragraph("영업본부의 견적 작성에 평균 3일이 소요되어 수주 기회를 놓치고 있다.")
    d.add_paragraph("상담, 설계, 견적 정보가 서로 다른 시스템에 있어 같은 내용을 여러 번 입력하고 있다.")
    d.paragraphs[-1].runs[-1].add_break(WD_BREAK.PAGE)
    d.add_heading("2. 요구사항", 1)
    for t in [
        "SFR-001 상담 이력과 설계 사양을 견적 항목에 자동으로 연계하여야 한다.",
        "SFR-002 AI가 작성한 견적 초안은 담당자 승인 후 확정되어야 한다.",
        "SFR-003 기존 SAP ERP 및 Salesforce CRM과 연동하여야 한다.",
        "PER-001 견적 초안 생성은 건당 5분 이내여야 한다.",
        "SER-001 고객 정보는 사내 보안 정책에 따라 외부로 전송되지 않아야 한다.",
        "PMR-001 수행사는 최근 3년 내 유사 사업 수행 실적을 제시할 것.",
    ]:
        d.add_paragraph(t)
    docx_path = outdir / "RFP.docx"
    d.save(str(docx_path))
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(docx_path)],
                   check=True, capture_output=True, timeout=180)
    docx_path.unlink()


def make_pptx_pdf(outdir: Path):
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(outdir / "Proposal.pptx")],
                   check=True, capture_output=True, timeout=180)


def make_xlsx(outdir: Path):
    from openpyxl import Workbook
    from openpyxl.chart import BarChart, Reference
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "요구사항"
    ws.append(["요구사항 ID", "구분", "요구사항 명", "상세 내용", "중요도"])
    for row in [
        ["SFR-001", "기능", "상담-설계-견적 연계", "상담 이력과 설계 사양을 견적 항목에 자동으로 연계", "상"],
        ["SFR-002", "기능", "견적 승인", "AI 견적 초안은 담당자 승인 후 확정", "상"],
        ["SFR-003", "연계", "기간계 연동", "SAP ERP, Salesforce CRM 연동", "상"],
        ["SFR-004", "기능", "견적 이력 검색", "과거 견적과 유사 사례를 검색", "중"],
        ["PER-001", "성능", "초안 생성 시간", "견적 초안 생성 건당 5분 이내", "상"],
        ["SER-001", "보안", "고객 정보 보호", "고객 정보 외부 전송 금지", "상"],
    ]:
        ws.append(row)
    for c in ws[1]:
        c.font = Font(bold=True)
    ws2 = wb.create_sheet("용어")
    ws2.append(["용어", "설명"])
    ws2.append(["견적 초안", "가격 확정 전 견적서"])
    wb.save(str(outdir / "Requirements.xlsx"))

    wb = Workbook()
    ws = wb.active
    ws.title = "수행실적"
    ws.append(["고객사", "사업명", "기간", "규모", "주요 성과"])
    ws.append(["A전자(가명)", "영업 견적 자동화 구축", "2024.03~2024.12", "15억", "견적 작성 시간 62% 단축"])
    ws.append(["B중공업(가명)", "설계 문서 AI 검색", "2025.01~2025.08", "9억", "설계 문서 검색 시간 하루 40분 단축"])
    ws.append(["C화학(가명)", "ERP 운영 MSP", "2023.01~2025.12", "30억", "장애 복구 평균 25분, 가용률 99.95%"])
    wb.save(str(outdir / "Reference.xlsx"))

    wb = Workbook()
    ws = wb.active
    ws.title = "Storyline"
    ws.append(["장표", "섹션", "장표 제목", "Governing Message", "Key Message 1", "Key Message 2", "글자수"])
    rows = [
        [4, "사업 이해", "사업 배경", "생성형 AI 기반 Intelligent Workplace를 구축합니다.", "견적 1건에 평균 3일이 걸립니다", "견적 재작성 비율 18%"],
        [5, "제안 전략", "제안 전략", "당사의 차별화된 AI 기술을 기반으로 고객의 디지털 혁신을 가속화합니다.", "AI 기반 업무 자동화를 통한 혁신", "생산성 극대화"],
        [6, "구축 방안", "To-Be", "상담부터 견적까지 하나의 Workflow로 연결합니다.", "담당자는 가격과 최종 견적만 승인합니다", ""],
        [10, "수행 역량", "수행 역량", "차별화된 운영 역량을 통해 안정적인 서비스를 제공합니다.", "최고의 전문가를 투입합니다", ""],
    ]
    for i, r in enumerate(rows, start=2):
        ws.append(r + [f"=LEN(D{i})"])
    hdr_fill = PatternFill("solid", fgColor="1F3864")
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = hdr_fill
    ws.column_dimensions["D"].width = 60
    ch = BarChart()
    ch.title = "Governing 글자수"
    ch.add_data(Reference(ws, min_col=7, min_row=1, max_row=5), titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=1, min_row=2, max_row=5))
    ws.add_chart(ch, "I2")
    s2 = wb.create_sheet("Summary")
    s2["A1"] = "Governing 수"
    s2["B1"] = "=COUNTA(Storyline!D2:D10)"
    wb.save(str(outdir / "Storyline.xlsx"))


def main():
    outdir = Path(sys.argv[1] if len(sys.argv) > 1 else "fixtures")
    outdir.mkdir(parents=True, exist_ok=True)
    make_pptx(outdir / "Proposal.pptx")
    make_pptx_pdf(outdir)
    make_rfp_pdf(outdir)
    make_xlsx(outdir)
    for p in sorted(outdir.iterdir()):
        print(f"[OK] {p.name} ({p.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
