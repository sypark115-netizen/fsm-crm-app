# proposal-red-team — STEP 1~4 설계 보고서

> 상태: **설계안 (승인 대기)** · 작성일 2026-11-11
> 범위: Requirements Summary · Critical Questions · Benchmark · Architecture · V1 Scope · Roadmap · Risks
> 구현은 아직 하지 않았다. 승인 후 STEP 5(Phase 단위 구현·테스트)로 진행한다.
> PRD는 별도 문서: [`PRD.md`](./PRD.md)

---

## 1. Requirements Summary (1페이지)

**무엇을 만드는가**
KT가 금융사에 제출·발표하는 대형 IT/AX/Cloud/AI/Data/DC/Network 제안서를 **최종 제출 전 평가위원 관점에서 검증**하는 단일 Skill `proposal-red-team`.
문서검사기가 아니라 "평가위원이라면 이 제안을 어떻게 평가하고, KT를 고를 것인가?"를 먼저 묻는 Red Team.

**두 개의 Mode**

| | Mode 1 — Proposal Red Team | Mode 2 — Presentation Red Team |
|---|---|---|
| 대상 | 정식 제출 제안서 (PDF/PPTX, 수백 페이지) | 제안발표 PPT/PDF (20~60장) |
| 핵심 질문 | RFP를 빠짐없이, **평가받기 쉽게** 대응했는가? | **왜 KT인가?** 보이고·믿기고·기억되는가? |
| Backbone | RFP → 평가항목 → 요구사항 → KT 대응 → Evidence → Page → Compliance → Risk | Customer → Differentiation → Why KT → Evidence → How → Impact |
| 핵심 산출물 | RFP Compliance Matrix + 감점 Risk | GM Storyline + Winning Triangle + Memory Test |

**판단 원칙 (우선순위 순)**
1. 평가위원 관점 → 2. 전략/Storyline → 3. Differentiation → 4. Why KT → 5. Evidence → 6. How → 7. Governing Message → 8. Visual → 9. PM/수행팀 Trust → 10. RFP Compliance → 11. 논리·기술 일관성 → 12. 문장/오탈자(Hygiene)
- 최상위 평가모델: **SEE → UNDERSTAND → BELIEVE → TRUST → REMEMBER**
- **Winning Triangle = WHY KT × EVIDENCE × HOW** — Evidence 없는 차별화는 차별화가 아니다. 적용방법(How) 없는 Evidence도 부족.
- **KT Capability ≠ Differentiation** — Capability → Evidence → 고객별 적용 → 고객 Impact 로 연결돼야 인정.
- **Competitor Replaceability Test** — "KT"를 경쟁사명으로 바꿔도 말이 되면 `DIFFERENTIATION FAILURE` 후보.
- "존재한다"와 "평가위원에게 전달된다"는 다르다 → 내용이 있어도 찾기 어렵거나 안 보이면 감점 Risk.

**절대 규칙 (Guardrails)**
- Evidence·규제·사실을 **AI가 만들어내지 않는다** → `UNSUBSTANTIATED CLAIM` / `EVIDENCE REQUIRED` / `VERIFY` / `REGULATORY VERIFY`
- **Protected Facts**(고객명·가격·인력·일정·Reference·제품명·사양·계약조건·실적·숫자)는 수정 제안하지 않고 `VERIFY`만 표시
- **LOCAL ONLY** 기본값, 원본 파일 **절대 overwrite 금지**
- 결과는 **MUST FIX / SHOULD FIX / ENHANCEMENT / PASS** 4단계. 점수 남발 금지. 오탈자 목록을 맨 앞에 두지 않음.

**V1 산출물**: ① Executive Red Team ② Slide-by-Slide Review ③ RFP Compliance (Mode 1)
**V1 성공기준**: 기능 개수가 아니라 "Senior 제안 전문가가 읽고 **실제로 고칠 것이 생기는가**"

---

## 2. Critical Questions / Missing Requirements

개발 방향이 바뀌는 질문만 추렸다. **굵게** 표시한 것이 기본 가정(답이 없으면 이대로 진행).

