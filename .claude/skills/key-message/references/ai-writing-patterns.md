# AI스러운 문체 · 제안서 상투어

사전은 `scripts/km_common.py > AI_PATTERNS` 한 곳에서 관리한다 (id, 정규식, 범주, 심각도 1~3, 힌트).
**단어 자체를 지우는 규칙이 아니다.** 탐지 대상은 추상성·과장·상투성·반복·번역투·기계적 문장·근거 없는 형용사다. 문맥상 필요하면 유지한다.

| 범주 | 예 | 처리 |
|---|---|---|
| 번역투 | ~를 통해, ~에 있어서, 이를 통해, 기반으로 | "~로", 동사 문장으로 |
| 접속사 남발 | 또한, 나아가, 아울러 | 지우고 결론부터 |
| 추상 부사·명사 | 효과적으로, 체계적으로, 고도화, 가속화 | 무엇이 어떻게 바뀌는지 |
| 과장 | 극대화, 획기적, 선도적, 혁신적인 | 근거 수치 또는 삭제 |
| 근거 없는 형용사 | 차별화된, 최적의, 풍부한, 최고의, 우수한 | Evidence 또는 ESCALATE |
| 버즈워드 | 지능형, Intelligent, End-to-End, Seamless | AI가 실제 하는 일 |
| 상투 결론 | 중요한 역할을 합니다, 기여할 수 있습니다, ~할 수 있습니다 | 단정형(근거 있을 때) |
| 자기중심 | 당사의, 당사는 | 고객을 주어로 |
| 추상 결과 | 디지털 혁신, 가치 창출, 패러다임, 초석 마련 | 구체 업무 변화 |

심각도 합계가 4 이상이거나 추상 결과만 있으면 RED 신호. 1~3이면 YELLOW 신호(최소 수정).

## 우선순위
이 규칙은 우선순위 12번째다. Governing·Tech-to-Value·Fact Guard 판단이 먼저다. **AI 탐지 회피 자체를 목표로 고치지 않는다.**

## 참고한 오픈소스 (개념만 참고, 코드·패턴 목록 복사 없음 — 2026-11 확인, 모두 MIT)
- epoko77-ai/im-not-ai (Humanize KR) — 번역투·AI 관용구 분류 체계, 심각도 개념
- CY-HYUN/korean-ai-tell — 규칙 ID + 수정 힌트 구조
- evergreentree97/K-Humanizer — 숫자·가격·날짜를 정확히 지키는 원칙
- devjun7/LUDDITE_KR — 사람이 이해하기 쉬운 문체 원칙
여러 Humanizer를 순차 실행하지 않는다. 이 Skill의 판단 순서는 IT·AX 제안 Logic → Governing/Key → Tech-to-Value → Customer/Audience → Fact & Evidence → Business Writing → AI 패턴이다.
