"""최초 실행 시 데모 계정 생성. 운영 배포 전 반드시 비밀번호 변경."""
from __future__ import annotations

from sqlalchemy import select

from core.database import get_session
from core.models import Role, User
from core.security import hash_password

DEMO_USERS = [
    ("A001", "김대표", Role.ADMIN, "test1234", "경영지원", 20_000),
    ("M001", "이마케터", Role.MARKETER, "test1234", "마케팅", 13_000),
    ("W001", "박현장", Role.WORKER, "test1234", "시공1팀", 12_000),
    ("W002", "최기사", Role.WORKER, "test1234", "시공2팀", 11_500),
]


def seed_if_empty() -> None:
    with get_session() as s:
        if s.scalar(select(User.id).limit(1)) is not None:
            return
        for emp_no, name, role, pw, dept, wage in DEMO_USERS:
            s.add(User(emp_no=emp_no, name=name, role=role, password_hash=hash_password(pw),
                       department=dept, hourly_wage=wage))