| # | 질문 | 왜 중요한가 | 기본 가정 |
|---|---|---|---|
| Q1 | **실행 런타임은?** Claude Code / Codex(`agents/openai.yaml`) / 둘 다 | Skill 포맷·서브에이전트 병렬화·Vision 호출 방식이 달라짐. 초안에 `openai.yaml`이 있어 확인 필요 | **Claude Code 우선**, SKILL.md는 표준 포맷으로 써서 Codex 호환 유지 |
| Q2 | **기밀자료를 클라우드 LLM에 보내도 되는가?** (KT 보안정책상 Claude API/Enterprise 허용 여부) | "LOCAL ONLY"는 파일 저장/전송 정책이지만, 판단은 LLM이 한다. 텍스트·슬라이드 이미지가 모델로 전송됨. 허용 안 되면 아키텍처 자체가 바뀜(온프렘 모델) | **승인된 LLM 엔드포인트만 사용**, 그 외 외부 전송(웹 맞춤법 검사기, 외부 OCR API 등) 0건 |
| Q3 | **RFP·제안서 원본 포맷 비중은?** 특히 **HWP/HWPX** | 국내 금융 RFP는 HWP 비율이 높음. HWP 파서는 AGPL 등 라이선스 문제가 많음 | V1: **PDF/PPTX만 직접 지원**, HWP는 사용자가 PDF 변환 후 투입. HWPX(XML)는 V2 |
| Q4 | **의도된 Win Theme / 경쟁사를 사용자가 입력하는가?** | Memory Test(의도 vs 실제 비교)와 Replaceability Test는 기준값이 있어야 판정 가능 | 실행 시 `brief.yaml`로 Win Theme 3개·경쟁사·고객사·발표시간 입력. 없으면 AI가 추정하되 `ASSUMED` 표시 |
| Q5 | **평가 기준표(배점) 입수 가능 여부** | Mode 1의 "평가받기 쉽게"는 배점표·평가항목이 있어야 우선순위화 가능 | RFP에 있으면 추출, 없으면 요구사항 단위로만 판정하고 배점 기반 우선순위는 생략 |
| Q6 | **결과물 포맷**: Markdown / Excel / Word 중 무엇이 실제 업무에 쓰이나 | 제안팀은 Compliance Matrix를 보통 Excel로 돌린다 | **Executive·Slide Review = Markdown(+HTML 뷰)**, **RFP Compliance = XLSX + Markdown** |
| Q7 | **V1 검증용 실제 Sample** — 과거 제안서(가능하면 수주/실주 결과 포함) 2~3건 제공 가능한가 | 판단 품질은 실제 자료로만 검증 가능. 합성 샘플로는 "그럴듯한 일반론"을 걸러낼 수 없음 | 비식별화된 과거 발표본 1건 + 제출본/RFP 1세트를 Golden Set으로 사용 |
| Q8 | **Skill 저장 위치** — 이 저장소(fsm-crm-app, Next.js CRM)는 무관한 프로젝트 | 기밀 제안서·테스트 샘플이 CRM 저장소에 섞이면 안 됨 | 설계문서는 지정 브랜치에 두되, **구현은 별도 private repo** 또는 `~/.claude/skills/` 로 분리 권장 |

---

## 3. GitHub / Open Source Benchmark

조사 방법: PyPI 메타데이터(최신 버전·배포일·라이선스)를 2026-11-11에 직접 조회 + 실행환경에서 설치/동작 확인. "유지보수 상태"는 최신 릴리스 날짜 기준.
판정: **Reuse**(그대로 의존) / **Wrap**(얇게 감싸 사용) / **Ref**(접근법만 참고, 코드 복사 안 함) / **Avoid**(라이선스·보안 사유) / **Build**(대안 없음)

### 3.1 PPTX Parsing / Open XML Editing / Comment

| Project | URL | License | 최신 릴리스 | 주요 기능 | 재사용 부분 | Gap | 판정 |
|---|---|---|---|---|---|---|---|
| python-pptx | github.com/scanny/python-pptx | MIT | 1.0.2 (2024-08) | Shape·Text·Table·Chart·Notes·Placeholder·좌표/폰트 접근 | **구조 추출의 핵심**: shape 위치·크기·폰트크기·placeholder 유형(Title 판별) → GM 추출, 시각 위계 추정 | 릴리스 2년 정체(안정판). **Comment API 없음**, SmartArt·그룹 내부 일부 미지원, 렌더링 불가 | **Reuse** |
| lxml (python-pptx 내부) | lxml.de | BSD | 활발 | Open XML 직접 조작 | SmartArt(`dgm`), 그룹 shape, Comment XML 직접 읽기/쓰기 | 스키마 지식 필요 | **Reuse** |
| Open XML SDK | github.com/dotnet/Open-XML-SDK | MIT | 활발 | .NET 공식 OOXML SDK, Modern Comment 포함 | V2 PPT Comment 삽입의 레퍼런스 구현 | .NET 런타임 필요 → Python 스킬과 이질적 | **Ref** (V2) |
| Anthropic `pptx` / `docx` Skill | (이 환경에 `anthropic-skills:pptx` 설치됨) | Source-available(코드 재배포 불가) | — | PPTX 생성·편집·썸네일 워크플로 | V2 Redline/Revised PPT 생성 시 **런타임에서 호출**만 | 코드 복사 불가 | **Ref** (호출만) |
| MarkItDown | github.com/microsoft/markitdown | MIT | 0.1.9 (2026-10) | PPTX/DOCX/XLSX/PDF → Markdown | 보조자료(Word·Excel) 빠른 텍스트화 | 좌표·폰트·placeholder 정보 손실 → 시각 판단에 부적합 | **Wrap** (보조자료 전용) |

