# -*- coding: utf-8 -*-
import itertools, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATE = "2026-09-26"


def load(name):
    return json.load(open(os.path.join(HERE, name), encoding="utf-8"))


def fit_ratings(target, ease, speed_prior=4, kpi_prior=4):
    """V1 총점을 5개 기준(1~5)으로 분해: 용이성은 V1 난이도에서 고정, 나머지는 총점에 가장 근접하도록 탐색."""
    best = None
    for e, a, s, k in itertools.product(range(1, 6), repeat=4):
        tot = 8 * e + 4 * a + 3 * s + 2 * ease + 3 * k
        cost = abs(tot - target) * 10 + abs(s - speed_prior) * 2 + abs(k - kpi_prior) * 2 + abs(a - 4) + (5 - e)
        if best is None or cost < best[0]:
            best = (cost, [e, a, s, ease, k])
    return best[1]


PRICE_STEPS = [
    ("1. 경제가치 계산", "절감 인건비 + 매출총이익 증가 + 직접비 절감 + 오류·리스크 감소액을 월 기준으로 환산 (04 계산기)"),
    ("2. Value Capture", "검증 가능한 월 가치의 10~25%를 1차 가격 범위로 설정 (진입기 10~15% → 효과 검증 후 상향)"),
    ("3. 경쟁 앵커", "06 시트의 공식 가격(좌석형 AI·CRM·CS AI·메시징 단가)을 하한/상한 참고치로 사용"),
    ("4. 구현/운영 원가", "LLM·API·메시지 실비·저장소·고객지원 원가가 요금의 20~30% 이하가 되도록 사용 한도 설정"),
    ("5. 과금구조 선택", "좌석형/정액/사용량/성과연동 중 고객 KPI와 가장 직접 연결되는 방식 선택, Basic·Pro 2단 + 연간할인"),
]

COMMON_SOURCES = {
    "S1": ("McKinsey - Economic potential of generative AI",
           "https://www.mckinsey.com/capabilities/tech-and-ai/our-insights/the-economic-potential-of-generative-ai-the-next-productivity-frontier",
           "생성형 AI 가치의 약 75%가 고객운영·마케팅/영업·SW·R&D에 집중 — 영역별 경제효과 가중 근거"),
    "S2": ("OECD - AI adoption by SMEs (2025)",
           "https://www.oecd.org/en/publications/ai-adoption-by-small-and-medium-sized-enterprises_426399c1-en.html",
           "SME AI 도입의 생산성 잠재력과 도입 장벽(데이터·인력·비용) — 구현용이성·도입기간 가정 근거"),
    "S3": ("OECD - AI and the labour market in Korea",
           "https://www.oecd.org/en/publications/artificial-intelligence-and-the-labour-market-in-korea_68ab1a5a-en/full-report/overview_ad148dd1.html",
           "한국 기업의 AI 도입률·성과 인식 — 국내 적용 가능성 근거"),
    "S4": ("Microsoft - 2025 Work Trend Index (SMB)",
           "https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/microsoft/final/en-us/microsoft-brand/documents/2025-WTI-SMB-Infographic.pdf",
           "SMB 리더의 생산성 압박·에이전트 도입 계획 — 메일·회의·문서 코파일럿 효과 근거"),
    "S5": ("Microsoft - 2026 Work Trend Index (Korea)",
           "https://news.microsoft.com/source/asia/2026/06/15/2026-work-trend-index/?lang=ko",
           "AI 사용자의 고부가가치 업무 전환 — 보고·분석 자동화 근거"),
    "S6": ("OpenAI - ChatGPT Business pricing", "https://openai.com/ko-KR/business/pricing/",
           "범용 업무 AI 좌석형 가격 앵커 (조회일 기준 요금제 확인)"),
    "S7": ("Microsoft 365 Copilot pricing (Korea)", "https://www.microsoft.com/ko-kr/microsoft-365-copilot/pricing",
           "업무 코파일럿 국내 사용자당 월 가격 앵커"),
    "S8": ("Intercom - Fin AI Agent pricing", "https://www.intercom.com/pricing",
           "CS AI 좌석 + 해결건(outcome) 과금 사례 — 성과연동형 근거"),
    "S9": ("HubSpot - Sales Hub pricing", "https://www.hubspot.com/pricing/sales",
           "영업 CRM/Sales AI 좌석 + 크레딧 과금 사례"),
    "S10": ("SOLAPI - 알림톡·문자 가격 정책", "https://solapi.com/pricing",
            "카카오 알림톡 건당 단가(월 발송량 구간별) — 메시지 실비 분리 과금 근거"),
    "S11": ("중소벤처기업부 - 2025년 소상공인 실태조사", "https://www.mss.go.kr/site/smba/foffice/ex/statDB/StReportContentDetailView.do?gb=1&reSeq=2187",
            "소상공인 613.4만개·기업체당 종사자 1.57명 — 1인·가족 운영 전제(좌석 1~2개, 월 1~10만원대) 근거"),
    "S12": ("Apollo.io - Pricing", "https://www.apollo.io/pricing",
            "영업 인텔리전스 좌석형 앵커: 연간결제 기준 $49~$119/좌석/월 (조회일 기준)"),
    "S13": ("네이버웍스 - 클로바노트 이용요금", "https://naver.worksmobile.com/pricing/clovanote/",
            "국내 음성 기록·요약 서비스의 사용량(분·회) 기반 과금 앵커"),
    "S14": ("국가법령정보센터 - 정보통신망법 제50조(광고성 정보 전송 제한)",
            "https://www.law.go.kr/법령/정보통신망이용촉진및정보보호등에관한법률",
            "(광고) 표기·수신거부·야간(21~08시) 전송 제한 — 메시지·콜드메일 아이템 가드레일"),
    "S15": ("국가법령정보센터 - 개인정보 보호법", "https://www.law.go.kr/법령/개인정보보호법",
            "고객·연락처·통화녹음 처리 시 동의·목적 제한·마스킹 — 전 아이템 공통 리스크"),
}


