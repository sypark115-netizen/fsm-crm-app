"""홈택스/인터넷등기소 증명서 자동 발급 RPA (Playwright).

⚠ 현실적 제약 (운영 전 반드시 확인)
1. 홈택스 공동인증서 로그인은 보안 모듈(AnySign4PC 등) 설치가 필요한 경우가 많아
   **headless 리눅스 서버에서는 실패할 수 있다.** 인증서가 설치된 사무실 Windows PC에서
   headful(브라우저 표시) 모드로 실행하는 것을 1차 목표로 잡는다.
2. 법인인감증명서는 홈택스가 아니라 **대법원 인터넷등기소(iros.go.kr)** 발급 대상이며,
   온라인 발급 범위(열람/발급 가능 여부)가 제한적이다 → 별도 플로우로 분리.
3. 사이트 DOM은 수시로 바뀌므로 SELECTORS 를 한 곳에 모아 두고 실패 시 스크린샷을 남긴다.
4. 인증서 비밀번호는 코드/DB에 저장하지 않고 환경변수(GW_HOMETAX_CERT_PASSWORD)로만 주입한다.

기본은 HOMETAX_MODE=mock — 실제 사이트에 접속하지 않고 흐름/UI를 검증하는 샘플 PDF를 만든다.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw

from core.config import DOCUMENT_DIR, HOMETAX_CERT_PASSWORD_ENV, HOMETAX_MODE
from core.database import get_session
from core.models import Document, DocStatus, DocType

ProgressFn = Callable[[str], None]


@dataclass(frozen=True)
class DocSpec:
    label: str
    portal: str        # hometax | iros
    menu_path: tuple[str, ...]  # 메뉴 클릭 경로 (사람이 읽는 용도 + selector 키)


DOC_SPECS: dict[DocType, DocSpec] = {
    DocType.VAT_STANDARD: DocSpec("부가가치세 과세표준증명", "hometax", ("민원증명", "부가가치세 과세표준증명")),
    DocType.FINANCIAL_STATEMENT: DocSpec("표준재무제표증명", "hometax", ("민원증명", "표준재무제표증명")),
    DocType.BIZ_REGISTRATION: DocSpec("사업자등록증명", "hometax", ("민원증명", "사업자등록증명")),
    DocType.CORP_SEAL: DocSpec("법인인감증명서", "iros", ("법인", "인감증명서")),
}

HOMETAX_URL = "https://www.hometax.go.kr"
IROS_URL = "https://www.iros.go.kr"

# TODO: 실제 DOM 확인 후 채우기 (개발자도구 → Copy selector). 값이 None 이면 live 모드에서 즉시 중단.
SELECTORS: dict[str, str | None] = {
    "login_button": None,
    "cert_login_tab": None,
    "cert_password_input": None,
    "cert_confirm": None,
    "menu:민원증명": None,
    "menu:부가가치세 과세표준증명": None,
    "menu:표준재무제표증명": None,
    "menu:사업자등록증명": None,
    "issue_button": None,
    "print_or_pdf": None,
}


class RpaError(Exception):
    pass


def _record(doc_type: DocType, user_id: int) -> int:
    with get_session() as s:
        d = Document(doc_type=doc_type, status=DocStatus.RUNNING, requested_by=user_id)
        s.add(d)
        s.flush()
        return d.id


def _finish(doc_id: int, path: Path | None, error: str | None = None) -> None:
    with get_session() as s:
        d = s.get(Document, doc_id)
        d.status = DocStatus.DONE if error is None else DocStatus.FAILED
        d.file_path = str(path) if path else None
        d.error, d.finished_at = error, datetime.now()


def issue(doc_type: DocType, user_id: int, progress: ProgressFn = lambda _m: None) -> Path:
    doc_id = _record(doc_type, user_id)
    try:
        runner = _issue_mock if HOMETAX_MODE != "live" else _issue_live
        path = runner(doc_type, progress)
        _finish(doc_id, path)
        return path
    except Exception as e:  # noqa: BLE001 - 이력에 남기고 UI로 다시 던짐
        _finish(doc_id, None, f"{type(e).__name__}: {e}")
        raise


# ─────────────────────────── mock ───────────────────────────
def _issue_mock(doc_type: DocType, progress: ProgressFn) -> Path:
    spec = DOC_SPECS[doc_type]
    for step in ("홈택스 접속", "공동인증서 로그인", " > ".join(spec.menu_path) + " 메뉴 이동", "발급 및 PDF 저장"):
        progress(f"[MOCK] {step}…")
        time.sleep(0.4)
    out = DOCUMENT_DIR / f"{doc_type.value}_{datetime.now():%Y%m%d_%H%M%S}_MOCK.pdf"
    img = Image.new("RGB", (1240, 1754), "white")  # A4 @150dpi
    d = ImageDraw.Draw(img)
    d.text((80, 80), "MOCK DOCUMENT - NOT VALID", fill="red")
    d.text((80, 140), f"type: {doc_type.value}", fill="black")
    d.text((80, 180), f"generated: {datetime.now():%Y-%m-%d %H:%M:%S}", fill="black")
    d.text((80, 220), "Set GW_HOMETAX_MODE=live to run the real Playwright flow.", fill="black")
    img.save(out, "PDF", resolution=150)
    return out


# ─────────────────────────── live ───────────────────────────
def _sel(key: str) -> str:
    sel = SELECTORS.get(key)
    if not sel:
        raise RpaError(f"SELECTORS['{key}'] 미설정 — 실제 DOM 확인 후 services/hometax_rpa.py 를 채워주세요.")
    return sel


def _issue_live(doc_type: DocType, progress: ProgressFn) -> Path:
    from playwright.sync_api import TimeoutError as PwTimeout, sync_playwright  # 지연 import

    spec = DOC_SPECS[doc_type]
    if spec.portal == "iros":
        raise RpaError("법인인감증명서(인터넷등기소) 플로우는 아직 구현되지 않았습니다.")
    password = os.getenv(HOMETAX_CERT_PASSWORD_ENV)
    if not password:
        raise RpaError(f"환경변수 {HOMETAX_CERT_PASSWORD_ENV} 가 없습니다.")

    out = DOCUMENT_DIR / f"{doc_type.value}_{datetime.now():%Y%m%d_%H%M%S}.pdf"
    headless = os.getenv("GW_HOMETAX_HEADLESS", "0") == "1"  # 기본 headful: 인증서 보안모듈 호환
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        ctx = browser.new_context(accept_downloads=True, locale="ko-KR")
        page = ctx.new_page()
        try:
            progress("홈택스 접속…")
            page.goto(HOMETAX_URL, wait_until="domcontentloaded", timeout=30_000)

            progress("공동인증서 로그인…")
            page.click(_sel("login_button"))
            page.click(_sel("cert_login_tab"))
            # TODO: 인증서 선택(저장위치: 하드디스크/이동식) 단계 — 환경마다 다름
            page.fill(_sel("cert_password_input"), password)
            page.click(_sel("cert_confirm"))
            page.wait_for_load_state("networkidle", timeout=30_000)

            for menu in spec.menu_path:
                progress(f"메뉴 이동: {menu}")
                page.click(_sel(f"menu:{menu}"))

            progress("발급 요청…")
            page.click(_sel("issue_button"))
            with page.expect_download(timeout=60_000) as dl:
                page.click(_sel("print_or_pdf"))
            dl.value.save_as(out)
            # 대안: 다운로드가 아닌 인쇄 미리보기라면 headless 에서 page.pdf(path=out) 사용
            return out
        except PwTimeout as e:
            shot = out.with_suffix(".fail.png")
            page.screenshot(path=str(shot), full_page=True)
            raise RpaError(f"시간 초과 — 스크린샷: {shot.name}") from e
        finally:
            ctx.close()
            browser.close()


def history(limit: int = 30) -> list[Document]:
    from sqlalchemy import select
    with get_session() as s:
        return list(s.scalars(select(Document).order_by(Document.requested_at.desc()).limit(limit)))
