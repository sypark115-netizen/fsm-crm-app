# 현장 그룹웨어 (Streamlit)

소규모 시공·제조·서비스 기업용 초경량 사내 그룹웨어 + 업무 자동화.
기존 Next.js FSM 앱과 독립된 Python 서브프로젝트입니다.

## 실행

```bash
cd groupware
pip install -r requirements.txt
playwright install chromium        # 홈택스 RPA live 모드에서만 필요
streamlit run app.py
```

데모 계정 (최초 실행 시 자동 생성 — 운영 전 반드시 변경)

비밀번호는 모두 `test1234`

| 역할 | 사번 |
|---|---|
| 관리자(admin) | A001 |
| 마케터(marketer) | M001 |
| 작업자(worker) | W001 / W002 |

이미 `data/` 폴더가 있는 상태에서 비밀번호를 초기화하려면 `python reset_passwords.py` 실행.

## 구조

```
app.py                     진입점: 로그인 + 권한별 st.navigation 분기
core/
  config.py                기준좌표·반경, 급여규칙, 경로, 모드 플래그 (env 로 덮어쓰기)
  models.py                users / attendance / work_requests / photos / portfolio_items / blog_posts / documents
  database.py, seed.py     SQLAlchemy 엔진·세션, 데모 시드
  auth.py, security.py     PBKDF2 해시, session_state 로그인, require_role()
  ui.py                    모바일 반응형 CSS, 작업자 빠른 이동
services/                  (UI 비의존 — 테스트 대상)
  geofence.py              하버사인 거리, 반경 판정
  attendance.py            출퇴근 (서버측 반경 재검증)
  approvals.py             연장근로/연차 전자결재
  payroll.py               근태 × 승인연장 자동 대조 → 급여대장 / 엑셀
  photos.py                업로드 리사이즈·EXIF 회전보정·썸네일
  publishing.py            노출 체크 → 포트폴리오 DB + 마크다운 블로그 + portfolio.json
  image_studio.py          전후 비교 / 3컷 공정 스토리 / 자동 보정 / 워터마크
  hometax_rpa.py           Playwright 증명서 발급 (기본 mock)
views/worker|admin|marketing/  화면
tests/                     pytest (서비스 레이어)
```

## 권한 설계
- 메뉴 노출: 역할별로 `st.navigation` 에 **등록하는 페이지 자체를 다르게** 함 → 작업자 세션에는 급여 페이지 URL이 존재하지 않음.
- 2중 차단: 모든 페이지 첫 줄 `require_role(...)`.

## 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `GW_DATA_DIR` | `./data` | DB·업로드·발행물 저장 위치 |
| `GW_HQ_LAT`, `GW_HQ_LNG` | 종로 1 (37.5710, 126.9780) | 출퇴근 기준 좌표 (반경 150m) |
| `GW_ALLOW_MANUAL_GPS` | `1` | 개발용 좌표 수동 입력 (운영은 `0`) |
| `GW_HOMETAX_MODE` | `mock` | `live` 시 실제 Playwright 실행 |
| `GW_HOMETAX_CERT_PASSWORD` | – | 공동인증서 비밀번호 (코드/DB 저장 금지) |
| `GW_HOMETAX_HEADLESS` | `0` | 인증서 보안모듈 호환 위해 기본 headful |

## 운영 전 확인할 것
1. **GPS는 HTTPS에서만 동작** (모바일 브라우저 정책). 리버스 프록시(Caddy/Nginx)로 TLS 적용.
2. **새로고침 시 로그인 해제** — Streamlit 세션은 WebSocket 단위. 현장 편의를 위해 OIDC(`st.login`)나 쿠키 기반 토큰 도입 권장.
3. **홈택스 RPA**: `services/hometax_rpa.py` 의 `SELECTORS` 가 비어 있음 → 실제 DOM 확인 후 채워야 live 동작. 공동인증서 보안모듈 때문에 리눅스 headless 서버보다 **인증서가 설치된 사무실 Windows PC**에서 실행하는 구성이 현실적. 법인인감증명서는 홈택스가 아닌 인터넷등기소 소관이라 별도 플로우(미구현).
4. **급여**: 기본급·연장수당(1.5배)만 산출. 주휴수당, 야간(22~06시)·휴일 가산, 4대보험/원천세 공제는 TODO.
5. **블로그 퍼블리싱**: 현재 `LocalPublisher`(마크다운 파일 + `portfolio.json`). 네이버/워드프레스 등은 `Publisher` 프로토콜 구현으로 확장.
6. SQLite는 WAL 모드로 소규모 동시 사용(수십 명)까지 무난. 그 이상은 `GW_DATABASE_URL` 로 PostgreSQL 전환.

## 테스트
```bash
cd groupware && python -m pytest -q
```
