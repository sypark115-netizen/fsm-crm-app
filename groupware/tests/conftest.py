import os
import sys
import tempfile
from pathlib import Path

# 모듈 import 전에 격리된 데이터 디렉터리/DB 지정
_tmp = tempfile.mkdtemp(prefix="gw_test_")
os.environ["GW_DATA_DIR"] = _tmp
os.environ["GW_DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["GW_HOMETAX_MODE"] = "mock"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

from core.database import Base, engine, init_db  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    init_db()
    yield
