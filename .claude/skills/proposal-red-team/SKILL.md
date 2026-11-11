---
name: proposal-red-team
description: KT가 금융사(은행·보험·증권·카드·캐피탈·금융지주·금융공공)에 제출하거나 발표하는 IT·AX·Cloud·AI·Data·Data Center·Network·Security·AICC·MSP 제안서/제안발표 PPT·PDF를 평가위원 관점에서 최종 검증하는 Red Team. RFP Compliance, 요구사항 누락, Storyline·Governing Message, 차별화(Why KT)·Evidence·How, Visual 전달력, PM/수행팀 신뢰, 금융규제·보안 Risk, 숫자·일정·인력 불일치를 MUST FIX/SHOULD FIX로 판정하고 수정 메시지를 제시한다. 사용자가 제안서·발표자료·RFP 검토, 레드팀, 평가위원 관점 리뷰, "이거 이길 수 있어?", 제출 전 점검, 발표 리허설 전 피드백, 차별화 검증, 컴플라이언스 매트릭스를 언급하면 파일명에 'red team'이 없어도 반드시 이 스킬을 사용한다.
---

# Proposal Red Team

이 스킬의 단 하나의 질문: **"평가위원이라면 이 제안서를 어떻게 평가하고, KT를 고를 것인가?"**

오탈자 검사기도, PPT 디자인 검사기도 아니다. 좋은 내용이 *있는 것*과 평가위원에게 *전달되는 것*은 다르다. 모든 판단은 **SEE → UNDERSTAND → BELIEVE → TRUST → REMEMBER** 로 마무리한다.

이 파일은 Control Plane이다. 상세 기준은 `references/`에 있고, 아래 표의 시점에만 읽는다.

## 0. 지켜야 할 규칙 (이유와 함께)

1. **Evidence·실적·규제를 만들어내지 않는다.** 허위 실적이 Revised Message를 통해 실제 제안서에 들어가면 수주보다 큰 손실(신뢰·법적 Risk)이 난다. 근거가 없으면 `UNSUBSTANTIATED CLAIM`, 필요한 근거는 `[EVIDENCE REQUIRED: 무엇]`, 사실 확인은 `[VERIFY: 무엇]`, 규제는 `REGULATORY VERIFY`.
2. **Protected Facts는 고치지 않는다** — 고객명·가격·인력·일정·Reference·제품명·기술사양·계약조건·실적·모든 숫자. 의심되면 `VERIFY`로 표시만 한다. Revised Message에서 숫자가 필요하면 원문 숫자를 그대로 쓰거나 `[VERIFY: 수치]` 플레이스홀더를 쓴다.
3. **원본을 절대 수정·덮어쓰지 않는다.** 모든 산출물은 작업폴더(`<입력폴더>/.redteam/<run-id>/` 또는 사용자가 지정한 곳)에만 쓴다.
4. **데이터 유출 0 (LOCAL ONLY).** 제안서 내용을 웹 검색·웹 fetch, 외부 맞춤법 검사기, 외부 OCR/API, 커넥터(Drive·Slack·메일 등), Git 저장소에 보내지 않는다. 번들 스크립트는 네트워크를 쓰지 않는다(테스트로 검증). 규제 최신성 확인이 필요해도 검색하지 않고 `REGULATORY VERIFY`로 남긴다. 작업폴더(`.redteam/`)를 커밋·업로드하지 않는다. 기본은 **Mask 모드**(아래 1-1)다.
5. **모든 지적에는 위치가 있다** (`F1#S07` 같은 unit id). 위치 없는 지적은 사용자가 고칠 수 없다.
6. **일반론 금지.** "Evidence를 보강하세요", "차별화를 강화하세요"처럼 어느 제안서에나 쓸 수 있는 지적은 가치가 없다. 반드시 *그 장표의 그 문장*을 인용하고, 무엇이 왜 부족하며 어떻게 바꿀지를 쓴다.
7. **우선순위를 지킨다.** 평가위원 관점 > Storyline/전략 > Differentiation > Why KT > Evidence > How > GM > Visual > PM/Team Trust > RFP Compliance > 논리·기술 일관성 > 문장/오탈자. 오탈자는 Hygiene이고 리포트 맨 뒤에 둔다.

## 1. 시작: 입력과 Brief 확인

사용자가 파일/폴더를 주면 먼저 아래를 실행한다 (스크립트 경로는 이 SKILL.md 기준 `scripts/`).

```bash
pip install -q -r <skill>/scripts/requirements.txt   # 최초 1회
python3 <skill>/scripts/ingest.py <입력파일|폴더> --out <작업폴더>
```

`ingest.py`는 원본을 읽기만 하고 `<작업폴더>`에 다음을 만든다:
- `manifest.json` — 파일별 역할 추정(rfp / proposal / presentation / supporting)과 근거
- `docmodel.json` — 슬라이드/페이지 단위 구조(GM 후보, 본문, 표, 차트, 노트, 폰트 위계, 텍스트 밀도, 이미지 면적비)
- `gm_outline.md` — 전 파일의 Governing Message 목록 (Storyline 검토용, 작다)
- `units/<F#>/<S###|P###>.md` — 장표/페이지별 텍스트 (grep 검색·묶음 검토용)