**결론**: PPTX는 python-pptx + lxml로 **구조 추출 직접 구현**. PPT Comment/Redline은 Python 생태계에 성숙한 라이브러리가 없음 → V2에서 Open XML(legacy comment 또는 modern comment) 직접 작성.

### 3.2 PPTX Rendering

| Project | URL | License | 상태 | 기능 | Gap | 판정 |
|---|---|---|---|---|---|---|
| LibreOffice (headless `soffice --convert-to pdf`) | libreoffice.org | MPL-2.0 | 24.2 설치 확인 | PPTX → PDF → 이미지 | **폰트 대체·레이아웃 깨짐** 가능. 이 환경엔 한글 폰트가 WenQuanYi(중국어)뿐 → 맑은 고딕/KT 전용폰트 미설치 시 실제와 다르게 보임 | **Reuse** (+ 폰트 번들 필수) |
| PowerPoint COM / AppleScript export | — | 사용자 보유 라이선스 | — | 원본 그대로 렌더 | Windows/Mac 로컬 PowerPoint 필요 | **V2 옵션** (고충실도 모드) |
| 사용자 제공 PDF | — | — | — | 발표본은 대부분 PDF 동봉됨 | — | **V1 권장 경로**: PDF가 있으면 PDF를 렌더 기준으로 사용 |

### 3.3 PDF Extraction / Rendering

| Project | URL | License | 최신 릴리스 | 기능 | 판정 / 이유 |
|---|---|---|---|---|---|
| pypdfium2 | github.com/pypdfium2-team/pypdfium2 | Apache-2.0 / BSD-3 | 5.15.2 (2026-11) | Chrome PDFium 기반 고속 렌더 + 텍스트 | **Reuse — 렌더 기본 엔진** (페이지 단위 스트리밍, 대용량에 유리) |
| pdfplumber (+pdfminer.six) | github.com/jsvine/pdfplumber | MIT | 0.11.10 (2026-06) | 문자 단위 좌표·폰트크기·표 추출 | **Reuse — PDF 텍스트·폰트크기·표** (GM 추정에 폰트크기 필요) |
| pypdf | github.com/py-pdf/pypdf | BSD-3 | 7.0.1 (2026-11) | 분할·메타데이터·북마크 | **Reuse** — 목차/북마크 → 섹션 구조, 대용량 분할 |
| Docling (IBM) | github.com/docling-project/docling | MIT | 2.150 (2026-11) | 레이아웃 분석·표 구조·OCR, PPTX/DOCX도 지원 | **V2 Wrap** — RFP의 복잡한 표/스캔본에 강함. 단 torch 모델 의존으로 무거움 |
| Unstructured | github.com/Unstructured-IO/unstructured | Apache-2.0 | 0.27 (2026-11) | 범용 문서 파티셔닝 | **Ref** — Docling과 중복, 의존성 큼 |
| Marker | github.com/datalab-to/marker | 코드 Apache-2.0 표기 / **모델 가중치 별도 라이선스(상업 사용 제한 이력)** | 2.1 (2026-10) | PDF→Markdown 고품질 | **Avoid** — 대기업 상업 사용 조건 `VERIFY` 필요 |
| PyMuPDF | github.com/pymupdf/PyMuPDF | **AGPL-3.0** 또는 상용 | 2.1 (2026-11) | 가장 빠르고 기능 많음 | **Avoid** — AGPL. 사내 배포 시 소스공개 의무 Risk |
| pdf2image (+poppler) | github.com/Belval/pdf2image | MIT (poppler는 GPL) | 1.17 (2024-01) | PDF→이미지 | **Avoid/Fallback** — pypdfium2로 대체 가능 |

### 3.4 Slide Visual Analysis

| 후보 | License | 판단 |
|---|---|---|
| 멀티모달 LLM Vision (Claude) | 서비스 약관 | **핵심 엔진.** 3초/10초/30초 인지 테스트는 결국 "보는 모델"의 판단. OSS 대체재 없음 |
| Saliency 모델 (DeepGaze 등 학술 OSS) | 코드/가중치 라이선스 개별 확인 필요 | **V3 Ref** — 시선 예측 히트맵은 흥미롭지만, 제안서 판단 품질과의 상관이 검증되지 않음 |
| OmniParser (Microsoft, UI 요소 검출) | 모델 일부 AGPL | **Avoid** — UI 스크린 대상, 슬라이드에 부적합 |
| **자체 구조 지표** (python-pptx/pdfplumber 좌표·폰트크기) | 자체 | **Build** — 텍스트 밀도, 최대 폰트 요소, 단어 수, 요소 수, 색 대비 등 결정적(deterministic) 지표로 Vision 판단을 **교차검증** |

