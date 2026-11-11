---
name: key-message
description: 「키 메시지」 — 대기업 B2B/B2G IT·AX 제안서(IT, AX, 생성형 AI, AI Agent, Cloud/MSP, Data, SI, Infra, Network, Data Center, Security, AICC, 업무자동화, DX)의 Governing Message와 Key Message를 진단·개선하는 Proposal Message QA Skill. PPTX·PDF·XLSX·DOCX·MD·TXT(여러 파일 동시, RFP+요구사항+제안서+Reference 통합)를 읽어 고객·기술·가치를 분석하고, 사람이 승인할 Review Excel을 만든 뒤, 승인된 메시지만 원본 PPTX/XLSX에 반영한다. "키 메시지 검토", "키 메시지 REVIEW", "거버닝 메시지", "헤드 메시지 다듬어줘", "제안서 메시지 QA", "승인한 키 메시지 Excel 기준으로 원본 PPT 수정", "키 메시지 AUTO" 요청에 사용. 단순 맞춤법 교정·Humanizer 요청에는 쓰지 않는다.
---

# 키 메시지 (key-message)

> 대기업 IT·AX 제안서의 **기술 설명을 고객의 의사결정 메시지로 바꾸고**, **사람이 승인한 결과만** 원본에 반영한다.

항상 두 질문을 먼저 던진다.
1. 이 장표에서 고객이 기억해야 할 **한 문장**은 무엇인가?
2. 이 기술 때문에 고객의 **사업·업무·운영이 실제로 무엇이 달라지는가?**

판단 우선순위: Governing → Key → Customer Relevance → One Message → Tech-to-Value → **Fact/Number Guard** → Audience → Story → Specificity → Differentiation → Evidence → AI 문체 → 자연스러운 한국어. Humanizer보다 메시지 품질이 우선이다.

## 0. 모드 결정

| 요청 | Mode |
|---|---|
| "키 메시지 검토/REVIEW 해줘", 지시 없음 | **REVIEW (기본값)** |
| "승인한 키 메시지 Excel 기준으로 원본 수정해줘" | **APPLY** |
| "키 메시지 AUTO", "빠르게 수정본까지" | **AUTO** (내부 초안용 — 중요한 대기업 제안서는 REVIEW → 승인 → APPLY 권장을 한 줄로 알린다) |

스크립트 경로: `SKILL_DIR=.claude/skills/key-message` (사용자 전역 설치 시 `~/.claude/skills/key-message`). 작업 산출물은 입력 파일 옆 `KeyMessage_work/` 폴더에 둔다. **원본 파일은 절대 덮어쓰지 않는다.**
필요 패키지: `python-pptx openpyxl pdfplumber python-docx lxml` (없으면 `pip install`).

## 1. REVIEW (기본)

```bash
W=<입력폴더>/KeyMessage_work
python $SKILL_DIR/scripts/extract_content.py <파일들...> -o $W/content.json      # 여러 파일 동시 가능
python $SKILL_DIR/scripts/analyze_messages.py $W/content.json -o $W              # 진단 + Brief + 재작성 템플릿
```

1. `extract_content.py` 출력에서 각 파일의 **role**(proposal / rfp / requirements / reference)을 확인한다. 틀리면 `--role 파일명=역할`로 다시 실행한다. 수정 대상은 proposal뿐이고, 나머지는 Context·Evidence다.
2. `$W/analysis_brief.md`를 **처음부터 끝까지 읽는다.** 개별 문장을 고치기 전에 Customer / Business / Technology / Competition / Evidence / Story를 머릿속에 정리한다 → `references/multi-source-rules.md`.
   엔진 판정은 1차 신호일 뿐이다. 근거를 갖고 Status를 바꿀 수 있다.
3. `$W/recommendations.json`을 채운다 (Unit ID 키 `items`, 또는 원문 키 `by_original`). 메시지마다:
   - `status` GREEN / YELLOW / RED / ESCALATE → `references/scoring-rubric.md`
   - `problem`, `customer_value`, `evidence`(출처 포함), `ai_recommended`, `alt_a`, `alt_b`, `reason`, `category`
   - 규칙: `governing-message.md`, `key-message.md`, `tech-to-value.md`, `it-ax-message-rules.md`, `audience-rules.md`, `business-writing-rules.md`, `ai-writing-patterns.md`, 예시는 `examples.md`
   - Brief 끝의 **과거 PM 선택 예시(Learning Loop)** 가 있으면 문체·수준의 1순위 기준으로 삼는다.
   - `summary.diagnosis`(제안서 핵심 진단 3~5문장), `summary.top_issues`(3~5개)도 쓴다.