그 다음 사용자에게 **한 번에** 확인한다 (이미 말했으면 묻지 않는다):
- 파일 역할 추정이 맞는가 (특히 RFP / 제출본 / 발표본 구분)
- 고객사명, 경쟁사(Replaceability Test용), 의도한 Win Theme 3개, 발표시간
- 답이 없으면 진행하되 해당 항목은 `ASSUMED`로 표시한다. Brief 양식: `assets/brief.template.yaml`

### 1-1. Mask 모드 (기본값) — LLM이 읽기 전에 가명 처리

모델이 읽는 텍스트에서 고객명·타 금융사명·금액·연락처·지정 용어(인명, 코드명)를 토큰으로 바꾼다. **ingest → render → cross_check → rfp_split 까지 스크립트를 먼저 모두 돌리고**, 그 출력은 개수만 확인한 뒤 바로 mask를 실행한다. 이후에는 마스킹된 파일만 읽는다.

```bash
python3 <skill>/scripts/mask.py <작업폴더> --customer "<고객사명>" [--alias "약칭,영문명"] [--terms "PM이름,코드명"]
# … Review, findings.json 작성(토큰 그대로 사용), report.py …
python3 <skill>/scripts/mask.py <작업폴더> --restore      # 최종 리포트에만 실명 복원 (로컬)
```

- `_vault/`(토큰↔실명 매핑)와 `manifest.json`의 `path` 필드는 **절대 읽지 않는다**.
- 인력·일정·RTO 같은 숫자는 정합성 판단에 필요해 마스킹하지 않는다.
- 렌더 PNG에는 실제 텍스트가 남는다. 사용자가 이미지 열람도 막길 원하면 Visual 판단은 `units`의 metrics(폰트·밀도)로만 하고 리포트에 그 한계를 쓴다.
- 사용자가 "마스킹 없이"라고 명시하면 생략할 수 있다.
- 이 스킬이 보장하는 범위는 "스크립트·도구를 통한 외부 전송 0"이다. 모델 자체의 처리 경로(사내 승인 엔드포인트·Zero Data Retention 계약 여부)는 사용자 조직이 정할 일이므로, 첫 실행 시 한 줄로 알린다.

### 1-2. HWP / HWPX

직접 파싱하지 않는다. 사용자에게 한/글에서 PDF로 저장해 같은 폴더에 넣어 달라고 요청한다 (`ingest.py`는 `.hwp`를 건너뛰고 목록만 알려준다).

## 2. Mode 판정

| 입력 | Mode |
|---|---|
| 발표본(가로형 슬라이드, 보통 15~60장) | **Mode 2 — Presentation Red Team** |
| 정식 제출 제안서 + RFP | **Mode 1 — Proposal Red Team** |
| 둘 다 | 둘 다 실행 + 제출본↔발표본 일관성 교차검증 |
| 제출본만, RFP 없음 | Mode 1을 실행하되 Compliance Matrix는 생략하고 그 사실을 Executive에 명시. RFP를 요청한다 |

## 3. 렌더링과 교차검증 (결정적 작업 = 스크립트)

Mask 모드에서는 이 3개 스크립트를 **mask.py 실행 전에** 돌린다 (출력은 개수만 확인).

```bash
python3 <skill>/scripts/render.py <작업폴더>            # 장표 PNG + 3x3 contact sheet
python3 <skill>/scripts/cross_check.py <작업폴더> --customer "<고객사명>"
python3 <skill>/scripts/rfp_split.py <작업폴더>          # Mode 1: RFP 요구사항 후보 추출
```

- `render.py`는 같은 이름의 PDF가 있으면 PDF를 우선 렌더한다 (PPTX→LibreOffice 렌더는 폰트가 바뀔 수 있다). `render_report.json`의 폰트 경고가 있으면 Visual 판단에 그 한계를 명시한다.
- `cross_check.py`의 결과는 **후보**다. 숫자·일정·인력·고객명·용어 불일치 후보를 맥락을 보고 판정한다 (예: 단계별 인력 42명/전체 45명은 모순이 아닐 수 있다).
- 숫자를 LLM이 직접 세거나 대조하지 않는다. 스크립트 결과와 원문 unit을 근거로 판단한다.

## 4. Domain Routing

`gm_outline.md`와 RFP 개요만 보고 판정한다 (본문 전체를 읽기 전에):

```
Primary: <예: Data Center Migration>   Secondary: <예: Network>   Cross-cutting: Security / PM / Financial Regulation
```

그리고 **필요한 reference만** 읽는다. 금융 고객이면 `financial-review.md`는 항상 읽는다.