**핵심 설계 아이디어 — Blind-first Visual Test**: 모델에게 먼저 **이미지 1장만** 주고 "3초에 보이는 것 / 10초 후 이해한 장표 주제"를 답하게 한 뒤, 그 다음에 추출된 GM(작성자 의도)을 보여주고 비교. 둘이 다르면 `MESSAGE DELIVERY FAILURE`. 텍스트를 먼저 주면 모델이 "읽어서" 판단해 버려 평가위원의 실제 지각을 시뮬레이션하지 못한다.

### 3.5 Proposal Review / Document Redlining

| 후보 | License | 판단 |
|---|---|---|
| OSS 제안서 Red Team 도구 | — | **조사 결과 실질적인 OSS 없음.** 상용(Loopio, Responsive, AutogenAI 등)은 RFP 응답 작성·라이브러리 중심이지 평가위원 관점 Red Team이 아님 → **Build** (판단 로직이 이 제품의 본체) |
| Shipley 방법론 (Color Team Review: Pink/Red/Gold) | 방법론(상용 교육) | **Ref** — Red Team = 평가위원 시뮬레이션이라는 개념 정합. 용어·절차만 참고 |
| python-redlines (Open-XML-PowerTools 래퍼) | MIT | 2.0.0 (2026-10) | **V2 Wrap** — Word 제안서의 Track Changes Redline 생성 |
| python-docx | MIT | 1.2.0 (2025-06) | **Reuse** — Word 보조자료 읽기, V2 Word 리포트 |
| openpyxl | MIT | 3.1.5 (2024-06) | **Reuse** — Compliance Matrix XLSX 출력, Excel 인력/일정표 읽기 |

### 3.6 Korean Proofreading

| 후보 | License | 상태 | 판단 |
|---|---|---|---|
| py-hanspell (부산대/네이버 웹 검사기 호출) | **UNKNOWN** | 1.1 (**2015**) | **Avoid** — 라이선스 불명 + **기밀 문장을 외부 웹으로 전송** + 유지보수 중단 |
| 부산대 맞춤법 검사기 웹 | 이용약관 | — | **Avoid** — 외부 전송 |
| kiwipiepy (Kiwi 형태소 분석기) | Apache-2.0 | 0.24.1 (2026-10) | **Reuse (V1 선택)** — 로컬 동작. 띄어쓰기 교정 후보, 용어 정규화(표기 변형 클러스터링)에 사용 |
| 바른(Bareun) 등 상용 엔진 | 상용 | — | **V2 옵션** — 온프렘 가능 시 검토 |
| LLM 교정 | — | — | **V1 기본** — 맞춤법·어색한 한국어·AI스러운 문장 판단. Hygiene 영역이므로 별도 저비용 Pass로 분리 |

### 3.7 Google Drive / Large File

| 후보 | License | 상태 | 판단 |
|---|---|---|---|
| google-api-python-client (`MediaIoBaseDownload` chunked) | Apache-2.0 | 2.202 (2026-11) | **V2 Reuse** — Resumable·청크 다운로드로 200MB+ 대응 |
| rclone | MIT | 활발 | **V2 Ref** — 폴더 동기화가 필요할 때 |
| 이 환경의 Google Drive 커넥터 | — | — | **V2** — 단, 기본값 LOCAL ONLY와 충돌하므로 opt-in |

### 3.8 Build vs Reuse 요약

- **Reuse**: python-pptx, lxml, pypdfium2, pdfplumber, pypdf, openpyxl, python-docx, kiwipiepy, LibreOffice
- **Build (제품의 본체)**: Document Model, Domain Router, Review Rubric(references), Evidence Ledger, GM Storyline 분석, Cross-slide Checker, Report Generator
- **Avoid**: PyMuPDF(AGPL), py-hanspell(라이선스 불명·외부전송), Marker(모델 라이선스 VERIFY), 외부 OCR/맞춤법 웹 API 전부
- **V2 이후**: Docling, python-redlines, PPT Comment 직접 작성, Google Drive API

> 시사점: 파싱/렌더링은 성숙한 OSS로 80%가 해결되지만, **이 프로젝트의 가치는 100% Build 영역(판단 기준과 Evidence 추적)에 있다.** 개발 공수도 그쪽에 써야 한다.