def sources(codes):
    return [(c, *COMMON_SOURCES[c]) for c in codes]


TOOLKIT = [
    ("[워크플로·앱 빌더]", "n8n·Dify·Flowise로 트리거→LLM→연동을 시각적으로 구성, PoC 후 셀프호스팅", "https://github.com/n8n-io/n8n / https://github.com/langgenius/dify"),
    ("[모델 게이트웨이]", "LiteLLM으로 Claude·GPT·Gemini·HyperCLOVA X를 하나의 API로 교체·비용 추적 (단순 생성=경량 모델, 장문·법률=상위 모델)", "https://github.com/BerriAI/litellm"),
    ("[프롬프트 버전관리]", "레포 /prompts/{아이템}/v1.md + /schemas(JSON) + /evals 구조, PR로 변경 리뷰", "레포 예: /prompts /schemas /evals /app"),
    ("[프롬프트 테스트]", "promptfoo로 아이템별 평가셋(20~50문항)·금지어·글자수·JSON 형식 회귀테스트 → GitHub Actions에서 PR마다 실행", "https://github.com/promptfoo/promptfoo"),
    ("[운영 관측·로그]", "Langfuse로 호출 로그·비용·사용자 피드백 추적 (사용량 과금 근거로 활용)", "https://github.com/langfuse/langfuse"),
    ("[결제·메시징]", "PortOne·토스페이먼츠 정기결제(빌링키), 알림톡·문자는 솔라피 등 선충전 실비 + 관리비로 분리", "https://solapi.com/pricing"),
    ("[AI 코딩 절차]", "CLAUDE.md에 요구사항·스택·금지사항 → 스펙·JSON 스키마 먼저 → 테스트 → 구현 → PR 자동리뷰", "https://github.com/anthropics/claude-code"),
    ("[보안·컴플라이언스]", "개인정보 마스킹 후 API 전송, 학습 미사용(ZDR) 계약, 금액·발송·법률 판단은 사람 승인(Human-in-the-loop)", "개인정보보호법·정보통신망법 체크"),
    ("[확인 필요] 라이선스", "도입 전 README·LICENSE 확인: MIT/Apache 우선, n8n(Sustainable Use)·AGPL 계열은 상업 SaaS 재판매 조건 검토", "LICENSE 파일 직접 확인"),
]
