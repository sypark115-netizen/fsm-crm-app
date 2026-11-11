# Proposal Red Team (Mode 1)

목적: RFP를 **빠짐없이, 평가받기 쉽게** 대응했는가를 검증하고 감점 Risk를 찾는다.

```
RFP → Evaluation Criteria → Requirement → KT Response → Evidence → Page → Compliance → Risk
```

## 1. 절차

1. `rfp_split.py` 결과(`rfp_requirements.md`)를 검토한다. 후보 목록이므로:
   - 같은 요구가 쪼개졌으면 병합, 서술문(요구 아님)은 삭제
   - 표·별첨·과업내용서에 있는데 빠진 요구는 `units/<RFP>/`를 직접 읽어 추가 (ID 없으면 `R-###`)
   - **제안서 작성지침**(페이지 제한, 목차 준수, 대비표 제출, 글자 크기, 발표시간)도 요구사항이다. 위반은 형식 감점·실격 사유가 될 수 있다.
2. **평가기준표**(`criteria_pages`)를 읽고 요구사항을 평가항목에 매핑한다. 배점이 큰 항목의 요구사항이 우선이다. 배점표가 없으면 그 사실을 Executive에 쓴다.
3. 요구사항마다 대응 위치를 찾는다: 핵심 키워드로 `grep -rl "<키워드>" <작업폴더>/units/<제안서 F#>/` → 해당 unit을 읽고 판정. 키워드는 RFP 표현과 제안서 표현이 다를 수 있으니 동의어도 검색 (예: 암호화/Encryption/DRM, 상주/On-site).
4. 판정 후 Compliance 행을 작성한다 (스키마는 `output-templates.md`).

## 2. Status 판정 기준

| Status | 기준 |
|---|---|
| `COMPLIANT` | 요구를 충족하는 대응이 있고, 평가항목/요구ID 기준으로 쉽게 찾을 수 있음 |
| `PARTIAL` | 일부만 대응 (예: RTO는 썼는데 RPO 없음, 수행경험 제시 요구인데 상주만 언급) |
| `HARD TO FIND` | 내용은 있으나 평가위원이 찾기 어려움 — 부록·기타 장, 다른 주제 장 속 한 줄, 목차·소제목·대비표에 없음 |
| `MISSING` | 대응 없음 |
| `CONFLICT` | 요구와 상충 (RTO 4시간 이내 요구 vs 제안 6시간) 또는 제안서 내부 상충 |

**Findability(발견용이성)** 는 Status와 별도로 `HIGH / MEDIUM / LOW`로 쓴다. 평가위원은 평가표를 들고 해당 항목 페이지를 찾는다. 다음이면 HIGH:
- 요구사항 ID나 RFP 용어가 소제목·표에 그대로 있음
- 요구사항 대비표(Compliance Matrix)에 페이지가 명시됨
- 평가항목 순서와 목차 순서가 일치함

## 3. Risk 판정

| Risk | 예 |
|---|---|
| **MUST FIX** | 필수(`mandatory`) 요구 MISSING/CONFLICT, 배점 큰 항목 PARTIAL, 작성지침 위반(페이지 초과 등), 금융규제·보안 요구 누락 |
| **SHOULD FIX** | HARD TO FIND (특히 배점 큰 항목), 선택 요구 MISSING, Evidence 없는 대응 |
| **ENHANCEMENT** | 대응은 충분하나 대비표·소제목 개선으로 점수 확보 용이 |

## 4. 제출본 전반 체크

- **목차 = 평가항목 구조?** RFP가 목차를 지정했으면 그대로 따랐는가 (불일치는 MUST FIX).
- **요구사항 대비표** 존재 여부 — 없으면 평가위원이 직접 찾아야 함 → SHOULD FIX 이상.
- **일관성**: `cross_check.json`의 숫자·일정·인력 후보 — 제출본 내부, 제출본↔발표본, 제안서↔가격/인력 별첨(Excel) 간.
- **기술적 오류**: 용어 오용, 불가능한 수치(RPO 0 + 비동기 복제 등), 구성도와 본문 불일치.
- **고객명·제품명**: 다른 고객사명(`other_customers`), 제품 버전·명칭.
- **과장 표현**: "무중단", "100%", "완벽" — 보장 의무·계약 Risk로 이어질 수 있음 → `VERIFY`.
- **위탁·하도급 구조**: 그룹사·협력사 역할과 책임이 명확한가 (금융 위탁 규정 관점은 `financial-review.md`).

## 5. 결과물

- `compliance` 배열 → `03_rfp_compliance.xlsx/.md`
- 감점 Risk가 큰 항목은 `findings`에도 올리고 Top 5 후보로 검토한다.
- Executive에 "필수 요구 N건 중 MISSING x / CONFLICT y / HARD TO FIND z"를 명시한다.