---

## 4. Recommended Architecture

### 4.1 설계 원칙 3가지

1. **Scripts = 사실(Facts), LLM = 판단(Judgment).** 숫자 대조·좌표·폰트크기·페이지 매핑 같은 결정적 작업은 스크립트가, 평가위원 시뮬레이션은 LLM이 한다. LLM이 숫자를 세거나 대조하게 하지 않는다.
2. **모든 지적은 출처를 가진다.** 리포트의 모든 행은 `file#slide/page#shape` 포인터를 갖는다. 포인터 없는 Evidence는 자동으로 `EVIDENCE REQUIRED`.
3. **전체 문서를 한 번에 Context에 넣지 않는다.** "작은 골격 → 묶음 정밀검토 → 교차검증 → 종합"의 다단계 Pass.

### 4.2 Pipeline

```
INPUT (local file/folder, brief.yaml)
  │
  ▼
[1] INGEST ─ scripts/ingest.py
  │   · 파일 분류: RFP / Proposal / Presentation / 보조자료 (파일명+내용 휴리스틱 → 사용자 확인)
  │   · 원본은 읽기 전용, 작업 사본은 ./.redteam/<run-id>/ 에만 생성
  │   · PPTX: python-pptx+lxml → shape/text/table/chart/notes/좌표/폰트
  │   · PDF : pdfplumber(문자·폰트크기·표) + pypdf(북마크) — 페이지 스트리밍
  │   · 미디어(이미지/동영상)는 추출하지 않고 크기만 기록 → 200MB 파일도 텍스트는 수 MB
  ▼
[2] NORMALIZE → Document Model (docmodel.json, 슬라이드/페이지 단위 레코드)
  │   { id, file, index, section, title_candidate(GM), body_blocks[], tables[], numbers[],
  │     dates[], headcount[], terms[], font_hierarchy, text_density, notes, image_path }
  ▼
[3] RENDER ─ scripts/render.py
  │   · PDF 우선(있으면) → pypdfium2 → PNG (Review용 1280px, 썸네일 400px)
  │   · PPTX만 있으면 LibreOffice → PDF → PNG, 폰트 대체 발생 시 경고 기록
  ▼
[4] CROSS-CHECK ─ scripts/cross_check.py   (LLM 미사용, 결정적)
  │   · 숫자/단위/일정/인력/금액 불일치 후보 · 고객명·제품명 표기 변형 · 용어 비통일
  │   · 결과는 "후보"로만 → LLM이 맥락 판단 후 Severity 부여
  ▼
[5] ROUTE ─ Domain Router (LLM, 소형 입력)
  │   입력: 목차 + 전체 GM 목록 + RFP 개요 (수천 토큰)
  │   출력: Mode(1/2) · Primary/Secondary/Cross-cutting Domain · 로드할 references 목록
  ▼
[6] REVIEW (LLM, 다단계 Pass)
  │   Pass A  Storyline  : GM01→GMn만으로 흐름·Break·Win Theme 추정 (전체를 한 번에, 텍스트만)
  │   Pass B  Section    : 섹션(5~8장) 단위로 이미지+구조데이터 → Blind-first Visual,
  │                        Winning Triangle, Evidence Ledger 작성  ← 서브에이전트 병렬 가능
  │   Pass C  RFP        : (Mode 1) 요구사항 단위로 Proposal 검색 → Compliance 판정
  │   Pass D  Red Team   : 리스크 관리자 역할로 A~C의 낙관적 판단에 반론 (Devil's advocate)
  │   Pass E  Hygiene    : 오탈자·띄어쓰기·AI스러운 문장 (저비용, 별도)
  ▼
[7] SYNTHESIZE ─ Memory Test(의도 Win Theme vs 실제 기억 3가지), Top 5 Winning Issues
  ▼
[8] REPORT ─ scripts/report.py
      01_executive.md · 02_slide_review.md · 03_rfp_compliance.xlsx/.md · evidence_ledger.md
```

### 4.3 핵심 데이터 구조

- **Document Model** — 슬라이드/페이지 레코드의 배열. 모든 후속 단계의 단일 진실원천.
- **Evidence Ledger** — `Claim | Claim 위치 | Evidence 유형(8종) | Evidence 위치 | 상태(SUPPORTED / WEAK / UNSUBSTANTIATED / VERIFY)`. Winning Triangle 판정과 Hallucination 방지의 핵심. Evidence 위치가 비어 있으면 상태는 자동으로 `UNSUBSTANTIATED`.
- **Requirement Matrix** (Mode 1) — `REQ-ID | RFP 원문·위치 | 평가항목/배점 | 대응 위치 | 대응 요약 | 발견용이성 | 상태 | Risk`. "발견용이성"(평가위원이 그 페이지에서 쉽게 찾는가)을 별도 컬럼으로 둬서 "있지만 안 보이는" 문제를 잡는다.
- **Finding** — 모든 지적의 공통 스키마: `id, location, severity, category, current, issue, why_it_matters, recommendation, revised(Protected Fact는 [VERIFY: …] 플레이스홀더), triangle{why_kt, evidence, how}, visual_rec, evaluator_view`.

