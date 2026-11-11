# Message Map

Message Map 시트는 장표 순서대로 Governing Message만 모은 **Story 검증표**다.

| 컬럼 | 내용 |
|---|---|
| Page / Slide / Source Location | `Proposal.pptx p5` |
| Section | 직전 간지 제목 (예: 02 제안 전략) |
| Audience | 장표 주 독자 → `audience-rules.md` |
| Role | Why / What / Why Us / How / Evidence / Value |
| Original Governing Message | 원문 (없으면 "(Governing 없음) 제목: …") |
| Recommended Governing Message | RED·YELLOW는 AI 추천안, GREEN·ESCALATE는 원문 |
| Customer Value | 이 장표로 고객이 얻는 것 |
| Story Connection | `이전 Role → [이번 Role] → 다음 Role` + 연결된 고객 요구사항 ID |
| Evidence | 장표 내·연결 자료의 근거 |
| Status | GREEN / YELLOW / RED / ESCALATE |

## 읽는 법
1. Recommended Governing만 위에서 아래로 소리 내어 읽는다. 1분 안에 "왜 이 사업을, 왜 우리에게, 어떻게, 무엇이 남는가"가 들려야 한다.
2. Role이 Why에서 바로 How로 건너뛰거나, Value 장표가 없으면 `analysis.json > story.missing_roles`에 나온다 → 핵심 진단에 적는다.
3. Governing 없는 장표는 그 자체로 RED다. 제목만 있는 장표에는 한 문장을 추가하라고 권고한다(내용은 장표 본문에서만).
4. Source Trace 시트의 GAP(메시지로 응답하지 않은 고객 요구사항)를 Story Connection과 함께 본다.
