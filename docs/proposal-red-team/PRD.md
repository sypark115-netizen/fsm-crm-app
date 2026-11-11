# PRD — proposal-red-team (V1)

> 상태: 초안 (승인 대기) · 2026-11-11 · 설계 근거: [`REPORT.md`](./REPORT.md)

## 1. Problem

대형 금융 IT 제안에서 KT 제안팀은 마감 직전까지 내용을 "채우는" 데 집중한다. 그 결과:

- 좋은 내용이 있어도 **평가위원이 제한된 시간 안에 보지 못한다** (있지만 안 보임).
- "KT는 Network·Cloud·DC·AI 역량을 보유"처럼 **경쟁사도 쓸 수 있는 문장**이 차별화로 남는다.
- 주장과 Evidence, Evidence와 고객 적용방법(How)이 **끊어져** 있다.
- RFP 요구사항 누락, 페이지 간 숫자·일정·인력 불일치가 **제출 후에** 발견된다.
- 내부 리뷰는 시간이 부족하고, 작성자 관점이라 평가위원 관점의 냉정한 검증이 어렵다.

## 2. User

| User | 상황 | 원하는 것 |
|---|---|---|
| 제안 PM / 사업개발 담당 (Primary) | 제출 D-3~D-1, 발표 리허설 전 | 수주에 영향 큰 문제 Top 5와 즉시 고칠 수 있는 수정 문장 |
| 제안 작성자 (장표 Owner) | 담당 섹션 수정 | 내 장표의 Slide-by-Slide 지적과 Revised Message |
| 발표 PM | 발표 준비 | Storyline, Memory Test, PM이 보여줄 Expert Insight |
| 제안 리더 / 임원 | Go/No-go 최종 점검 | Executive 1페이지 |

## 3. Use Cases

1. **발표본 최종 점검**: 발표 PDF + brief(Win Theme, 경쟁사) → "평가위원이 기억할 3가지가 우리가 의도한 것과 같은가?"
2. **제출본 Compliance 점검**: RFP + 제안서 → 요구사항별 대응 위치·발견용이성·누락 Matrix
3. **차별화 스트레스 테스트**: 핵심 메시지에 경쟁사명 대입 → 교체 가능한 문장 목록
4. **Evidence 감사**: 모든 핵심 주장 → Evidence 유무·유형·출처 → `UNSUBSTANTIATED CLAIM` 목록
5. **일관성 점검**: 제출본과 발표본 간 숫자·일정·인력·용어 충돌
6. **폴더 일괄 투입**: `proposal-red-team ./customer-project/` → 파일 역할 자동분류 후 적절한 Mode 실행

## 4. Mode 1 — Proposal Red Team

- 대상: 정식 제출 제안서 (+ RFP 필수)
- 흐름: RFP → 평가항목/배점 → 요구사항(REQ-ID) → KT 대응 → Evidence → Page → Compliance → Risk
- 판정: `COMPLIANT / PARTIAL / HARD TO FIND / MISSING / CONFLICT`
  - **HARD TO FIND** = 내용은 있으나 평가위원이 해당 평가항목 기준으로 찾기 어려움 (목차·제목·대응표에 없음)
- 추가 검토: 논리 모순, 숫자/일정/인력 불일치, 기술 오류, 금융규제·보안 Risk(`REGULATORY VERIFY`), 고객명·제품명 오류, Hygiene

## 5. Mode 2 — Presentation Red Team

- 대상: 발표 PPT/PDF
- Backbone: Customer → Differentiation → Why KT → Evidence → How → Impact (6문항 필수 응답)
- 평가모델: SEE(3~5초) → UNDERSTAND(10초) → BELIEVE → TRUST → REMEMBER
- 핵심 판정: Storyline Break, Differentiation Failure(Replaceability), Unsubstantiated Claim, Message Delivery Failure, PM/Team Trust Gap, Memory Mismatch

## 6. Input