### 4.4 Skill 디렉터리 구조 (초안 대비 수정 제안)

```
proposal-red-team/
├── SKILL.md                     # Control Plane: Mode 판정, Pipeline 순서, Guardrails, 언제 무엇을 Load
├── agents/openai.yaml           # (Q1 결과에 따라) Codex 호환용, 선택
├── references/                  # 필요할 때만 Load
│   ├── evaluator-model.md       # [추가] SEE→UNDERSTAND→BELIEVE→TRUST→REMEMBER, Severity 기준, 공통 판단규칙
│   ├── proposal-review.md       # Mode 1: Compliance 판정 기준, 발견용이성, 감점 패턴
│   ├── presentation-review.md   # Mode 2: Backbone, Memory Test, PM/Team Trust
│   ├── key-message.md           # GM 평가 9문항, Storyline Break, Replaceability Test
│   ├── evidence-framework.md    # Evidence 8유형, Winning Triangle, Capability≠Differentiation
│   ├── visual-review.md         # 3/10/30초 테스트, Blind-first 절차, Visual 추천 14종의 "언제"
│   ├── financial-review.md      # 금융 Cross-cutting 체크 (규제 "확인할 항목"만, 결론 단정 금지)
│   ├── domains/                 # [변경] 단일 파일 → 도메인별 분리 (Router가 필요한 것만 Load)
│   │   ├── dc-migration.md  ├── cloud.md  ├── ai-genai.md  ├── data-platform.md
│   │   ├── network.md       ├── security.md  ├── aicc.md   ├── msp-operation.md  └── si-ax.md
│   ├── hygiene.md               # [추가] 오탈자·용어·AI스러운 문장 패턴 (가장 낮은 우선순위)
│   └── output-templates.md      # [추가] 3개 리포트의 정확한 포맷과 예시 1개씩
├── assets/
│   └── brief.template.yaml      # [추가] Win Theme·경쟁사·고객사·발표시간·Mode 입력
├── scripts/
│   ├── ingest.py                # [통합] extract_pptx + extract_pdf → docmodel.json
│   ├── render.py                # PDF/PPTX → PNG (페이지 스트리밍)
│   ├── cross_check.py           # 숫자·일정·인력·용어 교차검증 후보
│   ├── rfp_split.py             # [추가] RFP 요구사항 후보 문장 분할("~하여야 한다", 번호체계)
│   └── report.py                # Finding JSON → MD/XLSX
└── tests/
    ├── fixtures/                # 합성 샘플(공개 가능) — 의도적 결함을 심은 PPTX/PDF
    ├── golden/                  # [추가] 실제 비식별 샘플 + 전문가 기대 Finding (repo 밖 보관)
    └── test_*.py                # 스크립트 단위 테스트 + 판단 품질 회귀 체크리스트
```

변경 이유:
- `analyze_structure.py`는 ingest 단계의 폰트/좌표 지표로 흡수 (별도 파일 불필요).
- `domain-review.md` 단일 파일은 도메인 9개가 쌓이면 수천 줄 → Router의 의미가 사라짐. 도메인별 분리.
- `evaluator-model.md`, `output-templates.md`를 분리해 SKILL.md를 200줄 이하 Control Plane으로 유지.
- `golden/`은 **판단 품질 회귀 테스트**의 근거. 이게 없으면 V1 성공기준을 측정할 수 없다.

### 4.5 V3 확장 지점 (지금은 인터페이스만)

- `references/kt-context/` 자리 — KT Reference·Asset·인증 목록을 **사용자가 제공한 사실만** 넣는 슬롯. Evidence Ledger가 이를 "검증된 출처"로 인정.
- Document Model과 Finding이 JSON 스키마로 고정돼 있으므로, 향후 과거 제안서·평가결과·Win/Loss를 같은 스키마로 색인하면 RAG(Winning Proposal Library)로 연결 가능.

---

## 5. V1 Scope

### 넣는 것 (판단 품질에 직결)

