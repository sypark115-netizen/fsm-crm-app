# Scoring Rubric · Status

## Status
| Status | 기준 | 처리 | 기본 Decision |
|---|---|---|---|
| GREEN | 이미 좋은 메시지 | 유지. AI Recommended 비움 | KEEP |
| YELLOW | 의미는 좋음, 표현 개선 가능 (상투어 1~3점, 길이, 기능명 Key, 숫자는 좋은데 과장어) | 최소 수정 | (사람 선택) |
| RED | 추상적 / AI 상투어 / 고객 가치 부족 / 차별성 부족 / One Message 불명확 / Tech→Value 없음 / AX 역할 구분 없음 | 적극 수정 | (사람 선택) |
| ESCALATE | 주장의 근거(Evidence·Fact)가 없어 고치면 없는 사실을 만들게 됨 | 원문 유지 + 추가 정보 요청 | ESCALATE |

엔진 규칙(analyze_messages.assess) 순서:
1. 근거 없는 주장(차별화·역량·안정적·풍부한·최고…) + 추상 결과·기술 공백·AX 역할 공백이 아님 → **ESCALATE**
2. 상투어 심각도 ≥4 / 추상 결과(숫자·업무 근거 없음) / Tech→Value 공백 / AX 역할 공백 / One Message 실패 / Swap 실패+상투어 → **RED**
3. 상투어 1~3 / 기능명 Key / 추상어 섞인 숫자 문장 / 길이 초과 / Governing 반복 / 가치 불명 Governing → **YELLOW**
4. 그 외 → **GREEN**
Claude는 근거를 적고 Status를 바꿀 수 있다(recommendations `status`).

## 점수 (1~5, Executive Summary는 ×20)
| 항목 | 높음(5) | 낮음(1~2) |
|---|---|---|
| Customer Relevance | 고객 업무·가치가 주어 | '당사'·추상 결과 |
| Governing Message | 장표 메시지 평균 overall | |
| Key Message | Key 메시지 평균 overall | |
| Tech-to-Value | 기술 + 업무 변화 + 가치 | 기술명만 |
| Audience Fit | 독자 언어 | 경영진 장표에 약어 다수 |
| Specificity | 업무명·숫자 | 추상어 |
| Differentiation | Swap Test 통과 + 근거 | 일반론 |
| Evidence | 메시지 안 숫자 | 근거 없는 주장 |
| Story Flow | Governing 있는 장표 비율, Story Role 누락, 요구사항 GAP | |
| AI Naturalness | 상투어 없음 | 상투어 다수 |
| One Message | 한 문장 한 주장 | 절 5개 이상 |

Proposal Message Score = 가중 평균 × 20 (Governing 2, Key 1.5, Customer Relevance 1.5, Tech-to-Value 1.5, Evidence 1.2, 나머지 1).
점수는 **비교·우선순위용**이다. 사용자에게는 점수보다 "가장 중요한 문제 3~5개"를 먼저 말한다.
