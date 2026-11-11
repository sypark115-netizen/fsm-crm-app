# -*- coding: utf-8 -*-
"""키 메시지 Skill 공통 모듈.

- 사전(AI 상투어, 기술어, 가치어, 주장어, Story Role, Audience)
- 텍스트 정규화 / 토큰화 / 유사도
- Fact Guard (숫자·고유명사 보존 검사)

메시지 판단 로직은 analyze_messages.py, 사전은 이 파일 한 곳에서 관리한다.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = 1

# --------------------------------------------------------------------------
# 1. AI스러운 표현 / 제안서 상투어 사전
#    (id, regex, category, severity(1~3), 수정 힌트)
#    단어 자체를 지우라는 뜻이 아니다. "추상성·과장·상투·번역투" 신호로만 쓴다.
# --------------------------------------------------------------------------
AI_PATTERNS = [
    ("TONGHAE", r"(을|를)\s*통(해|하여|한)", "번역투", 1, "'~로' 또는 동사로 바로 쓴다"),
    ("ITONGHAE", r"이를\s*통(해|하여)", "번역투", 1, "앞 문장과 합치거나 결과를 바로 쓴다"),
    ("EISSEO", r"에\s*있어(서)?", "번역투", 1, "'~에서', '~할 때'로 바꾼다"),
    ("GIBAN", r"기반(으로|의|하여|한)?", "상투/번역투", 1, "무엇을 하는지 동사로 쓴다"),
    ("CONJ", r"(^|[\s.,])(또한|나아가|아울러|더불어)(\s|,)", "접속사 남발", 1, "접속사 없이 결론부터"),
    ("EFFECTIVE", r"효과적(으로|인)|효율적(으로|인)", "추상 부사", 1, "무엇이 얼마나 좋아지는지"),
    ("SYSTEMATIC", r"체계적(으로|인)", "추상 부사", 1, "실제 절차·체계 이름으로"),
    ("INNOVATION", r"디지털\s*혁신|혁신(적인|적으로|적)?", "추상/과장", 2, "바뀌는 업무를 쓴다"),
    ("DIFFERENT", r"차별화(된|한|된다)", "근거 없는 형용사", 2, "무엇이 다른지 Evidence로"),
    ("OPTIMAL", r"최적(의|화된|화)", "근거 없는 형용사", 2, "기준을 쓴다(비용·성능·일정)"),
    ("LEADING", r"선도(적|하는|적인)", "과장", 2, "근거(순위·실적) 또는 삭제"),
    ("ADVANCE", r"고도화", "추상 명사", 1, "무엇을 어떻게 바꾸는지"),
    ("MAXIMIZE", r"극대화", "과장", 1, "무엇이 늘어나는지"),
    ("ACCEL", r"가속화", "추상 명사", 1, "무엇이 빨라지는지"),
    ("EPOCH", r"획기적(인|으로)?", "과장", 2, "근거 수치 또는 삭제"),
    ("SUCCESS", r"성공적(인|으로)", "상투", 1, "성공 기준을 쓴다"),
    ("INTELLIGENT", r"지능형|[Ii]ntelligent|스마트한", "버즈워드", 1, "AI가 실제로 하는 일을 쓴다"),
    ("E2E", r"[Ee]nd[- ]?to[- ]?[Ee]nd|엔드\s*투\s*엔드|E2E", "버즈워드", 1, "어디서 어디까지인지 업무로"),
    ("SEAMLESS", r"[Ss]eamless|끊김\s*없(는|이)", "버즈워드", 1, "무엇이 끊기지 않는지"),
    ("ROLE", r"중요한\s*역할을\s*(합니다|한다|수행)", "상투", 2, "무슨 역할인지 동사로"),
    ("CONTRIB", r"기여(할\s*수\s*있|합니다|하겠습니다)", "약한 결론", 2, "결과를 단정적으로(근거 있을 때)"),
    ("CAN", r"(할|될|드릴)\s*수\s*있(습니다|다|음|을\s*것)", "약한 결론", 1, "'~합니다'로 결론부터"),
    ("RICH", r"풍부한\s*(경험|노하우|역량|레퍼런스)", "근거 없는 형용사", 2, "건수·기간·사례로"),
    ("BEST", r"최고(의|\s*수준)|독보적|탁월한|우수한|업계\s*최초", "근거 없는 형용사", 2, "근거 없으면 삭제/ESCALATE"),
    ("NOMINAL", r"(구현|실현|제공|지원|확보|강화|제고)(을|를)?\s*(위한|통한)", "명사형 나열", 1, "동사 문장으로"),
    ("PROVIDE", r"(서비스|솔루션|환경|체계)(를|을)\s*제공(합니다|함|한다)", "상투", 1, "고객이 얻는 변화를 주어로"),
    ("WE", r"당사(의|는|가|만의)", "자기중심", 1, "고객을 주어로"),
    ("PARADIGM", r"패러다임|새로운\s*가치|가치\s*창출|미래\s*지향", "추상/과장", 2, "구체 변화로"),
    ("FOUNDATION", r"(초석|발판|토대)(을|를)?\s*(마련|구축)", "상투", 2, "무엇이 가능해지는지"),
]
AI_PATTERNS_RE = [(i, re.compile(r), c, s, h) for i, r, c, s, h in AI_PATTERNS]

# 결과가 추상적인 표현 (고객 변화가 안 보임)
ABSTRACT_OUTCOMES = re.compile(
    r"디지털\s*혁신|혁신(을|적)|경쟁력\s*(강화|제고)|가치\s*창출|새로운\s*가치|패러다임|"
    r"미래\s*(지향|성장)|지능형\s*업무환경|혁신적\s*업무환경|업무\s*혁신|DX\s*실현|디지털\s*전환을\s*(선도|가속)|"
    r"생산성(을)?\s*극대화|초석|토대|비즈니스\s*가치"
)

# 증거가 필요한 주장어
CLAIM_WORDS = re.compile(
    r"차별화|역량|노하우|풍부한|검증된|안정적|신뢰|최고|1위|독보적|전문(성|인력)|우수한|보장|"
    r"경험(을|이|과)?\s*(바탕|기반|보유)|업계\s*최초|유일"
)

# 기술어 → (도메인, Capability 힌트). 힌트는 일반 Capability이며 '사실'이 아니다.
TECH_TERMS = [
    (r"AI\s*Agent|Agentic\s*AI|에이전트|(?<![A-Za-z])Agent(?![A-Za-z])", "AX", "자료 탐색·분석·작성·실행을 AI가 먼저 처리"),
    (r"생성형\s*AI|Gen\s*AI|GenAI|LLM|GPT|sLLM", "AI", "요약·초안 작성·질의응답"),
    (r"RAG|검색\s*증강", "AI", "사내 문서 근거로 답변"),
    (r"(?<![A-Za-z])AI(?![A-Za-z])|인공지능|머신러닝|딥러닝", "AI", "분류·예측·판단 보조"),
    (r"RPA|업무\s*자동화|자동화", "업무자동화", "반복 입력·조회·대사 작업을 자동 수행"),
    (r"AICC|콜봇|챗봇|voicebot|보이스봇|STT|TTS", "AICC", "단순 문의는 자동 응대, 상담원은 복잡 상담에 집중"),
    (r"[Cc]loud|클라우드|IaaS|PaaS|SaaS|하이브리드", "Cloud", "변동 수요에 맞춰 자원을 늘리고 줄임"),
    (r"MSP|Managed\s*Service|운영\s*대행|관제", "MSP", "모니터링·장애 대응·변경 관리를 대행"),
    (r"[Dd]ata\s*[Pp]latform|데이터\s*플랫폼|[Dd]ata\s*[Ll]ake|레이크하우스|DW|데이터\s*허브|데이터\s*통합", "Data", "흩어진 데이터를 한 곳에서 조회·분석"),
    (r"[Mm]igration|마이그레이션|이관|전환", "SI/Infra", "서비스 영향 없이 옮김"),
    (r"[Dd]ata\s*[Cc]enter|데이터\s*센터|데이터센터|IDC", "Infra", "센터 이전·통합·이중화"),
    (r"[Nn]etwork|네트워크|SD-?WAN|회선|5G", "Network", "지점·현장 연결 품질과 장애 대응"),
    (r"보안|[Ss]ecurity|[Zz]ero\s*[Tt]rust|제로\s*트러스트|SOC|SIEM|EDR", "Security", "위협 탐지·차단·대응 시간 단축"),
    (r"[Kk]ubernetes|MSA|컨테이너|DevOps|CI/CD", "Cloud", "배포·변경 주기 단축"),
    (r"(?<![A-Za-z])API(?![A-Za-z])|인터페이스|연동|EAI|ESB", "Integration", "기존 시스템과 연결"),
    (r"(?<![A-Za-z])(ERP|CRM|MES|SCM|PLM|WMS|SAP)(?![A-Za-z])", "SI", "기간계 데이터·업무 연계"),
    (r"(?<![A-Za-z])DX(?![A-Za-z])|[Dd]igital\s*[Tt]ransformation|디지털\s*전환", "DX", "업무 방식 자체를 디지털로 바꿈"),
    (r"(?<![A-Za-z])AX(?![A-Za-z])", "AX", "업무에 AI를 붙여 사람·AI 역할을 재설계"),
    (r"[Ii]ntelligent\s*[Ww]orkplace|스마트\s*오피스|디지털\s*워크플레이스|지능형\s*업무환경", "AX", "자료 찾기·정리·초안 작성을 AI가 맡음"),
    (r"플랫폼|[Pp]latform|솔루션|아키텍처|[Aa]rchitecture|인프라", "General IT", "(구체 Capability 확인 필요)"),
]
TECH_TERMS_RE = [(re.compile(r), d, h) for r, d, h in TECH_TERMS]

# 고객 변화·업무·가치가 드러나는 단어
VALUE_TERMS = re.compile(
    r"시간|단축|줄(이|여|입|인)|감소|절감|비용|TCO|매출|수익|생산성|오류|실수|누락|장애|중단|없이|무중단|"
    r"대응|처리|응대|복구|가용성|SLA|리스크|위험|일정|납기|품질|정확(도|히)|빠르|즉시|실시간|한\s*번에|하나의|"
    r"집중|맡(고|기|습)|판단|승인|검토|의사\s*결정|선별|예외|담당자|사람|상담원|현업|고객|직원|"
    r"연결|이어|통합(해|하여|합니다)|유지|그대로|단계적|확산|재사용|표준|"
    r"매일|월|주|건|명|%|배|배로"
)
# 구체적인 업무·프로세스 명사 (Customer/Process Specificity 신호)
PROCESS_NOUNS = re.compile(
    r"상담|문의|견적|설계|주문|수주|발주|구매|정산|청구|결산|재고|생산|품질|설비|점검|검사|물류|배송|"
    r"영업|마케팅|계약|심사|여신|보험금|민원|접수|진단|보고서|회의록|문서|자료|초안|매뉴얼|"
    r"서버|회선|센터|장애|변경|배포|백업|DR|로그|티켓|요청|승인|결재|인사|급여|채용|교육|"
    r"점포|매장|지점|공장|현장|콜센터|고객센터|상담원|임직원|담당자|협력사|"
    r"이전|전환|이관|통합|연동|조회|검색|분석|예측|추천|요약|번역|작성|입력|대사|모니터링"
)
HUMAN_ROLE = re.compile(r"담당자|사람|직원|상담원|현업|승인|검토|판단|결정|확인|예외|최종")
AUTOMATION = re.compile(r"자동화|자동\s*처리|무인|완전\s*자동|[Ee]nd[- ]?to[- ]?[Ee]nd|E2E")
AI_ACTOR = re.compile(r"(?<![A-Za-z])AI(?![A-Za-z])|Agent|에이전트|생성형|LLM|봇|RPA")

# 경쟁사 Swap Test: 회사명만 바꿔도 통하는 일반론 신호
GENERIC_SELF = re.compile(
    r"당사(의|는|가|만의)?|저희|우리\s*회사|(풍부한|오랜|다양한)\s*(경험|노하우|레퍼런스)|"
    r"차별화된\s*(기술|역량|서비스|솔루션)|최고의\s*(전문가|품질|서비스)|원스톱|토탈\s*솔루션|"
    r"최적의\s*(서비스|솔루션|방안)|고객\s*만족|글로벌\s*수준"
)

# Story Role 키워드 (장표 단위)
STORY_ROLES = [
    ("Why", r"배경|현황|문제|이슈|과제|Pain|진단|이해|환경\s*분석|As-?Is|요구사항\s*분석"),
    ("What", r"목표|방향|비전|전략|개념|개요|To-?Be|추진\s*방안|제안\s*요약|핵심\s*제안"),
    ("Why Us", r"차별|강점|역량|경쟁력|Why\s*Us|선정\s*사유|수행\s*실적|레퍼런스|Reference"),
    ("How", r"아키텍처|Architecture|구성|적용\s*방안|연동\s*방안|구축\s*방안|수행\s*방안|방법론|일정|조직|이행|전환\s*방안|이전\s*방안|운영\s*방안|거버넌스|Governance"),
    ("Evidence", r"사례|실적|PoC|검증|결과|벤치마크|Benchmark|인증"),
    ("Value", r"기대\s*효과|효과|성과|ROI|가치|TCO|Value|KPI"),
]
STORY_ROLES_RE = [(n, re.compile(r, re.I)) for n, r in STORY_ROLES]

AUDIENCE_RULES = [
    ("CEO / 경영진", r"경영|전략|비전|기대\s*효과|ROI|투자|성과|매출|Executive|Summary|요약|총괄"),
    ("CIO / IT 담당 임원", r"IT\s*전략|거버넌스|TCO|표준|중장기|로드맵|Roadmap|운영\s*체계"),
    ("IT / AX 담당자", r"아키텍처|Architecture|인터페이스|연동|API|인프라|서버|네트워크|보안|Cloud|클라우드|데이터\s*모델|전환|이전|구성도|DB|SLA"),
    ("사업부장", r"사업부|영업|매출|고객\s*경험|채널|시장|수주"),
    ("현업 담당자", r"업무\s*(흐름|프로세스|절차)|현업|화면|사용자|담당자|교육|매뉴얼|상담|견적"),
    ("구매 / 재무 / 관리", r"가격|비용|단가|예산|계약|구매|지급|투입\s*인력|M/M|MM"),
]
AUDIENCE_RE = [(n, re.compile(r, re.I)) for n, r in AUDIENCE_RULES]

REWRITE_CATEGORIES = [
    "Abstract → Concrete",
    "Tech → Value",
    "Generic → Differentiated",
    "AI Tone → Human Tone",
    "Feature → Business Impact",
    "Automation → Human/AI Role",
    "Long → Concise",
    "Evidence Lift",          # 본문 Evidence를 메시지로 끌어올림
    "Keep",
]

STATUSES = ["GREEN", "YELLOW", "RED", "ESCALATE"]
DECISIONS = ["ACCEPT", "EDIT", "KEEP", "ESCALATE"]

# --------------------------------------------------------------------------
# 2. 텍스트 유틸
# --------------------------------------------------------------------------
def norm_text(s: str | None) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFC", str(s))
    s = s.replace("\v", "\n").replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def cmp_key(s: str | None) -> str:
    """원문 일치 비교용 키 (공백·줄바꿈 무시)."""
    return re.sub(r"\s+", "", norm_text(s))


HANGUL = re.compile(r"[가-힣]+")
LATIN = re.compile(r"[A-Za-z][A-Za-z0-9+\-/]*")
STOP = set("및 등 을 를 이 가 은 는 의 에 로 으로 와 과 도 한 하는 합니다 있는 위한 통한 통해 대한 관련 기반".split())
JOSA = re.compile(r"(은|는|이|가|을|를|의|에|에서|으로|로|와|과|도|만|까지|부터|에게|께|이며|하고|하여|해서|합니다|입니다|한다|된다|됩니다|하는|하며|되는)$")


def tokens(s: str) -> set[str]:
    """한국어 문자 bigram + 영문 단어 토큰 (형태소 분석기 없이 동작)."""
    s = norm_text(s)
    out: set[str] = set()
    for w in LATIN.findall(s):
        if len(w) >= 2:
            out.add(w.lower())
    for w in HANGUL.findall(s):
        w = JOSA.sub("", w)
        if not w or w in STOP:
            continue
        if len(w) == 1:
            continue
        for i in range(len(w) - 1):
            out.add(w[i:i + 2])
    return out


def similarity(a: str | set, b: str | set) -> float:
    ta = a if isinstance(a, set) else tokens(a)
    tb = b if isinstance(b, set) else tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    return inter / min(len(ta), len(tb)) * 0.5 + inter / len(ta | tb) * 0.5


# --------------------------------------------------------------------------
# 3. Fact / Number / Meaning Guard
# --------------------------------------------------------------------------
NUM_RE = re.compile(r"(?<![A-Za-z0-9])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?")
PROTECTED_LATIN = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Za-z0-9]*[A-Z0-9][A-Za-z0-9\-+.]*|[A-Z]{2,}[a-z]*|[A-Za-z]+-?\d+[A-Za-z0-9]*)(?![A-Za-z0-9])")
QUOTED = re.compile(r"[「『“\"']([^」』”\"']{2,40})[」』”\"']")
COMPANY = re.compile(r"(㈜\s*[가-힣A-Za-z0-9]+|[가-힣A-Za-z0-9]+\s*㈜|주식회사\s*[가-힣A-Za-z0-9]+|[가-힣A-Za-z0-9]+(?:社))")
# 영문이지만 사실성 없는 일반어(Guard 대상 제외)
COMMON_LATIN = set("AI IT AX DX OK PM PMO KPI ROI".split())


def numbers(s: str) -> list[str]:
    out = []
    for m in NUM_RE.finditer(norm_text(s)):
        whole = m.group(1).replace(",", "")
        frac = m.group(2)
        out.append(whole + ("." + frac if frac else ""))
    return out


def protected_terms(s: str) -> set[str]:
    s = norm_text(s)
    out = set()
    for m in PROTECTED_LATIN.finditer(s):
        t = m.group(1)
        if t.upper() in COMMON_LATIN:
            continue
        out.add(t)
    for m in QUOTED.finditer(s):
        out.add(m.group(1))
    for m in COMPANY.finditer(s):
        out.add(re.sub(r"\s+", "", m.group(1)))
    return out


def fact_guard(original: str, revised: str, corpus_numbers: set[str] | None = None,
               corpus_text: str = "") -> dict:
    """수정문이 원문의 사실(숫자·고유명사)을 바꾸거나 새로 만들었는지 검사.

    level: OK / WARN / ERROR
      ERROR  : 원문·근거자료 어디에도 없는 숫자가 새로 등장 / 원문 숫자 값이 바뀜
      WARN   : 원문 숫자·고유명사가 빠짐, 근거자료에서 끌어온 숫자·고유명사 사용(출처 확인 필요)
    """
    res = {"level": "OK", "messages": []}
    if not revised or not norm_text(revised):
        return res
    o_nums, r_nums = numbers(original), numbers(revised)
    corpus_numbers = corpus_numbers or set()
    from collections import Counter
    oc, rc = Counter(o_nums), Counter(r_nums)
    new_nums = [n for n in rc if n not in oc]
    dropped = [n for n in oc if n not in rc]
    for n in new_nums:
        if n in corpus_numbers:
            res["messages"].append(f"근거자료 숫자 사용: {n} (출처 확인)")
            res["level"] = max_level(res["level"], "WARN")
        else:
            res["messages"].append(f"원문·근거에 없는 숫자 생성: {n}")
            res["level"] = "ERROR"
    for n in dropped:
        res["messages"].append(f"원문 숫자 누락: {n}")
        res["level"] = max_level(res["level"], "WARN")
    o_terms, r_terms = protected_terms(original), protected_terms(revised)
    ck = cmp_key(corpus_text)
    for t in sorted(r_terms - o_terms):
        if cmp_key(t) and cmp_key(t) in ck:
            res["messages"].append(f"근거자료 고유명사 사용: {t}")
        else:
            res["messages"].append(f"원문에 없는 고유명사/기술명: {t}")
        res["level"] = max_level(res["level"], "WARN")
    for t in sorted(o_terms - r_terms):
        if cmp_key(t) not in cmp_key(revised):
            res["messages"].append(f"원문 고유명사/기술명 누락: {t}")
            res["level"] = max_level(res["level"], "WARN")
    return res


def max_level(a: str, b: str) -> str:
    order = {"OK": 0, "WARN": 1, "ERROR": 2}
    return a if order[a] >= order[b] else b


# --------------------------------------------------------------------------
# 4. IO
# --------------------------------------------------------------------------
def load_json(p) -> dict:
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def dump_json(obj, p):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def safe_output_path(src: Path, suffix: str, ext: str | None = None, out: str | None = None) -> Path:
    """원본을 절대 덮어쓰지 않는 출력 경로. 이미 있으면 _v3, _v4..."""
    src = Path(src).resolve()
    ext = ext or src.suffix
    if out:
        p = Path(out).resolve()
    else:
        p = src.with_name(f"{src.stem}{suffix}{ext}")
    if p == src:
        raise SystemExit(f"[STOP] 출력 경로가 원본과 같습니다: {p}")
    if p.exists() and not out:
        m = re.search(r"_v(\d+)$", p.stem)
        n = int(m.group(1)) if m else 1
        base = p.stem[: m.start()] if m else p.stem
        while p.exists():
            n += 1
            p = p.with_name(f"{base}_v{n}{ext}")
    return p
