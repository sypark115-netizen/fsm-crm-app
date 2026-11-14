"""데모 계정 비밀번호를 test1234 로 일괄 초기화 (기존 DB가 있을 때).

사용: python reset_passwords.py [새비밀번호]
"""
import sys

from sqlalchemy import select

from core.database import get_session, init_db
from core.models import User
from core.security import hash_password

new_pw = sys.argv[1] if len(sys.argv) > 1 else "test1234"
init_db()
with get_session() as s:
    users = list(s.scalars(select(User)))
    for u in users:
        u.password_hash = hash_password(new_pw)
print(f"{len(users)}명 비밀번호 초기화 완료")