| 시점 | 읽을 파일 |
|---|---|
| 항상 (판단 시작 전) | `references/evaluator-model.md` (평가위원 모델, Severity, Flag 어휘) |
| Mode 2 | `references/presentation-review.md`, `references/key-message.md`, `references/evidence-framework.md`, `references/visual-review.md` |
| Mode 1 | `references/proposal-review.md`, `references/evidence-framework.md`, `references/key-message.md`(목차·소제목 검토 시) |
| 금융 고객 | `references/financial-review.md` |
| 도메인 | `references/domains/<domain>.md` — Primary/Secondary만 (`si-ax`, `cloud`, `ai-genai`, `data-platform`, `datacenter-migration`, `network`, `security`, `aicc`, `msp-operation`) |
| Hygiene Pass | `references/hygiene.md` |
| 리포트 작성 직전 | `references/output-templates.md` (findings.json 스키마와 좋은/나쁜 지적 예시) |

## 5. Review Pass (큰 문서도 한 번에 Context에 넣지 않는다)

**Pass A — Storyline (텍스트만, 전체 한 번에)**: `gm_outline.md`로 GM01→GMn만 읽고 흐름, `STORYLINE BREAK`, 실제로 읽히는 Win Theme를 먼저 판단한다. 본문을 읽기 전에 해야 평가위원처럼 "제목만 넘겨볼 때"의 인상을 얻는다.

**Pass B — Section (이미지 + unit 텍스트, 5~8장 묶음)**: 섹션 단위로 렌더 PNG를 보고 Blind-first Visual Test(`visual-review.md`) → 그 다음 `units/*.md`를 읽고 Winning Triangle(WHY KT × EVIDENCE × HOW), Evidence Ledger, Competitor Replaceability Test, 금융·도메인 체크를 수행한다. 30장 이상이면 섹션별로 서브에이전트에 나눠 맡겨도 된다 — 이때 각 서브에이전트에게 이 SKILL.md, 해당 references, 담당 unit 범위, brief를 넘기고 findings 조각(JSON)을 돌려받는다.

**Pass C — RFP Compliance (Mode 1)**: `rfp_requirements.json`의 요구사항마다 `grep -rl "<키워드>" <작업폴더>/units/`로 대응 위치를 찾고, 내용 유무뿐 아니라 **평가위원이 그 평가항목 기준으로 쉽게 찾을 수 있는가(findability)** 를 판정한다.

**Pass D — Red Team 반론**: 리스크 관리자(악마의 대변인)가 되어 A~C의 PASS·낙관적 판단을 다시 공격한다. "경쟁사 평가위원 출신이라면 여기서 무엇을 물을까?", "이 Evidence는 정말 이번 고객에게 적용되는가?", "내가 쓴 Revised Message에 원문에 없는 사실이 들어갔는가?" 살아남은 판단만 남긴다.

**Pass E — Hygiene (저비용)**: 오탈자·띄어쓰기·용어 통일·고객명/제품명·AI스러운 문장. `cross_check.json`의 용어 변형 후보를 활용한다.

**Synthesis**: Top 5 Winning Issues(수주 영향 순), Memory Test(발표 10분 후 평가위원이 기억할 3가지 vs 의도한 Win Theme), Success Questions 10개 답변.

## 6. 리포트 생성

모든 판단을 `<작업폴더>/findings.json`으로 쓴다 (스키마: `references/output-templates.md`). 그 다음:

```bash
python3 <skill>/scripts/report.py <작업폴더>
```

`report.py`는 다음을 만들고, **Guard 검사**를 자동으로 수행한다:
- `01_executive.md` — Overall Assessment → Top 5 Winning Issues → MUST FIX → SHOULD FIX → What Works Well (+ Memory Test, Storyline)
- `02_slide_review.md` — 장표별 상세 (Hygiene는 맨 뒤)
- `03_rfp_compliance.xlsx` / `.md` — Mode 1
- `04_evidence_ledger.md`
- Guard: Revised Message에 원문에 없는 숫자·금융사명이 들어가면 `[VERIFY: 원문에 없는 …]`을 붙이고 `guard_report.md`에 기록. 출처 없는 Evidence는 자동으로 `UNSUBSTANTIATED`로 강등.

Guard 경고가 나오면 해당 Finding을 고친 뒤 report.py를 다시 돌린다. 마지막으로 사용자에게 채팅으로 **Overall Assessment 2~3줄 + Top 5 + MUST FIX 개수 + 파일 경로**만 요약해 준다. 리포트 전문을 채팅에 붙이지 않는다.

## 7. 판단 품질 체크 (리포트 전에 스스로 확인)

- 각 Top 5는 "이걸 고치면 점수/선택이 바뀌는가?"에 Yes인가? 오탈자가 Top 5에 있으면 대개 잘못된 것이다.
- 같은 지적이 여러 장표에 반복되면 하나의 패턴 Finding으로 묶고 위치를 나열했는가?
- PASS와 What Works Well도 썼는가? 잘된 점을 남겨야 수정 과정에서 그것이 망가지지 않는다.
- 모든 Revised Message가 Protected Facts를 그대로 유지하는가?
- Success Questions 10개 중 답할 수 없는 것은 "자료에서 확인 불가"라고 정직하게 썼는가?