| 항목 | 이유 |
|---|---|
| Local PPTX / PDF / Folder 입력, 파일 역할 자동분류 + 사용자 확인 | 최소 입력경로 |
| Document Model (구조 추출) + 슬라이드 렌더 | 모든 판단의 기반 |
| Mode 자동판정 + Domain Router | 불필요한 체크리스트 적용 방지 |
| GM Storyline 분석 (Break, Replaceability, So What) | Mode 2의 핵심 |
| Winning Triangle + Evidence Ledger | 차별화 판정의 핵심, Hallucination 방지 |
| Blind-first Visual Test (3/10/30초) + Visual 추천 | `MESSAGE DELIVERY FAILURE` 판정 |
| PM/Team Trust, Memory Test | 발표 판단의 마지막 관문 |
| RFP Requirement 추출 → Compliance Matrix (발견용이성 포함) | Mode 1의 핵심 |
| Cross-slide Check (숫자·일정·인력·용어) | 결정적·저비용·고가치 |
| Financial Cross-cutting (`REGULATORY VERIFY` 방식) | 금융 고객 필수 |
| Hygiene Pass (LLM + kiwipiepy) | 낮은 우선순위로 분리 |
| 산출물 3종 (MD + Compliance XLSX) | 요구된 V1 Output |
| `brief.yaml` 입력 | Memory/Replaceability 판정 기준값 |

### 넣지 않는 것 (V2 이후)

| 항목 | V1 제외 이유 | 구현비용 |
|---|---|---|
| Google Drive 연동 | 판단 품질 무관, LOCAL ONLY 원칙과 충돌 | 중 |
| PPT Comment 삽입 / Redline PPT / Revised PPT | 판단이 맞는지 먼저 검증해야 의미 있음. OOXML 서식 깨짐 Risk 큼 | 상 |
| Word Track Changes Redline | 동일 | 중 |
| HWP 직접 파싱 | 라이선스 문제(대부분 AGPL), PDF 변환으로 우회 가능 | 상 |
| Docling 기반 고급 표/스캔 OCR | 대부분 제안서는 텍스트 PDF. 스캔 RFP가 많으면 V1.5로 앞당김 | 중 |
| 점수화 대시보드, 웹 UI | 요구사항상 점수 남발 금지, CLI/Skill로 충분 | 중 |
| 과거 제안서 RAG, 경쟁사 DB | V3 | 상 |
| Saliency 히트맵 | 판단 품질 상관 미검증 | 중 |

---

## 6. Development Roadmap

### V1 — Judgment Quality (Phase 단위, 각 Phase마다 구현→Test→Sample 실행→결과확인→문제분석→개선)

| Phase | 내용 | 완료 조건 (Exit) |
|---|---|---|
| P0 | Golden Set 준비: 비식별 실제 샘플 1~2세트 + 전문가 기대 Finding 10~20개 (Q7) | 사용자 확인 |
| P1 | `ingest.py` + `render.py` + Document Model, 한글 폰트 번들 | 샘플 전 페이지 추출·렌더 성공, GM 추출 정확도 육안 검증 |
| P2 | SKILL.md + `evaluator-model` · `key-message` · `evidence-framework` · `presentation-review` → **Mode 2 Executive + Slide Review** | Golden 기대 Finding 재현율, "일반론" 비율 점검 |
| P3 | `visual-review` (Blind-first) + PM Trust + Memory Test | MESSAGE DELIVERY FAILURE 판정이 전문가 판단과 일치하는지 |
| P4 | `rfp_split.py` + `proposal-review` → **Mode 1 Compliance Matrix (XLSX)** | 요구사항 누락 0건(샘플 기준), 오탐 검토 |
| P5 | `cross_check.py` + `financial-review` + `domains/*` + Hygiene | 숫자/일정 불일치 심은 결함 전부 검출 |
| P6 | 대용량(200MB+) · 다중 파일 폴더 · 회귀 테스트 정리 | 전체 Pipeline이 Context 한도 내 완료 |

Mode 2(발표)를 Mode 1보다 먼저 하는 이유: 판단 품질 차이가 가장 크게 드러나는 영역이고, 페이지 수가 적어 반복 개선 주기가 빠르다. Mode 1의 Compliance는 구조화가 쉬워 뒤에 붙여도 안정적이다.

### V2 — Workflow Automation (V1 품질 검증 후)
Google Drive(opt-in) · Word/Excel 보조자료 심화 · PPT Comment 삽입 · Redline PPT · Revised PPT · Word Redline · Render QA(PowerPoint 고충실도 렌더) · HWPX · Docling OCR

### V3 — KT Proposal Intelligence
과거 수주/우수 제안서 · RFP · 평가결과 · Win/Loss · KT Reference/Asset DB · 경쟁사 Profile · 고객 인터뷰 → Winning Proposal Library / RAG. Evidence Ledger가 "KT 검증 자산"을 직접 인용 가능.

