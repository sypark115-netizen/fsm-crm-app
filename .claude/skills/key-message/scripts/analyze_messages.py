# -*- coding: utf-8 -*-
"""Proposal Context Engine + IT·AX Tech-to-Value Engine + Governing/Key Message Engine
+ AI Writing QA + Fact/Evidence Guard (진단 단계).

입력 : content.json (extract_content.py 결과)
출력 :
  analysis.json         전체 진단 결과 (Context, Story, Message별 판정, Requirement Trace)
  analysis_brief.md     Claude/사람이 읽는 요약 (메시지 재작성 시 참고)
  recommendations.json  재작성 템플릿 — Claude가 ai_recommended / alt_a / alt_b / reason 등을 채운다

엔진은 '진단'만 한다. 문장 재작성은 Claude가 references 규칙에 따라 수행하고,
create_review_excel.py 가 Fact Guard / 재진단으로 다시 검증한다.

사용:
  python analyze_messages.py work/content.json -o work/
  python analyze_messages.py --text "당사의 차별화된 AI 기술을 기반으로 ..."   # 단일 문장 빠른 진단
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from km_common import (  # noqa: E402
    ABSTRACT_OUTCOMES, AI_ACTOR, AI_PATTERNS_RE, AUDIENCE_RE, AUTOMATION, CLAIM_WORDS, GENERIC_SELF,
    HUMAN_ROLE, PROCESS_NOUNS, SCHEMA_VERSION, STORY_ROLES_RE, TECH_TERMS_RE, VALUE_TERMS, dump_json,
    load_json, norm_text, numbers, similarity, tokens,
)

DEFAULT_LEARNING_LOG = Path(os.environ.get("KEY_MESSAGE_HOME", Path.home() / ".claude" / "key-message")) / "learning" / "decisions.jsonl"

FOOTER_NAME = re.compile(r"footer|slide\s*number|date|바닥글|슬라이드\s*번호|날짜|page\s*number|logo|로고", re.I)
FOOTER_TEXT = re.compile(r"^(\d{1,3}|-\s*\d+\s*-|page\s*\d+|confidential|copyright.*|ⓒ.*|©.*|대외비|내부용|\d{4}[.\-/]\d{1,2}([.\-/]\d{1,2})?)$", re.I)
TOC_RE = re.compile(r"^(목차|contents|agenda|index)$|^목\s*차$", re.I)
SECTION_NUM_RE = re.compile(r"^(\d{1,2}|[IVX]{1,4}|Part\s*\d+|Chapter\s*\d+)[.)]?\s+\S", re.I)
NAV_RE = re.compile(r"\s>\s|\(\s*\d+\s*/\s*\d+\s*\)\s*$")
DECL_END = re.compile(r"(니다|습니다|입니다|합니다|됩니다)\.?\s*$")
KEY_END = re.compile(r"(함|음|됨|확정|확보|제공|지원|적용|구현|전환|연계|처리|방지|단축|축소|해소)\.?\s*$")
FEATURE_END = re.compile(r"(Agent|에이전트|플랫폼|솔루션|시스템|모듈|엔진|Platform|Solution|Engine)\s*$")
SENTENCE_END = re.compile(r"(다|니다|요|함|임|음|됨|것|기|화|중)[.!]?$")
REQ_RE = re.compile(
    r"(해야\s*(한다|함|합니다)|하여야\s*(한다|함|하며)?|할\s*것|필요(함|하다|합니다)|요구(함|된다|됨)|"
    r"제시(할\s*것|하여야|해야)|바람|되어야|보장(할\s*것|해야|하여야))|"
    r"^(SFR|REQ|PER|SER|INR|DAR|TER|COR|PMR|PSR|QUR|SIR|ECR|CSR)[-_ ]?\d{2,4}", re.I)
EVIDENCE_HINT = re.compile(r"구축|수행|레퍼런스|Reference|사례|PoC|검증|SLA|인증|ISO|ISMS|CSAP|실적|운영\s*중|도입|특허|수상|무사고|무장애|가용률|\d")
WHY_NOW = re.compile(r"지금|올해|내년|20\d\d|규제|시행|만료|노후|EOS|EOL|종료|마감|시급|적기|골든\s*타임|전환\s*시점|계약\s*만료")
HOW_REAL = re.compile(r"단계(적|별)|연동|유지|그대로|전환|이전|이관|구성|일정|병행|리허설|시나리오|검증|파일럿|Pilot|PoC|\d+\s*(주|개월|단계)")
INDUSTRY = [
    ("금융", r"금융|은행|카드|보험|증권|캐피탈|여신|대출|핀테크"),
    ("제조", r"제조|공장|생산|설비|MES|품질\s*검사|라인|부품|반도체|자동차"),
    ("유통/리테일", r"유통|리테일|매장|점포|이커머스|커머스|쇼핑"),
    ("공공", r"공공\s*(기관|부문|서비스)|지자체|행정안전|중앙\s*부처|정부\s*(기관|부처)|공단"),
    ("통신/미디어", r"통신|미디어|방송|가입자|5G"),
    ("에너지/화학", r"에너지|발전|정유|화학|전력|가스"),
    ("의료/헬스케어", r"병원|의료|헬스케어|환자|제약"),
    ("물류", r"물류|배송|창고|WMS|운송|택배"),
    ("건설", r"건설|시공|현장\s*관리|플랜트"),
]
INDUSTRY_RE = [(n, re.compile(p)) for n, p in INDUSTRY]


# ===================================================================== assess
def assess(text: str, ctx: dict | None = None) -> dict:
    """메시지 1개 진단. ctx: {message_type, slide_evidence:[str], linked_evidence:[...], audience, governing}"""
    ctx = ctx or {}
    t = norm_text(text)
    one_line = t.replace("\n", " ")
    mtype = ctx.get("message_type", "Governing")
    res = {"text": t, "length": len(one_line)}

    # --- AI Writing QA
    hits = []
    for pid, rx, cat, sev, hint in AI_PATTERNS_RE:
        for m in rx.finditer(one_line):
            hits.append({"id": pid, "match": m.group(0).strip(), "category": cat, "severity": sev, "hint": hint})
    seen, uniq = set(), []
    for h in hits:
        k = (h["id"], h["match"])
        if k not in seen:
            seen.add(k)
            uniq.append(h)
    hits = uniq
    severity = sum(h["severity"] for h in hits)
    res["ai_patterns"] = hits
    res["ai_severity"] = severity

    # --- Tech-to-Value
    techs = []
    for rx, dom, hint in TECH_TERMS_RE:
        m = rx.search(one_line)
        if m and not any(m.group(0) in x["term"] or x["term"] in m.group(0) for x in techs):
            techs.append({"term": m.group(0), "domain": dom, "capability_hint": hint})
    value_hits = VALUE_TERMS.findall(one_line)
    process_hits = PROCESS_NOUNS.findall(one_line)
    nums = numbers(one_line)
    has_value = bool(value_hits) or bool(nums)
    has_process = bool(process_hits)
    tech_gap = bool(techs) and not has_value and not (has_process and len(process_hits) >= 2)
    res["tech_terms"] = techs
    res["value_terms"] = sorted(set(value_hits))
    res["process_terms"] = sorted(set(process_hits))
    res["numbers"] = nums

    # --- AX: Human vs AI 역할
    ax_role_gap = bool(AUTOMATION.search(one_line)) and bool(AI_ACTOR.search(one_line)) and not HUMAN_ROLE.search(one_line)
    res["ax_role_gap"] = ax_role_gap

    # --- Claim / Evidence
    claims = sorted(set(m.group(0) for m in CLAIM_WORDS.finditer(one_line)))
    slide_ev = [e for e in ctx.get("slide_evidence", []) if numbers(e) or EVIDENCE_HINT.search(e)]
    linked_ev = ctx.get("linked_evidence", [])
    has_evidence = bool(nums) or bool(slide_ev) or bool(linked_ev)
    unsupported_claim = bool(claims) and not has_evidence
    res["claims"] = claims
    res["has_evidence"] = has_evidence
    res["evidence_in_message"] = bool(nums)
    res["unsupported_claim"] = unsupported_claim

    abstract = bool(ABSTRACT_OUTCOMES.search(one_line))
    generic = bool(GENERIC_SELF.search(one_line)) and not nums and len(process_hits) < 2
    res["abstract_outcome"] = abstract
    res["competitor_swap"] = "YES" if (generic or (claims and not nums and not process_hits)) else "NO"

    # --- One Message
    # 절 수: 연결어미·쉼표만 센다 (가운뎃점·'및'은 명사 나열이므로 제외)
    clauses = 1 + len(re.findall(r"(하고|하며|하여|이며|이고|뿐\s*아니라|동시에|,)", one_line))
    sentences = len([s for s in re.split(r"[.!?]\s+|\n", t) if s.strip()])
    limit = 60 if mtype == "Governing" else 80
    one_msg_fail = sentences > 2 or res["length"] > limit + 30 or clauses >= 5
    res["clauses"] = clauses
    res["sentences"] = sentences

    # --- Five Question Test
    res["five_q"] = {
        "SO WHAT": has_value,
        "WHY US": (bool(nums) or bool(linked_ev) or bool(slide_ev)) and res["competitor_swap"] == "NO",
        "WHY NOW": bool(WHY_NOW.search(one_line)),
        "HOW REAL": bool(HOW_REAL.search(one_line)) or bool(nums) or len(process_hits) >= 2,
        "EVIDENCE": has_evidence,
    }

    # --- Governing ↔ Key 반복
    gov = ctx.get("governing")
    res["repeats_governing"] = bool(gov and mtype == "Key" and similarity(gov, one_line) >= 0.6)

    # --- Scores (1~5)
    def clamp(x):
        return max(1, min(5, round(x)))

    sc = {}
    sc["customer_relevance"] = clamp(2 + (1.5 if has_value else 0) + (1 if has_process else 0) - (1 if GENERIC_SELF.search(one_line) else 0) - (1 if abstract else 0))
    sc["one_message"] = clamp(5 - (2 if one_msg_fail else 0) - max(0, clauses - 2) * 0.7)
    sc["specificity"] = clamp(2 + min(2, len(set(process_hits)) * 0.8) + (1 if nums else 0) - (1.5 if abstract else 0))
    sc["differentiation"] = clamp(4 - (2 if res["competitor_swap"] == "YES" else 0) + (1 if nums or linked_ev else 0))
    sc["evidence"] = clamp((5 if nums else 3 if (slide_ev or linked_ev) else 2) - (1 if unsupported_claim else 0))
    sc["tech_to_value"] = clamp((4 if not techs else 3) + (1 if has_value else 0) - (2 if tech_gap else 0) - (1 if ax_role_gap else 0))
    jargon = len(re.findall(r"[A-Za-z]{3,}", one_line))
    aud = ctx.get("audience", "")
    sc["audience_fit"] = clamp(4 - (1.5 if aud.startswith("CEO") and jargon >= 2 else 0) - (1 if aud.startswith("현업") and jargon >= 3 else 0) + (0.5 if has_value else 0))
    sc["naturalness"] = clamp(5 - severity * 0.6)
    L = res["length"]
    sc["brevity"] = 5 if L <= 35 else 4 if L <= 50 else 3 if L <= 70 else 2 if L <= 95 else 1
    sc["memorability"] = clamp((sc["brevity"] + sc["specificity"] + sc["naturalness"]) / 3)
    res["scores"] = sc
    res["overall"] = round(sum(sc.values()) / len(sc), 2)

    # --- Status (규칙 순서 중요)
    problems, cats = [], []
    if hits:
        problems.append("AI/상투 표현: " + ", ".join(sorted(set(h["match"] for h in hits))))
    if abstract:
        problems.append("결과가 추상적 — 고객 업무·운영의 변화가 보이지 않음")
        cats.append("Abstract → Concrete")
    if tech_gap:
        problems.append("기술 설명만 있고 Capability·업무 변화·가치가 없음")
        cats.append("Tech → Value")
    if ax_role_gap:
        problems.append("자동화 주장에 AI와 사람의 역할 구분이 없음")
        cats.append("Automation → Human/AI Role")
    if res["competitor_swap"] == "YES":
        problems.append("Competitor Swap Test 실패 — 회사명만 바꿔도 경쟁사가 쓸 수 있음")
        cats.append("Generic → Differentiated")
    if unsupported_claim:
        problems.append("주장(" + ", ".join(claims) + ")을 뒷받침할 Evidence 없음")
    if one_msg_fail:
        problems.append("한 메시지에 주장이 여러 개이거나 너무 김")
        cats.append("Long → Concise")
    if res["repeats_governing"]:
        problems.append("Governing Message를 반복함 (Why/How/Evidence 역할 분리 필요)")
    if severity and not cats:
        cats.append("AI Tone → Human Tone")
    if slide_ev and not nums and (unsupported_claim is False) and claims:
        cats.append("Evidence Lift")

    abstract_red = abstract and not (nums and has_process)
    feature_label = mtype == "Key" and bool(techs) and not has_value and bool(FEATURE_END.search(one_line))
    if feature_label:
        problems.append("기능 이름만 있음 — 이 기능으로 업무가 어떻게 달라지는지 없음")
        cats.append("Feature → Business Impact")
    red = severity >= 4 or abstract_red or tech_gap or ax_role_gap or one_msg_fail or (res["competitor_swap"] == "YES" and severity >= 2)
    if unsupported_claim and not abstract_red and not tech_gap and not ax_role_gap:
        status = "ESCALATE"
    elif red:
        status = "RED"
    elif severity >= 1 or feature_label or abstract or res["length"] > limit or res["repeats_governing"] or (mtype == "Governing" and not has_value):
        status = "YELLOW"
    else:
        status = "GREEN"
    if status == "GREEN" and not has_process and not has_value and mtype == "Governing":
        status = "YELLOW"
        problems.append("고객이 얻는 것이 문장에 드러나지 않음")
    res["status"] = status
    res["problems"] = problems
    res["categories"] = cats or (["Keep"] if status == "GREEN" else ["AI Tone → Human Tone"])
    res["needs_evidence"] = unsupported_claim or (status in ("RED", "ESCALATE") and bool(claims) and not nums)

    # --- Tech-to-Value 체인 힌트 (사실 아님: Claude가 원문 근거로 채울 칸)
    if techs:
        res["tech_to_value_chain"] = [
            {"technology": x["term"], "capability": x["capability_hint"],
             "process_change": "(원문/근거에서 확인)", "business_impact": "(원문 수치가 있을 때만)",
             "executive_value": "(고객 의사결정 관점 한 줄)"} for x in techs[:3]]
    else:
        res["tech_to_value_chain"] = []
    res["evidence_request"] = evidence_request(res) if res["needs_evidence"] else []
    return res


def evidence_request(r: dict) -> list[str]:
    base = ["실제 구축 Reference(고객·업종·규모)", "적용 업무 수 / 처리 건수", "정확도·처리시간·비용 변화",
            "SLA / 가용률 실적", "운영 인력·조직", "Architecture 차별점", "PoC·검증 결과"]
    doms = {t["domain"] for t in r.get("tech_terms", [])}
    if "AX" in doms or "AI" in doms:
        base.insert(0, "AI가 처리하는 업무 범위와 사람 승인 지점")
    if doms & {"SI/Infra", "Infra", "Network"}:
        base.insert(0, "전환 대상 규모(서버·회선·시스템 수)와 무중단 전환 실적")
    if doms & {"MSP", "Cloud"}:
        base.insert(0, "운영 대상 규모, 장애 대응 시간 실적")
    return base[:8]


# ===================================================================== classify
def is_footer(u, slide_h):
    if FOOTER_NAME.search(u.get("shape_name") or ""):
        return True
    if FOOTER_TEXT.match(u["text"]):
        return True
    g = u.get("geom") or {}
    if slide_h and g.get("top", 0) > slide_h * 0.9 and len(u["text"]) < 40:
        return True
    if (u.get("style") or {}).get("size", 12) < 9:
        return True
    return False


def sentence_like(t: str) -> bool:
    t = t.strip()
    return bool(SENTENCE_END.search(t)) and len(t) >= 10 or len(t) >= 22


def classify_slide(units: list, page: int) -> dict:
    """한 장표(또는 PDF page)의 unit → title / governing / keys / body"""
    if not units:
        return {}
    sh = (units[0].get("geom") or {}).get("slide_h") or 0
    cand = [u for u in units if u["kind"] in ("title", "subtitle", "text") and not is_footer(u, sh)]
    tables = [u for u in units if u["kind"] == "table_cell"]
    notes = [u for u in units if u["kind"] == "notes"]
    out = {"page": page, "title": None, "governing": None, "keys": [], "body": [], "tables": tables,
           "notes": notes, "kind": "content"}
    if not cand:
        return out

    def top(u):
        return (u.get("geom") or {}).get("top", 0)

    def size(u):
        return (u.get("style") or {}).get("size") or 12

    titles = [u for u in cand if u["kind"] == "title"]
    if titles:
        title = titles[0]
    else:
        upper = [u for u in cand if not sh or top(u) < sh * 0.25]
        title = max(upper or cand, key=lambda u: (size(u), -top(u)))
    out["title"] = title
    rest = [u for u in cand if u is not title]
    # 경로 표시줄(Breadcrumb: "1. 대리점 시스템 구축 > 1) 영업 대리점 신설 (1/2)")은 메시지가 아니라 Section 정보
    navs = [u for u in rest if NAV_RE.search(u["text"]) and (not sh or top(u) < sh * 0.25)]
    if NAV_RE.search(title["text"]) and len(rest) > len(navs):
        navs.append(title)
        others = [u for u in rest if u not in navs]
        upper = [u for u in others if not sh or top(u) < sh * 0.3]
        title = max(upper or others, key=lambda u: (size(u), (u.get("style") or {}).get("bold") or False, -top(u)))
        out["title"] = title
    if navs:
        out["nav"] = navs[0]["text"]
    rest = [u for u in cand if u is not title and u not in navs]
    sizes = [size(u) for u in rest] or [12]
    body_size = statistics.median(sizes)

    # 표지 / 목차 / 간지
    if TOC_RE.match(title["text"].strip()):
        out["kind"] = "toc"
        return out
    if page == 1 and len(rest) <= 3 and all(u["kind"] in ("subtitle", "text") for u in rest):
        out["kind"] = "cover"
        out["body"] = rest
        return out
    if len(rest) <= 1 and not tables and (SECTION_NUM_RE.match(title["text"]) or len(title["text"]) <= 20):
        out["kind"] = "section"
        out["body"] = rest
        return out

    # Head message ① 상단 40% 이내의 서술형 완결 문장('~합니다.')을 글자 크기와 무관하게 우선
    head = None
    for u in sorted(rest, key=top):
        if ((not sh) or top(u) < sh * 0.4) and (u.get("style") or {}).get("level", 0) <= 1 \
                and DECL_END.search(u["text"]) and len(u["text"]) >= 15 \
                and (u.get("style") or {}).get("n_par_in_shape", 1) <= 2:
            head = u
            break
    # ② 제목 아래, 상단 40% 이내, 본문보다 크거나 굵은 문장
    for u in ([] if head else sorted(rest, key=top)):
        g_ok = (not sh) or top(u) < sh * 0.4
        lvl = (u.get("style") or {}).get("level", 0)
        if g_ok and lvl == 0 and sentence_like(u["text"]) and (size(u) > body_size or (u.get("style") or {}).get("bold") or size(u) >= 16):
            if (u.get("style") or {}).get("n_par_in_shape", 1) <= 2:
                head = u
                break
    if head:
        out["governing"] = head
    elif sentence_like(title["text"]):
        out["governing"] = title
    rest2 = [u for u in rest if u is not head]
    rest2.sort(key=lambda u: (top(u), (u.get("geom") or {}).get("left", 0), u["id"]))
    # Key 글자 크기 대역: 14pt 이상 후보 중 가장 많이 쓰인 크기(동률이면 큰 크기) ±1.5pt
    #  → 작은 글씨 본문/표/Evidence 박스와 큰 차트 라벨은 Key에서 제외
    cands = [round(size(u)) for u in rest2 if len(u["text"]) >= 8]
    big = [x for x in cands if x >= 14] or cands or [12]
    key_size = max(Counter(big).items(), key=lambda kv: (kv[1], kv[0]))[0]
    diagram = len(rest2) > 20  # 도식 위주 장표: 라벨은 Key가 아님 → 완결 문장만 Key
    for u in rest2:
        lvl = (u.get("style") or {}).get("level", 0)
        t = u["text"]
        if diagram:
            ok = lvl == 0 and 15 <= len(t) <= 120 and bool(DECL_END.search(t) or KEY_END.search(t)) and len(out["keys"]) < 6
        else:
            ok = lvl == 0 and abs(size(u) - key_size) <= 1.5 and 8 <= len(t) <= 120 and len(out["keys"]) < 6 and (sentence_like(t) or len(t) >= 12)
        if ok:
            out["keys"].append(u)
        else:
            out["body"].append(u)
    return out


def classify_doc(units: list) -> list[dict]:
    """DOCX / MD / TXT: heading=section, heading 다음 첫 문장=Governing, bullet=Key"""
    groups, cur = [], None
    sec = None
    for u in units:
        if u["kind"] == "heading":
            sec = u["text"]
            cur = {"page": None, "title": u, "governing": None, "keys": [], "body": [], "tables": [], "notes": [],
                   "kind": "content", "section": sec}
            groups.append(cur)
            continue
        if cur is None:
            cur = {"page": None, "title": None, "governing": None, "keys": [], "body": [], "tables": [], "notes": [],
                   "kind": "content", "section": None}
            groups.append(cur)
        if u["kind"] == "table_cell":
            cur["tables"].append(u)
        elif u["kind"] == "bullet":
            (cur["keys"] if len(u["text"]) >= 6 and len(cur["keys"]) < 8 else cur["body"]).append(u)
        elif u["source_type"] == "txt" and cur["title"] is None:
            # TXT: 줄마다 독립 메시지
            g = {"page": None, "title": None, "governing": u, "keys": [], "body": [], "tables": [], "notes": [],
                 "kind": "content", "section": None}
            groups.append(g)
        elif cur["governing"] is None and (u["kind"] == "quote" or sentence_like(u["text"])) and len(u["text"]) <= 140:
            cur["governing"] = u
        else:
            cur["body"].append(u)
    return [g for g in groups if g["governing"] or g["keys"]]


def classify_xlsx_storyline(units: list) -> list[dict]:
    """XLSX 스토리라인/메시지 시트: Header 이름으로 Governing/Key/Page/Section 컬럼 인식."""
    by_sheet_row = defaultdict(list)
    for u in units:
        if u["kind"] == "cell" and u["locator"].get("editable", True):
            by_sheet_row[(u["locator"]["sheet"], u["locator"]["row"])].append(u)
    groups = []
    for (sheet, row), cells in sorted(by_sheet_row.items(), key=lambda x: (x[0][0], x[0][1])):
        g = {"page": None, "title": None, "governing": None, "keys": [], "body": [], "tables": [], "notes": [],
             "kind": "content", "section": None, "sheet": sheet, "row": row}
        for u in cells:
            h = (u["style"] or {}).get("header") or ""
            if re.search(r"governing|헤드|head|거버닝|핵심\s*메시지", h, re.I):
                g["governing"] = u
            elif re.search(r"key|키\s*메시지|서브|sub", h, re.I):
                g["keys"].append(u)
            elif re.search(r"장표|slide|page|페이지|no", h, re.I):
                m = re.search(r"\d+", u["text"])
                g["page"] = int(m.group(0)) if m else None
            elif re.search(r"섹션|section|구분|목차|chapter", h, re.I):
                g["section"] = u["text"]
            elif re.search(r"제목|title|장표명", h, re.I):
                g["title"] = u
            elif not h and sentence_like(u["text"]) and len(u["text"]) >= 15:
                g["keys"].append(u)
            else:
                g["body"].append(u)
        if g["governing"] or g["keys"]:
            groups.append(g)
    return groups


# ===================================================================== context
def find_customer(texts: list[str]) -> str | None:
    """패턴 우선순위: 명시 필드(발주기관/고객사) > 귀중 > 표지 제목 첫 단어"""
    pats = [
        (r"(?:발주\s*기관|고객사|수요\s*기관|고객)\s*[:：]\s*([^\s,/|]+)", 1),
        (r"([가-힣A-Za-z0-9㈜()]{2,20})\s*(?:귀중|귀하)", 1),
        (r"^([가-힣A-Za-z0-9]{2,12}(?:㈜)?)\s+[^\n]{0,30}(?:제안서|제안요청서|사업|프로젝트|구축)$", 1),
    ]
    for p, gi in pats:
        for t in texts:
            m = re.search(p, t.strip())
            if m:
                cand = m.group(gi).replace("㈜", "").strip()
                if len(cand) >= 2 and not re.match(r"^(당사|본|제안|사업명)", cand):
                    return cand
    return None


def find_project(texts: list[str]) -> str | None:
    for t in texts:
        m = re.search(r"(사업명|프로젝트명|과업명)\s*[:：]\s*(.+)", t)
        if m:
            return m.group(2).strip()[:60]
    for t in texts:
        if re.search(r"(사업|프로젝트|구축|제안서)$", t.strip()) and 6 <= len(t) <= 60:
            return t.strip()
    return None


def build_context(content: dict, slides: list[dict]) -> dict:
    units = content["units"]
    all_text = "\n".join(u["text"] for u in units)
    own_text = "\n".join(u["text"] for u in units if u["source_role"] != "reference")  # 산업 판단은 고객·제안 자료만
    first_texts = []
    for s in content["sources"]:
        su = [u for u in units if u["source_file"] == s["file"]][:40]
        first_texts += [u["text"] for u in su]
    ind = Counter()
    for n, rx in INDUSTRY_RE:
        ind[n] = len(rx.findall(own_text))
    dom = Counter()
    for rx, d, _ in TECH_TERMS_RE:
        c = len(rx.findall(all_text))
        if c and d != "General IT":
            dom[d] += c
    techs = Counter()
    for rx, d, _ in TECH_TERMS_RE:
        for m in rx.finditer(all_text):
            techs[m.group(0)] += 1
    return {
        "customer": find_customer(first_texts),
        "project": find_project(first_texts),
        "industry": [n for n, c in ind.most_common(3) if c > 0],
        "domains": [d for d, _ in dom.most_common(6)],
        "top_technologies": [t for t, _ in techs.most_common(12)],
        "sources": [{k: s[k] for k in ("file", "type", "role", "units")} for s in content["sources"]],
        "slide_count": len([s for s in slides if s.get("source_role") == "proposal"]),
    }


def extract_requirements(content: dict) -> list[dict]:
    reqs = []
    for u in content["units"]:
        role = u["source_role"]
        if role == "requirements" and u["kind"] == "row":
            rec = u.get("record", {})
            rid = next((v for k, v in rec.items() if re.search(r"id|번호|no|코드", k, re.I)), None)
            desc = next((v for k, v in rec.items() if re.search(r"요구|내용|설명|desc|상세", k, re.I) and v != rid), None)
            name = next((v for k, v in rec.items() if re.search(r"명칭|요구사항\s*명|항목|name|제목", k, re.I)), None)
            text = " ".join(x for x in [name, desc] if x) or u["text"]
            reqs.append({"req_id": rid or u["location"], "text": text, "source_file": u["source_file"],
                         "source_type": u["source_type"], "source_location": u["location"], "page": u.get("page")})
        elif role == "rfp" and u["kind"] in ("text", "bullet", "table_cell", "cell") and REQ_RE.search(u["text"]) and len(u["text"]) >= 12:
            m = re.match(r"^([A-Z]{2,4}[-_ ]?\d{2,4})", u["text"])
            reqs.append({"req_id": m.group(1) if m else f"{u['source_file']} p{u.get('page')}", "text": u["text"],
                         "source_file": u["source_file"], "source_type": u["source_type"],
                         "source_location": u["location"], "page": u.get("page")})
    # 중복 제거
    seen, out = set(), []
    for r in reqs:
        k = re.sub(r"\s+", "", r["text"])[:80]
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def extract_evidence(content: dict) -> list[dict]:
    ev = []
    for u in content["units"]:
        role = u["source_role"]
        if role == "reference" and u["kind"] == "row":
            ev.append({"text": u["text"], "source_file": u["source_file"], "source_type": u["source_type"],
                       "source_location": u["location"], "page": u.get("page"), "kind": "reference"})
        elif role == "proposal" and u["kind"] in ("table_cell", "text", "bullet", "notes", "cell") and numbers(u["text"]) and EVIDENCE_HINT.search(u["text"]):
            ev.append({"text": u["text"], "source_file": u["source_file"], "source_type": u["source_type"],
                       "source_location": u["location"], "page": u.get("page"), "kind": "proposal_fact"})
        elif role in ("rfp", "requirements") and numbers(u["text"]) and u["kind"] in ("text", "cell", "row", "bullet"):
            ev.append({"text": u["text"], "source_file": u["source_file"], "source_type": u["source_type"],
                       "source_location": u["location"], "page": u.get("page"), "kind": "customer_fact"})
    return ev


# ===================================================================== main analyze
def slide_audience(text: str, role: str | None) -> str:
    best, bn = None, 0
    for n, rx in AUDIENCE_RE:
        c = len(rx.findall(text))
        if c > bn:
            best, bn = n, c
    if best:
        return best
    return {"Why": "CEO / 경영진", "What": "CEO / 경영진", "Value": "CEO / 경영진", "Why Us": "CIO / IT 담당 임원",
            "How": "IT / AX 담당자", "Evidence": "CIO / IT 담당 임원"}.get(role or "", "CIO / IT 담당 임원")


def slide_audience_ranked(title: str, body: str, role: str | None) -> str:
    """제목 → 역할(Why/What/Value는 경영진) → 본문 순으로 판단"""
    for n, rx in AUDIENCE_RE:
        if rx.search(title):
            return n
    if role in ("Why", "What", "Value"):
        return "CEO / 경영진"
    return slide_audience(body, role)


def gov_text_for_role(g) -> str:
    return g["governing"]["text"] if g.get("governing") else ""


def story_role(text: str) -> str | None:
    best, bn = None, 0
    for n, rx in STORY_ROLES_RE:
        c = len(rx.findall(text))
        if c > bn:
            best, bn = n, c
    return best


def analyze(content: dict, learning_log: Path | None = None) -> dict:
    units = content["units"]
    by_source = defaultdict(list)
    for u in units:
        by_source[u["source_file"]].append(u)

    groups = []  # 장표(그룹) 목록
    for s in content["sources"]:
        su = by_source[s["file"]]
        if s["role"] != "proposal":
            continue
        if s["type"] in ("pptx", "pdf"):
            pages = defaultdict(list)
            for u in su:
                pages[u["page"]].append(u)
            for p in sorted(pages):
                g = classify_slide(pages[p], p)
                if g:
                    g.update({"source_file": s["file"], "source_type": s["type"], "source_role": s["role"]})
                    groups.append(g)
        elif s["type"] == "xlsx":
            for g in classify_xlsx_storyline(su):
                g.update({"source_file": s["file"], "source_type": s["type"], "source_role": s["role"]})
                groups.append(g)
        else:
            for g in classify_doc(su):
                g.update({"source_file": s["file"], "source_type": s["type"], "source_role": s["role"]})
                groups.append(g)

    # Section 이름 전파 (Breadcrumb가 있으면 첫 단계를 Section으로)
    cur_sec = None
    for g in groups:
        if g.get("nav"):
            g["section"] = re.split(r"\s>\s", g["nav"])[0].strip()
        if g["kind"] == "section" and g["title"]:
            cur_sec = g["title"]["text"]
        if not g.get("section"):
            g["section"] = cur_sec

    requirements = extract_requirements(content)
    skip_pages = {(g["source_file"], g.get("page")) for g in groups if g["kind"] in ("toc", "section", "cover")}
    evidence = [e for e in extract_evidence(content) if (e["source_file"], e.get("page")) not in skip_pages or e["kind"] != "proposal_fact"]
    req_tok = [tokens(r["text"]) for r in requirements]
    ev_tok = [tokens(e["text"]) for e in evidence]
    ctx_info = build_context(content, groups)
    corpus_nums = sorted({n for u in units for n in numbers(u["text"])})

    messages, slides_out = [], []
    seq = 0
    for g in groups:
        if g["kind"] in ("toc",):
            continue
        title_t = g["title"]["text"] if g.get("title") else ""
        all_t = " ".join(u["text"] for u in [g.get("title"), g.get("governing")] + g["keys"] + g["body"] + g["tables"] if u)
        role = story_role(title_t) or story_role(gov_text_for_role(g)) or story_role(g.get("section") or "") or story_role(all_t)
        aud = slide_audience_ranked(title_t, all_t[:400], role)
        slide_ev = [u["text"] for u in g["body"] + g["tables"] + g["notes"]]
        slide_ev_loc = [f"{u['source_file']} / {u['location']}" for u in g["body"] + g["tables"] if numbers(u["text"]) or EVIDENCE_HINT.search(u["text"])]
        gov_text = g["governing"]["text"] if g.get("governing") else None
        slide_rec = {"source_file": g["source_file"], "page": g.get("page"), "kind": g["kind"], "title": title_t,
                     "section": g.get("section"), "story_role": role, "audience": aud,
                     "governing_id": g["governing"]["id"] if g.get("governing") else None,
                     "key_ids": [u["id"] for u in g["keys"]], "has_governing": bool(g.get("governing"))}
        slides_out.append(slide_rec)
        if g["kind"] in ("cover", "section"):
            continue
        targets = ([("Governing", g["governing"])] if g.get("governing") else []) + [("Key", u) for u in g["keys"]]
        for mtype, u in targets:
            seq += 1
            mt = tokens(u["text"] + " " + (title_t if mtype == "Governing" else ""))
            # Requirement 연결
            rl = sorted(((similarity(mt, rt), i) for i, rt in enumerate(req_tok)), reverse=True)[:3]
            linked_reqs = [dict(requirements[i], score=round(s, 2)) for s, i in rl if s >= 0.22]
            # Evidence 연결 (같은 장표 우선, 이후 Reference)
            el = sorted(((similarity(mt, et), i) for i, et in enumerate(ev_tok)), reverse=True)[:3]
            linked_ev = [dict(evidence[i], score=round(s, 2)) for s, i in el
                         if s >= 0.35 and not (evidence[i]["source_file"] == u["source_file"] and evidence[i].get("page") == g.get("page"))
                         and not (mtype == "Key" and evidence[i]["kind"] == "proposal_fact")]
            a = assess(u["text"], {"message_type": mtype, "slide_evidence": slide_ev if mtype == "Governing" else [],
                                   "linked_evidence": linked_ev, "audience": aud,
                                   "governing": gov_text if mtype == "Key" else None})
            # 근거 없는 주장 → Reference 자료에서 '후보'만 제시 (확정 Evidence 아님, 사람 확인 필요)
            cand = []
            if a["unsupported_claim"] or a["needs_evidence"]:
                st = tokens(all_t)
                refs = [(similarity(st, ev_tok[i]), i) for i, e in enumerate(evidence) if e["kind"] == "reference"]
                cand = [dict(evidence[i], score=round(sc, 2)) for sc, i in sorted(refs, reverse=True)[:2]]
            messages.append({
                "seq": seq,
                "id": u["id"],
                "source_type": u["source_type"],
                "source_file": u["source_file"],
                "source_location": u["location"],
                "page": g.get("page") or u.get("page"),
                "section": g.get("section") or "",
                "slide_title": title_t,
                "audience": aud,
                "story_role": role,
                "message_type": mtype,
                "original": u["text"],
                "locator": u["locator"],
                "style": u.get("style", {}),
                "geom": u.get("geom", {}),
                "slide_evidence": [e for e in slide_ev if numbers(e) or EVIDENCE_HINT.search(e)][:6],
                "slide_evidence_loc": slide_ev_loc[:6],
                "linked_requirements": linked_reqs,
                "linked_evidence": linked_ev,
                "evidence_candidates": cand,
                "assessment": a,
            })

    # Slide-level 문제: Governing 없음, Key가 모두 Governing 반복
    slide_issues = []
    for s in slides_out:
        if s["kind"] == "content" and not s["has_governing"]:
            slide_issues.append({"source_file": s["source_file"], "page": s["page"], "title": s["title"],
                                 "issue": "Governing Message 없음 — 장표 제목만 있음"})
    # Requirement coverage
    req_cov = []
    for i, r in enumerate(requirements):
        best = None
        for m in messages:
            for lr in m["linked_requirements"]:
                if lr["text"] == r["text"] and (best is None or lr["score"] > best[0]):
                    best = (lr["score"], m)
        req_cov.append(dict(r, covered_by=(f"{best[1]['source_file']} / {best[1]['source_location']}" if best else None),
                            covered_message=(best[1]["original"] if best else None),
                            coverage=("COVERED" if best and best[0] >= 0.3 else "WEAK" if best else "GAP")))

    # Story Flow
    roles_present = [s["story_role"] for s in slides_out if s["kind"] == "content" and s["story_role"]]
    missing_roles = [r for r, _ in STORY_ROLES_RE if r not in roles_present]
    gov_msgs = [m for m in messages if m["message_type"] == "Governing"]
    key_msgs = [m for m in messages if m["message_type"] == "Key"]
    content_slides = [s for s in slides_out if s["kind"] == "content"]
    story_score = 5.0
    if content_slides:
        story_score -= (1 - len([s for s in content_slides if s["has_governing"]]) / len(content_slides)) * 2.5
    story_score -= min(2, len(missing_roles) * 0.4)
    if requirements:
        gap_ratio = len([r for r in req_cov if r["coverage"] == "GAP"]) / len(requirements)
        story_score -= gap_ratio * 1.5

    def avg(lst, key):
        v = [m["assessment"]["scores"][key] for m in lst]
        return round(sum(v) / len(v), 2) if v else None

    def avg_overall(lst):
        v = [m["assessment"]["overall"] for m in lst]
        return round(sum(v) / len(v), 2) if v else None

    dims = {
        "Customer Relevance": avg(messages, "customer_relevance"),
        "Governing Message": avg_overall(gov_msgs),
        "Key Message": avg_overall(key_msgs),
        "Tech-to-Value": avg(messages, "tech_to_value"),
        "Audience Fit": avg(messages, "audience_fit"),
        "Specificity": avg(messages, "specificity"),
        "Differentiation": avg(messages, "differentiation"),
        "Evidence": avg(messages, "evidence"),
        "Story Flow": round(max(1, story_score), 2),
        "AI Naturalness": avg(messages, "naturalness"),
        "One Message": avg(messages, "one_message"),
    }
    vals = [v for v in dims.values() if v is not None]
    weights = {"Governing Message": 2, "Key Message": 1.5, "Customer Relevance": 1.5, "Tech-to-Value": 1.5, "Evidence": 1.2}
    tw = sum(weights.get(k, 1) for k, v in dims.items() if v is not None)
    total = sum(v * weights.get(k, 1) for k, v in dims.items() if v is not None) / tw if vals else 0
    status_count = Counter(m["assessment"]["status"] for m in messages)

    # 가장 중요한 문제 (빈도·중요도)
    issue_counter = Counter()
    for m in messages:
        a = m["assessment"]
        for c in a["categories"]:
            if c != "Keep":
                issue_counter[c] += 2 if m["message_type"] == "Governing" else 1
        if a["unsupported_claim"]:
            issue_counter["Evidence 부족"] += 2
    if slide_issues:
        issue_counter["Governing Message 없음"] += len(slide_issues) * 2
    if missing_roles:
        issue_counter["Story 단계 누락: " + ", ".join(missing_roles)] += 1
    gaps = [r for r in req_cov if r["coverage"] == "GAP"]
    if gaps:
        issue_counter[f"메시지로 응답하지 않은 고객 요구사항 {len(gaps)}건"] += len(gaps) * 2

    learned = load_learning(learning_log, ctx_info.get("domains", []))

    return {
        "schema_version": SCHEMA_VERSION,
        "context": ctx_info,
        "scores": {"Proposal Message Score": round(total * 20, 1), "dimensions": dims},
        "status_count": {k: status_count.get(k, 0) for k in ("GREEN", "YELLOW", "RED", "ESCALATE")},
        "top_issues": [k for k, _ in issue_counter.most_common(5)],
        "slides": slides_out,
        "slide_issues": slide_issues,
        "story": {"roles_in_order": [(s["page"], s["story_role"]) for s in content_slides], "missing_roles": missing_roles},
        "messages": messages,
        "requirements": req_cov,
        "evidence": evidence,
        "corpus_numbers": corpus_nums,
        "learned_examples": learned,
    }


def load_learning(path: Path | None, domains: list[str], limit: int = 12) -> list[dict]:
    if not path or not Path(path).exists():
        return []
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    def rank(r):
        s = 0
        if r.get("decision") == "EDIT":
            s += 3
        if r.get("decision") == "ACCEPT":
            s += 1
        if set(r.get("domain", []) if isinstance(r.get("domain"), list) else [r.get("domain")]) & set(domains):
            s += 2
        return -s
    rows.sort(key=rank)
    return rows[:limit]


# ===================================================================== outputs
def recommendations_template(an: dict) -> dict:
    items = {}
    for m in an["messages"]:
        a = m["assessment"]
        items[m["id"]] = {
            "seq": m["seq"],
            "message_type": m["message_type"],
            "page": m["page"],
            "original": m["original"],
            "engine_status": a["status"],
            "engine_problems": a["problems"],
            # ↓ Claude가 채우는 칸 -------------------------------------------
            "status": a["status"],         # 최종 판정 (엔진 판정을 근거 있게 바꿀 수 있음)
            "problem": "",                 # 고객 관점의 핵심 문제 한 줄
            "customer_value": "",          # 이 메시지로 고객이 얻는 것 (원문/근거 기반)
            "evidence": "",                # 사용한 Evidence와 출처 (없으면 '없음')
            "ai_recommended": "",          # GREEN이면 비워두거나 원문 유지
            "alt_a": "",
            "alt_b": "",
            "reason": "",
            "category": a["categories"][0],
        }
    return {"schema_version": SCHEMA_VERSION, "project": an["context"].get("project"),
            "summary": {"diagnosis": "", "top_issues": an["top_issues"]}, "items": items}


def write_brief(an: dict, path: Path):
    c = an["context"]
    L = []
    L.append(f"# 키 메시지 분석 Brief\n")
    L.append(f"- 고객: {c.get('customer') or '(미확인 — 원문에서 확인 필요)'}")
    L.append(f"- 사업: {c.get('project') or '(미확인)'}")
    L.append(f"- 산업: {', '.join(c.get('industry') or []) or '(미확인)'} / 도메인: {', '.join(c.get('domains') or [])}")
    L.append(f"- 주요 기술어: {', '.join(c.get('top_technologies') or [])}")
    L.append("- Sources: " + "; ".join(f"{s['file']}({s['type']}, {s['role']}, {s['units']})" for s in c["sources"]))
    L.append(f"\n## 점수 (엔진 1차) — Proposal Message Score {an['scores']['Proposal Message Score']}")
    for k, v in an["scores"]["dimensions"].items():
        L.append(f"- {k}: {v}")
    L.append(f"\n상태: {an['status_count']}")
    L.append("\n## 주요 문제\n" + "\n".join(f"- {x}" for x in an["top_issues"]))
    if an["slide_issues"]:
        L.append("\n## 장표 문제\n" + "\n".join(f"- {x['source_file']} p{x['page']} '{x['title']}': {x['issue']}" for x in an["slide_issues"]))
    L.append(f"\n## Story: {an['story']['roles_in_order']} / 누락: {an['story']['missing_roles']}")
    if an["requirements"]:
        L.append("\n## 고객 요구사항 ↔ 메시지")
        for r in an["requirements"]:
            L.append(f"- [{r['coverage']}] {r['req_id']} ({r['source_file']} / {r['source_location']}): {r['text'][:90]}"
                     + (f"\n    → {r['covered_by']}: {r['covered_message'][:60]}" if r.get("covered_by") else ""))
    L.append("\n## 메시지별 진단")
    for m in an["messages"]:
        a = m["assessment"]
        L.append(f"\n### #{m['seq']} [{a['status']}] {m['message_type']} — {m['source_file']} / {m['source_location']}")
        L.append(f"- 장표: {m['slide_title']} | Section: {m['section']} | Audience: {m['audience']} | Story: {m['story_role']}")
        L.append(f"- 원문: {m['original']}")
        st = m.get("style") or {}
        if st.get("wrap") == "none":
            from km_common import text_units
            lim = max((m.get("geom") or {}).get("width", 0) / 12700, text_units(m["original"]) * (st.get("size") or 12))
            L.append(f"- ⚠ 한 줄 박스(줄바꿈 없음): 수정문은 약 {int(lim / (st.get('size') or 12))}자 이내")
        if a["problems"]:
            L.append("- 문제: " + " / ".join(a["problems"]))
        if a["tech_terms"]:
            L.append("- 기술어 → Capability 힌트: " + "; ".join(f"{t['term']} → {t['capability_hint']}" for t in a["tech_terms"]))
        L.append(f"- 5Q: " + ", ".join(f"{k}={'O' if v else 'X'}" for k, v in a["five_q"].items()) + f" | Swap: {a['competitor_swap']}")
        if m["slide_evidence"]:
            L.append("- 장표 내 Evidence: " + " / ".join(e[:70] for e in m["slide_evidence"][:4]))
        if m["linked_evidence"]:
            L.append("- 연결 Evidence: " + " / ".join(f"{e['source_file']} {e['source_location']}: {e['text'][:70]}" for e in m["linked_evidence"]))
        if m["linked_requirements"]:
            L.append("- 연결 요구사항: " + " / ".join(f"{r['req_id']}: {r['text'][:60]}" for r in m["linked_requirements"]))
        if m.get("evidence_candidates"):
            L.append("- Evidence 후보(사실 확인 전 사용 금지): " + " / ".join(f"{e['source_file']} {e['source_location']}: {e['text'][:80]}" for e in m["evidence_candidates"]))
        if a["evidence_request"]:
            L.append("- 추가 Evidence 요청 후보: " + ", ".join(a["evidence_request"]))
    if an["learned_examples"]:
        L.append("\n## 과거 PM 선택 예시 (Learning Loop)")
        for e in an["learned_examples"]:
            L.append(f"- [{e.get('decision')}/{e.get('category')}] {e.get('original')}  →  {e.get('final')}")
    path.write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="키 메시지: 진단 엔진")
    ap.add_argument("content", nargs="?", help="content.json")
    ap.add_argument("-o", "--outdir", default=".")
    ap.add_argument("--text", action="append", help="단일 메시지 빠른 진단 (여러 번 가능)")
    ap.add_argument("--type", default="Governing", choices=["Governing", "Key"])
    ap.add_argument("--learning-log", default=str(DEFAULT_LEARNING_LOG))
    a = ap.parse_args()
    if a.text:
        out = [assess(t, {"message_type": a.type}) for t in a.text]
        print(json.dumps([{k: r[k] for k in ("text", "status", "problems", "categories", "ai_severity", "competitor_swap",
                                            "unsupported_claim", "tech_terms", "five_q", "evidence_request", "overall")}
                          for r in out], ensure_ascii=False, indent=2))
        return
    if not a.content:
        ap.error("content.json 또는 --text 가 필요합니다")
    content = load_json(a.content)
    an = analyze(content, Path(a.learning_log) if a.learning_log else None)
    od = Path(a.outdir)
    od.mkdir(parents=True, exist_ok=True)
    dump_json(an, od / "analysis.json")
    write_brief(an, od / "analysis_brief.md")
    rec_path = od / "recommendations.json"
    if rec_path.exists():
        print(f"[KEEP] 기존 {rec_path} 유지 (덮어쓰지 않음). 새 템플릿은 recommendations.template.json")
        dump_json(recommendations_template(an), od / "recommendations.template.json")
    else:
        dump_json(recommendations_template(an), rec_path)
    print(f"[OK] messages={len(an['messages'])} status={an['status_count']} score={an['scores']['Proposal Message Score']}")
    print(f"[OK] {od/'analysis.json'}\n[OK] {od/'analysis_brief.md'}\n[OK] {rec_path} (Claude가 채울 템플릿)")


if __name__ == "__main__":
    main()
