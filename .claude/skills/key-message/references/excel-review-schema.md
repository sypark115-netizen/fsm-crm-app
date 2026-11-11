# Review Excel Schema (Human Approval Interface)

파일명: `<프로젝트명>_KeyMessage_Review.xlsx` — 입력 형식과 관계없이 REVIEW 결과는 Excel이다.

## 시트
1. **Executive Summary** — 고객·사업·산업/도메인·분석 자료, Proposal Message Score, 11개 진단 항목 점수(1~5, 100점 환산, 색), 제안서 핵심 진단, 가장 중요한 문제 3~5개, GREEN/YELLOW/RED/ESCALATE 수, Fact Guard ERROR/WARN 수, 검토 방법
2. **Message Map** — `message-map.md`
3. **Message Review ★** — 아래 컬럼
4. **Source Trace** — 고객 요구사항(Req ID·원문·출처·Coverage COVERED/WEAK/GAP·응답 메시지) + Evidence Inventory (자료가 있을 때만)
5. **Guide** — Status·Decision 규칙
6. `_meta` (숨김) — Unit 위치(locator), 글자 크기, 근거 숫자 목록, 도메인 → APPLY·Learning Loop에서 사용

## Message Review 컬럼
`No · Source Type · Source File · Source Location · Page / Slide · Section · Audience · Message Type(Governing/Key) · Status · Original · Problem · Customer Value · Evidence · AI Recommended · Alternative A · Alternative B · Reason · Human Final · Decision · Comment · QA Check · Category · Unit ID (수정 금지)`

- 사람이 주로 보는 칸(주황 헤더): **Original · AI Recommended · Human Final · Decision · Comment**
- 입력 칸(연노랑): Human Final · Decision · Comment
- Decision: 드롭다운(ACCEPT/EDIT/KEEP/ESCALATE). GREEN은 KEEP, ESCALATE는 ESCALATE로 미리 채움. Fact Guard ERROR 행은 비워 둠.
- EDIT인데 Human Final이 비면 빨간색으로 표시(조건부 서식).
- Freeze: 헤더 + Status 열까지 고정. Filter 전체 적용. Wrap Text, 열 너비 지정, 행 높이 자동 추정. Source Type/File 열은 Outline으로 접기 가능.
- QA Check: `Fact Guard OK|WARN|ERROR` + 세부(새 숫자, 누락 숫자, 새 고유명사) + `재진단: <Status>`(AI안을 엔진으로 다시 평가) + "⚠ RED/YELLOW인데 AI Recommended 없음".

## Decision Logic
| Decision | 반영 |
|---|---|
| ACCEPT | AI Recommended (비어 있으면 Warning, Fact Guard ERROR면 차단) |
| EDIT | Human Final (비어 있으면 Warning, 미반영) |
| KEEP | 원문 |
| ESCALATE | 원문 + 추가 Evidence 필요 |
| (빈칸) | 원문 + Warning (AUTO 모드에서만 자동 결정) |

## Learning Loop 저장 구조 (`~/.claude/key-message/learning/decisions.jsonl`, APPLY 시 기록)
`ts, project, domain, industry, audience, message_type, status, category, decision, original, ai_recommended, human_final, final, reason, comment`
분석 시 EDIT(사람이 직접 고친 문장)를 최우선, 같은 도메인을 다음으로 최대 12개를 Brief에 예시로 넣는다. `KEY_MESSAGE_HOME` 환경변수로 위치 변경. 고객 문장이 들어가므로 저장소(Git)에는 넣지 않는다.
Category: Abstract → Concrete / Tech → Value / Generic → Differentiated / AI Tone → Human Tone / Feature → Business Impact / Automation → Human/AI Role / Long → Concise / Evidence Lift / Keep