---

## 7. Risks

| 영역 | Risk | 영향 | 대응 |
|---|---|---|---|
| **PPT/PDF Parsing** | SmartArt·그룹 shape·이미지화된 텍스트(캡처 붙여넣기)·표 병합셀 누락. 제안서는 "도식 이미지"가 많아 텍스트 추출만으로는 핵심을 놓침 | GM·Evidence 누락 → 잘못된 `UNSUBSTANTIATED` | lxml로 SmartArt/그룹 재귀 추출, 텍스트 커버리지 지표(이미지 면적 대비 텍스트량) 기록 → 낮으면 Vision 판독으로 보완 |
| | Title placeholder를 안 쓰는 템플릿 → GM 자동판별 실패 | Storyline 분석 오류 | 폰트크기·위치 휴리스틱 + 첫 실행 시 GM 목록을 사용자에게 보여주고 확인 |
| **Visual Analysis** | LibreOffice 렌더 시 폰트 대체·줄바꿈 변경 (이 환경에 한글 폰트 없음 확인) | 실제와 다른 장표로 Visual 판단 → 오판 | **PDF 우선 렌더**, 한글 폰트 번들, 폰트 대체 감지 시 경고 |
| | LLM이 이미지를 "읽어서" 판단 → 3초 인지 시뮬레이션 실패 | Visual Review 무의미화 | Blind-first 절차, 결정적 지표(최대 폰트 요소·텍스트 밀도)로 교차검증 |
| | Visual 추천이 "아이콘 넣으세요" 수준의 일반론 | 전문가에게 무가치 | 추천 시 5문항(무엇을/왜 안 보이나/어떤 방식/어디에/효과) 강제, 근거 없는 추천 금지 |
| **Large Files** | 200MB+ 대부분은 이미지·동영상. 무작정 렌더하면 시간·디스크 폭증 | 실행 실패 | 미디어 비추출, 페이지 스트리밍 렌더, 섹션 단위 Pass, 진행상태 manifest로 재시작 가능 |
| | 300페이지 제출본은 한 Context에 안 들어감 | 교차 페이지 모순 놓침 | 교차검증은 스크립트(결정적)로, LLM은 GM 골격+섹션 묶음만 |
| **Hallucinated Evidence** | 모델이 "KT는 OO은행 차세대 수행" 같은 그럴듯한 실적을 만들어 Revised Message에 삽입 | **가장 치명적**: 허위 실적이 제안서에 들어갈 수 있음 | Evidence Ledger 출처 포인터 필수, 출처 없는 사실은 `[EVIDENCE REQUIRED]` 플레이스홀더로만, Protected Facts 변경 금지 규칙, Pass D가 Revised Message 속 신규 사실을 재검사 |
| **Financial Regulation** | 전자금융감독규정·클라우드 이용 가이드·망분리 완화·신용정보법 등은 개정이 잦음. 모델 지식이 낡았을 수 있음 | 잘못된 규제 지적 → 신뢰 붕괴 | 규제는 "확인해야 할 질문"으로만 제시, 결론 단정 금지, 항상 `REGULATORY VERIFY` + 확인할 공식 출처명 제시 |
| **Confidential Data** | 슬라이드 텍스트·이미지가 LLM 엔드포인트로 전송됨. 맞춤법 웹검사기 등 외부 전송 경로 | 보안사고·규정위반 | Q2 확정 전 실제 기밀자료 투입 금지, 외부 전송 라이브러리 배제(3.6), 산출물은 로컬 `./.redteam/`에만, 테스트 샘플은 repo에 커밋 금지(.gitignore) |
| **Redline Formatting** (V2) | PPT 직접 수정 시 마스터/레이아웃·폰트·애니메이션 깨짐, Modern/Legacy Comment 호환 문제 | 사용자가 결과 파일을 못 씀 | V1에서 원본 수정 0건. V2에서도 **사본에 Comment만 추가**부터 시작, Render QA로 전후 비교 |
| **판단 품질 자체** | 모든 장표에 비슷한 지적("Evidence 보강 필요") 반복 → 노이즈 | 사용자가 리포트를 안 읽음 | Top 5 Winning Issues 강제 선정, 동일 패턴은 묶어서 1건으로, Golden Set 회귀 테스트, PASS도 명시해 "잘된 점" 보존 |

---

## 다음 단계 (승인 요청)

1. 위 **Critical Questions Q1~Q8** 답변 (특히 Q1 런타임, Q2 LLM 전송 허용, Q7 샘플)
2. Architecture(4.4 디렉터리 구조 수정안) 승인
3. 승인 시 **P0(Golden Set) → P1(Ingest/Render)** 부터 STEP 5 착수
