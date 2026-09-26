# -*- coding: utf-8 -*-
"""AI 상품화 아이디어 100 — Version2 공통 빌더 (3개 타깃 동일 양식)."""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

NAVY = "1F3864"
HDR_FILL = PatternFill("solid", fgColor=NAVY)
SUB_FILL = PatternFill("solid", fgColor="D9E1F2")
INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")
KPI_FILL = PatternFill("solid", fgColor="EDF2F9")
HDR_FONT = Font(name="맑은 고딕", bold=True, color="FFFFFF", size=10)
TITLE_FONT = Font(name="맑은 고딕", bold=True, size=15, color=NAVY)
SEC_FONT = Font(name="맑은 고딕", bold=True, size=11, color=NAVY)
BASE_FONT = Font(name="맑은 고딕", size=10)
BLUE_FONT = Font(name="맑은 고딕", size=10, color="0000FF")
BOLD_FONT = Font(name="맑은 고딕", size=10, bold=True)
KPI_FONT = Font(name="맑은 고딕", size=18, bold=True, color=NAVY)
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)

# 채점 가중치: 5개 기준 1~5점 입력 → 100점 환산 (경제효과40·적용범위20·성과속도15·구현용이성10·KPI측정성15)
WEIGHTS = [8, 4, 3, 2, 3]
CRITERIA = ["경제효과(1~5)\n×8=40", "적용범위(1~5)\n×4=20", "성과속도(1~5)\n×3=15",
            "구현용이성(1~5)\n×2=10", "KPI측정성(1~5)\n×3=15"]

COLS_02 = [  # (헤더, 폭)
    ("순위", 6), ("AI 아이템", 34), ("영역", 13), ("실사용자·추천 업종", 20), ("가치유형", 10),
    ("필요 데이터·연동", 26),
    (CRITERIA[0], 10), (CRITERIA[1], 10), (CRITERIA[2], 10), (CRITERIA[3], 10), (CRITERIA[4], 10),
    ("효과점수(100)", 9), ("효과등급", 11), ("대표 KPI 개선 범위", 32), ("도입기간", 9),
    ("가격모델", 18), ("과금 단위", 20), ("Basic 월요금(원)", 12), ("Pro 월요금(원)", 12),
    ("초기 구축비", 14), ("근거코드", 8), ("V1 출처", 12),
]
GRADE_F = '=IFS({c}>=95,"S | 최우선",{c}>=89,"A+ | 매우 큼",{c}>=80,"A | 큼",TRUE,"B | 보통")'


def score(r):
    return sum(w * x for w, x in zip(WEIGHTS, r))


def hdr(ws, row, values, height=32):
    for i, v in enumerate(values, 1):
        c = ws.cell(row=row, column=i, value=v)
        c.font, c.fill, c.alignment, c.border = HDR_FONT, HDR_FILL, CENTER, BORDER
    ws.row_dimensions[row].height = height


def body(c, blue=False, bold=False, center=False, fmt=None):
    c.font = BLUE_FONT if blue else (BOLD_FONT if bold else BASE_FONT)
    c.alignment = CENTER if center else WRAP
    c.border = BORDER
    if fmt:
        c.number_format = fmt


def title(ws, text, sub=None, span=8):
    ws["A1"] = text
    ws["A1"].font = TITLE_FONT
    ws.row_dimensions[1].height = 26
    if sub:
        ws["A2"] = sub
        ws["A2"].font = Font(name="맑은 고딕", size=9, italic=True, color="595959")
        ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=span)
        ws.row_dimensions[2].height = 30


