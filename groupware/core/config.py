"""전역 설정. 운영 시에는 환경변수로 덮어쓴다."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("GW_DATA_DIR", BASE_DIR / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
PORTFOLIO_DIR = DATA_DIR / "portfolio"
BLOG_DIR = DATA_DIR / "blog"
DOCUMENT_DIR = DATA_DIR / "documents"
EXPORT_DIR = DATA_DIR / "exports"

for _d in (DATA_DIR, UPLOAD_DIR, PORTFOLIO_DIR, BLOG_DIR, DOCUMENT_DIR, EXPORT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("GW_DATABASE_URL", f"sqlite:///{DATA_DIR / 'groupware.db'}")


@dataclass(frozen=True)
class Site:
    """출퇴근 인정 기준 좌표(회사/공장/현장)."""
    name: str
    lat: float
    lng: float
    radius_m: float = 150.0


# 기준 좌표 — 실제 회사 좌표로 교체
SITES: list[Site] = [
    Site("본사", float(os.getenv("GW_HQ_LAT", "37.5665")), float(os.getenv("GW_HQ_LNG", "126.9780"))),
]

# 급여 규칙 (근로기준법 기본값)
REGULAR_HOURS_PER_DAY = 8.0
OVERTIME_MULTIPLIER = 1.5
DEFAULT_HOURLY_WAGE = 10_320  # 2026년 최저시급, 회사 기준으로 조정

# 개발 편의: GPS 미지원 환경(HTTP, PC)에서 좌표 수동 입력 허용
ALLOW_MANUAL_GPS = os.getenv("GW_ALLOW_MANUAL_GPS", "1") == "1"

# 홈택스 RPA: 기본 mock. 실제 실행은 GW_HOMETAX_MODE=live
HOMETAX_MODE = os.getenv("GW_HOMETAX_MODE", "mock")
HOMETAX_CERT_PASSWORD_ENV = "GW_HOMETAX_CERT_PASSWORD"  # 비밀번호는 env로만 주입

PHOTO_TAGS = ["철거", "목공", "전기", "설비", "도장", "타일", "마감", "완공", "하자보수"]