4. 쓰기 전에 매번 확인한다:
   - **GREEN은 고치지 않는다.** `ai_recommended`를 비워 둔다.
   - **ESCALATE는 원문 유지.** `ai_recommended`를 비우고 `reason`에 필요한 Evidence를 적는다. 근거 후보(`Evidence 후보`)가 있으면 `alt_a`에 "확인 시 사용안"으로만 제시한다.
   - **숫자·고유명사·기술명·고객 요구사항은 원문 그대로 쓴다.** 원문이나 자료에 없는 숫자·효과·경쟁우위·Reference를 만들지 않는다.
   - Governing과 Key가 같은 말을 반복하지 않는다 (Key = Why / How / Evidence).
   - Five Question Test와 Competitor Swap Test, Human Quality Test를 통과하는지 확인한다.
5. Excel 생성 및 검증:
```bash
python $SKILL_DIR/scripts/create_review_excel.py $W/analysis.json $W/recommendations.json -o <입력폴더> --project <프로젝트명>
python $SKILL_DIR/scripts/validate_output.py review <입력폴더>/<프로젝트명>_KeyMessage_Review.xlsx
```
   `QA Check`에 **Fact Guard ERROR** 또는 **재진단 RED**가 나오면 해당 recommendation을 고치고 다시 생성한다.
6. 사용자에게 보고한다: Proposal Message Score, GREEN/YELLOW/RED/ESCALATE 수, 핵심 진단, 가장 중요한 문제 3~5개, ESCALATE 항목별로 필요한 Evidence, Excel 경로. 마지막에 "Message Review 시트에서 Decision을 고른 뒤 APPLY를 요청하라"고 안내한다.

## 2. APPLY (사람 승인 후)

```bash
python $SKILL_DIR/scripts/apply_approved_messages.py <원본.pptx|xlsx> <승인된_Review.xlsx>
python $SKILL_DIR/scripts/validate_output.py apply <원본> <원본명>_KeyMessage_v2.<ext>
```
- Decision: ACCEPT=AI Recommended, EDIT=Human Final(비면 Warning, 미반영), KEEP=원문, ESCALATE=원문, 빈칸=원문+Warning.
- 원본의 현재 문장이 Review의 Original과 다르면(Stale) 반영하지 않는다. ACCEPT안의 Fact Guard ERROR는 반영하지 않는다.
- PPTX는 첫 Run 서식(폰트·크기·색·굵기)과 Shape·Layout·차트·이미지·표를 그대로 두고 텍스트만 바꾼다. Overflow가 나면 폰트를 최대 10%(2pt 이내)까지만 줄이고, 그래도 넘치면 Warning을 남긴다 → 해당 문장 축약안을 사용자에게 제안.
- XLSX는 XML 단위로 해당 셀만 바꾼다 (수식·서식·차트·다른 시트 보존).
- PDF Review 결과는 **원본 PPTX**에 반영한다 (같은 장표에서 원문 텍스트로 매칭). PDF 직접 수정은 하지 않는다.
- 여러 파일을 통합 Review한 경우 원본 파일명과 같은 Source File 행만 반영된다.
- 결과 보고: 반영/유지 건수, Warning(Overflow·Stale·EDIT 빈칸·Fact) 목록, 수정본 경로, validate 결과.
- Decision 결과는 Learning Loop(`~/.claude/key-message/learning/decisions.jsonl`)에 쌓여 다음 분석 Brief에 예시로 나온다.

## 3. AUTO

REVIEW 1~5단계를 그대로 수행한 뒤:
```bash
python $SKILL_DIR/scripts/apply_approved_messages.py <원본> <Review.xlsx> --auto
```
빈 Decision → RED/YELLOW이면서 AI안이 있고 Fact Guard ERROR가 없으면 ACCEPT, 나머지(GREEN·ESCALATE)는 KEEP. Review Excel도 기록으로 함께 전달한다.

## 4. 절대 금지
없는 숫자·효과·고객 요구사항·경쟁우위·Reference 생성 / 모든 문장 강제 수정 / 기술명 나열 / 의미 없는 컨설팅 용어·영어 남발 / 광고 카피식 과장 / 원문 핵심 의미 변경 / AI 탐지 회피 자체를 목표로 한 수정 / Evidence 없이 메시지 강화 / 원본 덮어쓰기 / Source를 확인할 수 없는 사실의 확정적 사용.

## 5. 파일 지도
- `scripts/extract_content.py` File Parser + Content Normalizer (PPTX·PDF·XLSX·DOCX·MD·TXT → content.json)
- `scripts/analyze_messages.py` Proposal Context · Tech-to-Value · Governing/Key · AI Writing QA · Evidence Guard 진단 (`--text "문장"`으로 단일 문장 빠른 진단)
- `scripts/create_review_excel.py` Review Excel (Human Approval Interface) + Fact Guard/재진단 QA
- `scripts/apply_approved_messages.py` Apply Engine (APPLY/AUTO, Learning Loop 기록)
- `scripts/validate_output.py` Review Excel / 수정본 구조 검증
- `scripts/km_common.py` 사전(상투어·기술어·가치어·Audience·Story)과 Fact Guard
- `references/` 상세 규칙 · `tests/run_tests.py` 통합 테스트
