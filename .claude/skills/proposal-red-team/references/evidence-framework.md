# Evidence Framework & Winning Triangle

## 1. Winning Triangle — WHY KT × EVIDENCE × HOW

세 요소가 **같은 주장에 대해** 연결되어야 강한 차별화로 인정한다.

| 요소 | 질문 | 없으면 |
|---|---|---|
| WHY KT | 경쟁사와 실제로 무엇이 다른가? | 일반론 — `DIFFERENTIATION FAILURE` |
| EVIDENCE | 실적·숫자·Reference·기술·인력·자산·운영경험으로 증명되는가? | `UNSUBSTANTIATED CLAIM` — **차별화로 인정하지 않음** |
| HOW | 그 역량을 *이번 고객*에게 구체적으로 어떻게 적용하는가? | 자랑 — Evidence가 있어도 "부족한 제안" |

판정 표 (Finding의 `triangle` 필드에 각 요소를 원문 근거와 함께 쓴다):

| WHY KT | EVIDENCE | HOW | 판정 |
|---|---|---|---|
| ✔ | ✔ | ✔ | 강한 차별화 (PASS 또는 Visual 개선만) |
| ✔ | ✔ | ✘ | SHOULD FIX — 고객 적용방법 추가 |
| ✔ | ✘ | ✔/✘ | MUST FIX (핵심 메시지인 경우) — Evidence 없는 차별화 |
| ✘ | ✔ | ✔ | SHOULD FIX — 좋은 재료가 차별화로 포장되지 않음 (GM으로 끌어올릴 것) |
| ✘ | ✘ | ✘ | 장표 목적 재검토 |

## 2. KT Capability ≠ Differentiation

"KT는 Network, Cloud, Data Center, AI 역량을 모두 보유" — 사실이어도 차별화가 아니다. 다음 사슬이 이어져야 한다:

```
KT Capability → Evidence → Customer-specific Application → Customer Impact
```

예 (차별화 후보가 되는 경우):
> Network + DC + Migration PM 통합 → (Evidence) A금융사 1,180대 이전에서 회선-서버 Dependency를 단일 Runbook으로 관리 → (Application) 한빛은행 3단계 이전의 대외계 회선 전환을 서버 이전 Runbook에 통합 → (Impact) 계획정지 10시간 대비 2시간 여유

사슬 중 끊긴 고리를 Finding에 명시한다: "Capability는 있으나 Application이 없다" 등.

## 3. Evidence 8유형

| 유형 | 예 | 강함 | 약함 |
|---|---|---|---|
| Reference | 유사 사업 실적 | 업종·규모·유형·성과·시기가 명시된 사례 | 고객사 로고 나열 |
| Scale | 운영 규모 | 이번 사업과 관련된 규모 (금융 DC 상면, 금융 회선 수) | 회사 매출·임직원 수 |
| Technical | 특허·아키텍처·성능 실측 | 고객 환경과 유사한 조건의 실측치 | "자체 기술 보유" |
| People | 전문인력 | 실명·역할·유사 경험·투입 기간 | "전문인력 OO명" |
| Process | 방법론·Runbook·체크리스트 | 이번 고객에 맞춘 절차와 Go/No-go 기준 | 표준 방법론 그림 |
| Operational | 운영 지표·장애 대응 | SLA 달성률, MTTR, 실제 장애 대응 사례 | "24x7 운영" |
| Customer | 고객 평가·재계약 | 고객 인용, 재계약·확장 이력 | 없음 |
| Asset | 보유 시설·플랫폼·인증 | 이번 사업에 쓰일 자산 + 인증 범위 | 자산 목록 |

## 4. Evidence Ledger 작성 규칙

핵심 주장(GM, 차별화·Why KT 문장, 숫자 약속)마다 한 행:

| 필드 | 규칙 |
|---|---|
| `claim` | 원문 그대로 |
| `claim_loc` | unit id |
| `type` | 8유형 중 하나, 없으면 `—` |
| `evidence` | 원문에서 찾은 근거 요약 (없으면 빈칸) |
| `evidence_loc` | 근거가 있는 unit id. **비어 있으면 report.py가 자동으로 UNSUBSTANTIATED 처리** |
| `status` | `SUPPORTED` / `WEAK`(근거는 있으나 이번 사업과 유사성·구체성 부족) / `UNSUBSTANTIATED` / `VERIFY`(근거가 있으나 사실 확인 필요) |

## 5. 절대 하지 않는 것

- 자료에 없는 실적·수치·고객명·인증을 만들어 Evidence나 Revised Message에 넣는 것. 대신:
  `[EVIDENCE REQUIRED: 금융권 DC 이전 실적 — 고객 업종, 서버 규모, 계획정지 시간]`
- 공개 정보라도 확인하지 않은 KT 실적을 "알려진 사실"로 쓰는 것. 사용자가 제공한 KT Reference 자료(있다면 `supporting` 파일)만 근거로 인정한다.
- Evidence의 숫자를 "더 강하게" 바꾸는 것 (예: 1,180대 → 1,200대 이상).