| 입력 | V1 | 비고 |
|---|---|---|
| Local PPTX / PDF / Folder | ✅ | 원본 읽기 전용, 작업 사본은 `./.redteam/<run-id>/` |
| Word / Excel 보조자료 | ✅(텍스트만) | 인력표·일정표 교차검증용 |
| `brief.yaml` | ✅(선택) | 고객사, Mode, Win Theme 3개, 경쟁사, 발표시간. 없으면 AI 추정 + `ASSUMED` |
| HWP | ❌ | PDF 변환 후 투입 |
| Google Drive | ❌ | V2, opt-in |

## 7. Output

1. **01 Executive Red Team** — Overall Assessment → Top 5 Winning Issues → MUST FIX → SHOULD FIX → What Works Well (+ Mode 2: Memory Test, GM Storyline 요약)
2. **02 Slide-by-Slide Review** — Slide/Page · Severity · Category · Current Message · Issue · Why It Matters · Recommendation · Revised Message · Why KT · Evidence · How · Visual Recommendation · Evaluator Perspective
3. **03 RFP Compliance** (Mode 1) — Requirement · Evaluation Criteria · Proposal Response · Slide/Page · Evidence · Status · Risk · Recommendation (XLSX + MD)
4. 부속: **Evidence Ledger** (주장–근거–출처–상태)

Severity: MUST FIX / SHOULD FIX / ENHANCEMENT / PASS. 점수 없음. 오탈자는 맨 뒤 별도 섹션.
표지: Protected Facts는 수정하지 않고 `VERIFY`, 근거 없는 사실은 `[EVIDENCE REQUIRED]` 플레이스홀더.

## 8. Core Workflow

```
Input → Ingest/Normalize(Document Model) → Render → Cross-check(결정적)
     → Mode 판정 + Domain Router → Review Pass A(Storyline) / B(Section, Visual, Triangle)
     / C(RFP) / D(Red Team 반론) / E(Hygiene) → Synthesis(Top 5, Memory Test) → Report
```

## 9. V1 Scope

포함: Local 입력, Document Model, 렌더, Mode 판정, Domain Router, GM Storyline, Winning Triangle + Evidence Ledger, Blind-first Visual Test, PM Trust, Memory Test, RFP Compliance Matrix, Cross-slide Check, Financial Cross-cutting, Hygiene, 산출물 3종.

## 10. Non-goals (V1)

- PPT/Word 원본 수정, Comment 삽입, Redline/Revised 파일 생성 (V2)
- Google Drive·클라우드 동기화 (V2)
- HWP 직접 파싱 (V2)
- 점수/등급 대시보드, 웹 UI
- 제안서 자동 작성·생성 (이 제품은 **검증**한다, 쓰지 않는다)
- 규제 해석의 확정 (항상 `REGULATORY VERIFY`)
- 과거 제안서 RAG, 경쟁사 DB (V3)

### 기능 추가 판단 기준
새 기능은 **필요 이유 / V1 필요 여부 / 구현비용**을 먼저 평가하고, "판단 품질을 직접 올리는가?"에 Yes가 아니면 V2 이후로 보낸다.

## 11. Success Criteria

정성 기준 (주) — Senior 제안 전문가가 Golden Set 리뷰 결과를 보고 판정:
1. Top 5 Winning Issues 중 **3개 이상이 "실제로 고치겠다"** 판정
2. 전문가 기대 Finding의 **MUST FIX 재현율 ≥ 70%**
3. 지적 중 "어느 제안서에나 할 수 있는 일반론" 비율 **≤ 20%**
4. **허위 Evidence·허위 규제 단정 0건** (Revised Message 포함)
5. Memory Test 결과가 전문가의 "평가위원이 기억할 것" 판단과 2/3 이상 일치

정량 기준 (보조):
- 의도적으로 심은 숫자·일정·인력 불일치 **100% 검출**
- 300페이지/200MB 파일 Pipeline 완료 (Context 초과 없음)
- 원본 파일 변경 0건, 승인되지 않은 외부 전송 0건

Success Questions(10개) — 리포트가 다음에 답해야 한다: 고객의 진짜 니즈 / RFP 누락 / 제안전략 / 경쟁사 대비 차이 / 왜 KT / Evidence / How / 평가위원 눈에 보이는가 / PM·수행팀 신뢰 / 발표 후 무엇이 남는가.