def widths(ws, ws_list):
    for i, w in enumerate(ws_list, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def sort_items(items):
    idx = list(range(len(items)))
    idx.sort(key=lambda i: (-score(items[i]["r"]), -items[i]["r"][3], -items[i]["r"][0], i))
    return [items[i] for i in idx]


def build(cfg, out_path):
    items = sort_items(cfg["items"])
    assert len(items) == 100, (cfg["key"], len(items))
    names = [it["name"] for it in items]
    assert len(set(names)) == 100, [n for n in names if names.count(n) > 1]
    top15 = names[:15]
    for key in ("dev", "journey"):
        missing = [n for n in top15 if n not in cfg[key]]
        assert not missing, (cfg["key"], key, missing)
    model_codes = {m[0] for m in cfg["pricing"]}
    src_codes = {s[0] for s in cfg["sources"]}
    for it in items:
        assert it["model"] in model_codes, it
        for s in it["src"].split(","):
            assert s.strip() in src_codes, it
        assert it["area"] in cfg["areas"], it
    model_name = {m[0]: m[1] for m in cfg["pricing"]}

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    sheets = ["00_V1_진단", "01_Executive", "02_AI_100", "03_Pricing_Model", "04_Pricing_Calculator",
              "05_Category_Map", "06_Sources", "07_Top15_Dev_Guide", "08_User_Journey", "A1_V1_원본"]
    S = {n: wb.create_sheet(n) for n in sheets}
    T = cfg["target"]

    # ---------- 00_V1_진단 ----------
    ws = S["00_V1_진단"]
    title(ws, f"[V1 진단] {T} AI 상품화 아이디어 100 — 컨설턴트 리뷰 & V2 개선 내역",
          f"[원본] {cfg['v1_file']}  |  [기준일] {cfg['date']}  |  [원칙] 3개 타깃(중소기업·소상공인·영업사원) 모두 동일한 10시트·동일 컬럼·동일 채점식으로 재구성", 5)
    r = 4
    ws.cell(row=r, column=1, value="[요청 의도 재정의]").font = SEC_FONT
    r += 1
    for line in cfg["intent"]:
        c = ws.cell(row=r, column=1, value=line)
        c.font, c.alignment = BASE_FONT, WRAP
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
        ws.row_dimensions[r].height = 30
        r += 1
    r += 1
    ws.cell(row=r, column=1, value="[V1 진단표] 장점은 살리고, 단점은 V2에서 이렇게 고쳤습니다").font = SEC_FONT
    r += 1
    hdr(ws, r, ["구분", "진단 항목", "V1 현황 (근거)", "평가", "V2 조치"])
    r += 1
    for row in cfg["diagnosis"]:
        for i, v in enumerate(row, 1):
            c = ws.cell(row=r, column=i, value=v)
            body(c, center=(i in (1, 4)))
        ws.row_dimensions[r].height = 48
        r += 1
    r += 1
    ws.cell(row=r, column=1, value="[V1→V2 변경 로그] 통합·삭제·신규 아이템").font = SEC_FONT
    r += 1
    hdr(ws, r, ["유형", "V1 아이템", "V2 아이템", "사유", ""])
    r += 1
    for row in cfg["changes"]:
        for i, v in enumerate(list(row) + [""], 1):
            if i > 4:
                break
            c = ws.cell(row=r, column=i, value=v)
            body(c, center=(i == 1))
        ws.row_dimensions[r].height = 30
        r += 1
    widths(ws, [12, 30, 48, 12, 60])
    ws.freeze_panes = "A4"

    # ---------- 02_AI_100 ----------
    ws = S["02_AI_100"]
    hdr(ws, 1, [h for h, _ in COLS_02], 44)
    for i, it in enumerate(items, 2):
        vals = [i - 1, it["name"], it["area"], it["user"], it["vtype"], it["data"],
                *it["r"], None, None, it["kpi"], it["period"],
                f'{it["model"]} {model_name[it["model"]]}', it["unit"], it["basic"], it["pro"],
                it["setup"], it["src"], it["v1"]]
        for j, v in enumerate(vals, 1):
            c = ws.cell(row=i, column=j, value=v)
            blue = 7 <= j <= 11 or j in (18, 19)
            body(c, blue=blue, center=(j in (1, 3, 5, 7, 8, 9, 10, 11, 12, 13, 15, 21, 22)),
                 fmt="#,##0" if j in (18, 19) else None)
        ws.cell(row=i, column=12, value=f"=G{i}*8+H{i}*4+I{i}*3+J{i}*2+K{i}*3")
        body(ws.cell(row=i, column=12), bold=True, center=True)
        ws.cell(row=i, column=13, value=GRADE_F.format(c=f"L{i}"))
        body(ws.cell(row=i, column=13), center=True)
    widths(ws, [w for _, w in COLS_02])
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLS_02))}101"
    dv = DataValidation(type="whole", operator="between", formula1="1", formula2="5", allow_blank=False,
                        error="1~5 정수만 입력", errorTitle="채점 입력")
    ws.add_data_validation(dv)
    dv.add("G2:K101")

    # ---------- 03_Pricing_Model ----------
    ws = S["03_Pricing_Model"]
    title(ws, f"[가격모델] {T} AI SaaS 가격모델 설계", cfg["pricing_note"], 8)
    hdr(ws, 4, ["코드", "가격모델", "초기 구축비", "월 요금 범위", "적합 아이템", "과금 논리", "추천 운영 방식", "02 적용 수"])
    r = 5
    for m in cfg["pricing"]:
        for j, v in enumerate(m, 1):
            body(ws.cell(row=r, column=j, value=v), center=(j == 1))
        c = ws.cell(row=r, column=8, value=f"=COUNTIF('02_AI_100'!P:P,A{r}&\"*\")")
        body(c, center=True)
        ws.row_dimensions[r].height = 42
        r += 1
    r += 1
    ws.cell(row=r, column=1, value="[가격 산정 5단계]").font = SEC_FONT
    r += 1
    for k, v in cfg["price_steps"]:
        body(ws.cell(row=r, column=1, value=k), bold=True)
        c = ws.cell(row=r, column=2, value=v)
        body(c)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=7)
        ws.row_dimensions[r].height = 30
        r += 1
    widths(ws, [16, 20, 16, 22, 26, 44, 34, 10])
    ws.freeze_panes = "A5"

    # ---------- 04_Pricing_Calculator ----------
    ws = S["04_Pricing_Calculator"]
    title(ws, f"[계산기] {T} SaaS 가격 산정 — 고객 경제가치 기반",
          "파란 글씨·노란 셀만 바꾸세요. 나머지는 수식입니다.", 6)
    hdr(ws, 3, ["입력값", "값", "단위", "", "사용법", ""])
    inputs = cfg["calc"]
    labels = ["대상 사용자 수", "1인 월 총인건비", "대상 업무 비중", "AI 시간 절감률", "월 매출(담당 매출)",
              "예상 매출 증대율", "매출총이익률", "월 직접비 절감액", "가치 캡처율", "연간 계약 할인율"]
    units = ["명", "원", "%", "%", "원", "%", "%", "원", "%", "%"]
    for k, (lab, u, v) in enumerate(zip(labels, units, inputs)):
        row = 5 + k
        body(ws.cell(row=row, column=1, value=lab), bold=True)
        c = ws.cell(row=row, column=2, value=v)
        body(c, blue=True, fmt="0.0%" if u == "%" else "#,##0")
        c.fill = INPUT_FILL
        body(ws.cell(row=row, column=3, value=u), center=True)
    guide = ws.cell(row=5, column=5, value=cfg["calc_guide"])
    guide.font, guide.alignment = BASE_FONT, WRAP
    ws.merge_cells("E5:F14")
    hdr(ws, 16, ["계산 결과", "값", "수식 설명", "", "", ""])
    res = [
        ("월 인건비 절감가치", "=B5*B6*B7*B8", "사용자수×인건비×업무비중×절감률", "#,##0"),
        ("월 매출총이익 증가가치", "=B9*B10*B11", "매출×증대율×총이익률", "#,##0"),
        ("월 직접비 절감가치", "=B12", "직접 입력", "#,##0"),
        ("월 총 경제가치", "=SUM(B17:B19)", "위 3개 합계", "#,##0"),
        ("권장 SaaS 월요금", "=B20*B13", "총가치×가치 캡처율", "#,##0"),
        ("권장 연간 계약가", "=B21*12*(1-B14)", "월요금×12×(1-연간할인)", "#,##0"),
        ("12개월 고객 순가치", "=B20*12-B22", "연간 가치-연간 계약가", "#,##0"),
        ("고객 ROI", "=IF(B22=0,0,B23/B22)", "순가치÷연간 계약가", '0.0"x"'),
        ("가격 적정성 점검", f'=IF(B21<{cfg["calc_floor"]},"[하한 미달] 운영원가 이하 — 캡처율↑ 또는 최소요금 적용",IF(B21>{cfg["calc_ceiling"]},"[상한 초과] 타깃 예산 초과 — 모듈 분리·단계 과금 검토","[적정] 타깃 예산 범위 내"))',
         f'하한 {cfg["calc_floor"]:,}원 / 상한 {cfg["calc_ceiling"]:,}원 (03 시트 가격대 기준)', None),
    ]
    for k, (lab, f, d, fmt) in enumerate(res):
        row = 17 + k
        body(ws.cell(row=row, column=1, value=lab), bold=True)
        body(ws.cell(row=row, column=2, value=f), bold=True, fmt=fmt)
        body(ws.cell(row=row, column=3, value=d))
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=6)
    widths(ws, [24, 20, 10, 2, 40, 30])

    # ---------- 05_Category_Map ----------
    ws = S["05_Category_Map"]
    title(ws, f"[영역 지도] {T} 영역별 포트폴리오")
    hdr(ws, 2, ["영역", "아이템 수", "평균 효과점수", "최고점", "S·A+ 수", "최우선 추천 예시", "주요 가격모델", "영역 설명"])
    ws.row_dimensions[2].height = 32
    for k, area in enumerate(cfg["areas"]):
        row = 3 + k
        area_items = [it for it in items if it["area"] == area]
        best = area_items[0]
        models = {}
        for it in area_items:
            models[it["model"]] = models.get(it["model"], 0) + 1
        main_model = max(models, key=lambda m: models[m])
        vals = [area,
                f"=COUNTIF('02_AI_100'!C:C,A{row})",
                f"=IFERROR(ROUND(AVERAGEIF('02_AI_100'!C:C,A{row},'02_AI_100'!L:L),1),0)",
                f"=MAXIFS('02_AI_100'!L:L,'02_AI_100'!C:C,A{row})",
                f"=COUNTIFS('02_AI_100'!C:C,A{row},'02_AI_100'!L:L,\">=89\")",
                best["name"], f"{main_model} {model_name[main_model]}", cfg["areas"][area]]
        for j, v in enumerate(vals, 1):
            body(ws.cell(row=row, column=j, value=v), center=(2 <= j <= 5), bold=(j == 1))
        ws.row_dimensions[row].height = 30
    widths(ws, [16, 10, 12, 9, 9, 38, 24, 44])
    ws.freeze_panes = "A3"

    # ---------- 06_Sources ----------
    ws = S["06_Sources"]
    title(ws, f"[근거] 근거 및 가격 앵커 | {cfg['date']} 기준")
    hdr(ws, 2, ["코드", "출처", "URL", "활용 방식", "02 인용 수"])
    for k, s in enumerate(cfg["sources"]):
        row = 3 + k
        for j, v in enumerate(s, 1):
            body(ws.cell(row=row, column=j, value=v), center=(j == 1))
        body(ws.cell(row=row, column=5, value=f"=COUNTIF('02_AI_100'!U:U,\"*\"&A{row}&\"*\")"), center=True)
        if s[2].startswith("http"):
            ws.cell(row=row, column=3).hyperlink = s[2]
        ws.row_dimensions[row].height = 36
    row = 3 + len(cfg["sources"]) + 1
    c = ws.cell(row=row, column=1, value="[주의] 100개 아이템의 효과범위·점수·가격은 공개 연구와 SaaS 공식 가격을 참고한 컨설팅용 가정입니다. "
                                         "실제 효과는 업종·데이터 품질·사용자 채택·연동 범위에 따라 달라지며, 가격 앵커(환율·요금제)는 조회일 이후 변경될 수 있습니다.")
    c.font, c.alignment = Font(name="맑은 고딕", size=9, italic=True, color="C00000"), WRAP
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
    ws.row_dimensions[row].height = 32
    widths(ws, [7, 34, 50, 60, 10])

    # ---------- 07_Top15_Dev_Guide ----------
    ws = S["07_Top15_Dev_Guide"]
    title(ws, f"[개발가이드] {T} Top 15 — 노코드 PoC → GitHub 오픈소스 → 프롬프트 → AI코딩 제품화",
          "[활용법] ① 노코드로 1~2주 PoC → ② GitHub 오픈소스로 셀프호스팅 → ③ 프롬프트를 JSON 출력 규칙으로 고정 → ④ Claude Code·Cursor 등으로 제품화. 순위·아이템·난이도·구축비는 02_AI_100과 수식 연동.", 14)
    dev_cols = [("순위", 6), ("AI 아이템", 26), ("권장 개발경로", 22), ("① 노코드·SaaS PoC (1~2주)", 32),
                ("② GitHub 오픈소스", 30), ("대표 GitHub URL", 30), ("③ 프롬프트 설계 원칙", 32),
                ("핵심 프롬프트 예시 (복사용, {변수})", 50), ("④ AI코딩 직접개발 (스택)", 32), ("필수 연동·데이터", 28),
                ("MVP 4주 로드맵", 36), ("구현용이성(1~5)", 9), ("초기 구축비", 12), ("리스크·체크포인트", 34)]
    hdr(ws, 4, [h for h, _ in dev_cols], 36)
    for k, name in enumerate(top15):
        row = 5 + k
        d = cfg["dev"][name]
        assert len(d) == 10, (name, len(d))
        vals =[f"='02_AI_100'!A{k+2}", f"='02_AI_100'!B{k+2}", *d[:9], f"='02_AI_100'!J{k+2}", f"='02_AI_100'!T{k+2}", d[9]]
        for j, v in enumerate(vals, 1):
            body(ws.cell(row=row, column=j, value=v), center=(j in (1, 12, 13)), bold=(j == 2))
        ws.row_dimensions[row].height = 150
    row = 5 + 15 + 1
    ws.cell(row=row, column=2, value="[공통 개발 툴킷] 15개 아이템 공통 도구").font = SEC_FONT
    row += 1
    hdr_r = row
    for j, v in enumerate(["", "구분", "내용", "", "", "GitHub / 참고"], 1):
        if v:
            c = ws.cell(row=hdr_r, column=j, value=v)
            c.font, c.fill, c.alignment, c.border = HDR_FONT, HDR_FILL, CENTER, BORDER
    ws.merge_cells(start_row=hdr_r, start_column=3, end_row=hdr_r, end_column=5)
    row += 1
    for k, v, g in cfg["toolkit"]:
        body(ws.cell(row=row, column=2, value=k), bold=True)
        body(ws.cell(row=row, column=3, value=v))
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=5)
        body(ws.cell(row=row, column=6, value=g))
        ws.row_dimensions[row].height = 36
        row += 1
    widths(ws, [w for _, w in dev_cols])
    ws.freeze_panes = "C5"

    # ---------- 08_User_Journey ----------
    ws = S["08_User_Journey"]
    title(ws, f"[사용자여정] {T} Top 15 — 누가, 언제, 무엇을 넣고, 무엇을 받는가",
          "[읽는법] 사용자 인풋(직접 입력)과 시스템 인풋(자동 연동)을 구분, 절차는 사용자 클릭 기준 5단계, 화면은 텍스트 목업(회사명·금액은 예시). 순위·아이템은 02_AI_100과 수식 연동.", 12)
    uj_cols = [("순위", 6), ("AI 아이템", 24), ("실사용자", 18), ("사용 채널·트리거", 22), ("사용자 인풋 (직접 입력)", 24),
               ("시스템 인풋 (자동 연동)", 24), ("사용 절차 (①~⑤)", 26), ("아웃풋 (파일·결과물)", 22),
               ("아웃풋 화면 예시 (텍스트 목업)", 36), ("사람 확인·승인 포인트", 24), ("Before → After", 22), ("성공 판정 KPI", 22)]
    hdr(ws, 4, [h for h, _ in uj_cols], 36)
    for k, name in enumerate(top15):
        row = 5 + k
        d = cfg["journey"][name]
        assert len(d) == 10, (name, len(d))
        vals = [f"='02_AI_100'!A{k+2}", f"='02_AI_100'!B{k+2}", *d]
        for j, v in enumerate(vals, 1):
            body(ws.cell(row=row, column=j, value=v), center=(j == 1), bold=(j == 2))
        ws.row_dimensions[row].height = 150
    widths(ws, [w for _, w in uj_cols])
    ws.freeze_panes = "C5"

    # ---------- 01_Executive ----------
    ws = S["01_Executive"]
    title(ws, f"{T} AI 도입 100대 아이템 | 효과·우선순위·SaaS 가격모델 (Version 2)",
          f"[기준일] {cfg['date']}  |  [타깃] {cfg['target_desc']}  |  [양식] 3개 타깃 공통 V2 템플릿", 9)
    rows = [("[분석 기준]", "경제효과 40 + 적용범위 20 + 성과속도 15 + 구현용이성 10 + KPI 측정성 15 = 100점 (02 시트에 1~5점 입력 → 수식 환산)")]
    rows += [(f"[핵심 시사점 {i+1}]", v) for i, v in enumerate(cfg["insights"])]
    rows += [("[가격 원칙]", cfg["price_principle"]), ("[첫 상품 제안]", cfg["first_product"])]
    r = 4
    for k, v in rows:
        body(ws.cell(row=r, column=1, value=k), bold=True)
        c = ws.cell(row=r, column=2, value=v)
        body(c)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=9)
        ws.row_dimensions[r].height = 32
        r += 1
    r += 1
    kpi_r = r
    kpis = [("총 아이템", "=COUNTA('02_AI_100'!B:B)-1", "0"),
            ("평균 효과점수", "=ROUND(AVERAGE('02_AI_100'!L:L),1)", "0.0"),
            ("S·A+ 아이템", "=COUNTIF('02_AI_100'!M:M,\"S*\")+COUNTIF('02_AI_100'!M:M,\"A+*\")", "0"),
            ("분석 영역", "=COUNTA('05_Category_Map'!A:A)-2", "0")]
    for k, (lab, f, fmt) in enumerate(kpis):
        col = 1 + k * 2
        c = ws.cell(row=kpi_r, column=col, value=lab)
        c.font, c.fill, c.alignment = HDR_FONT, HDR_FILL, CENTER
        ws.merge_cells(start_row=kpi_r, start_column=col, end_row=kpi_r, end_column=col + 1)
        c = ws.cell(row=kpi_r + 1, column=col, value=f)
        c.font, c.fill, c.alignment, c.number_format = KPI_FONT, KPI_FILL, CENTER, fmt
        ws.merge_cells(start_row=kpi_r + 1, start_column=col, end_row=kpi_r + 1, end_column=col + 1)
    ws.row_dimensions[kpi_r + 1].height = 34
    r = kpi_r + 3
    ws.cell(row=r, column=1, value="[Top 15 우선 도입 아이템] 02 시트 1~15위 자동 연동").font = SEC_FONT
    r += 1
    hdr(ws, r, ["순위", "AI 아이템", "영역", "효과점수", "효과등급", "대표 KPI 개선", "Basic 월요금(원)", "도입기간", "개발 방법 (클릭→07)"])
    top_hdr = r
    for k in range(15):
        row = top_hdr + 1 + k
        src = k + 2
        vals = [f"='02_AI_100'!A{src}", f"='02_AI_100'!B{src}", f"='02_AI_100'!C{src}", f"='02_AI_100'!L{src}",
                f"='02_AI_100'!M{src}", f"='02_AI_100'!N{src}", f"='02_AI_100'!R{src}", f"='02_AI_100'!O{src}",
                f"=\"[개발가이드] \"&'07_Top15_Dev_Guide'!C{5+k}"]
        for j, v in enumerate(vals, 1):
            c = ws.cell(row=row, column=j, value=v)
            body(c, center=(j in (1, 3, 4, 5, 8)), fmt="#,##0" if j == 7 else None)
        ws.cell(row=row, column=9).hyperlink = f"#'07_Top15_Dev_Guide'!A{5+k}"
        ws.cell(row=row, column=9).font = Font(name="맑은 고딕", size=10, color="0563C1", underline="single")
        ws.row_dimensions[row].height = 30
    widths(ws, [14, 34, 13, 9, 11, 34, 13, 9, 34])
    ws.freeze_panes = "A4"

    # ---------- A1_V1_원본 ----------
    ws = S["A1_V1_원본"]
    ws["A1"] = f"[V1 원본 보존] {cfg['v1_file']} — 수정 없이 값만 보관 (V2 가공 전 비교용). V1 고유 정보(아이템별 프롬프트·GitHub 등)는 여기서 확인."
    ws["A1"].font = SEC_FONT
    r = 3
    for block_title, rows_ in cfg["v1_raw"]:
        ws.cell(row=r, column=1, value=block_title).font = SEC_FONT
        r += 1
        for k, rv in enumerate(rows_):
            for j, v in enumerate(rv, 1):
                if isinstance(v, str) and v.startswith("="):
                    v = "'" + v  # 원본 수식은 텍스트로 보존
                c = ws.cell(row=r, column=j, value=v)
                c.font = HDR_FONT if k == 0 else BASE_FONT
                if k == 0:
                    c.fill = HDR_FILL
                c.alignment = Alignment(wrap_text=False, vertical="top")
            r += 1
        r += 2
    for j in range(1, 20):
        ws.column_dimensions[get_column_letter(j)].width = 22
    ws.sheet_properties.tabColor = "A6A6A6"

    for n in sheets[:-1]:
        S[n].sheet_view.zoomScale = 90
    S["00_V1_진단"].sheet_properties.tabColor = "C00000"
    S["01_Executive"].sheet_properties.tabColor = NAVY
    wb.active = 1
    wb.save(out_path)
    return items
