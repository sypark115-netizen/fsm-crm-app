"""DB 스키마.

users ─┬─ attendance        (GPS 출퇴근 타임스탬프)
       ├─ work_requests     (연장근로/연차 전자결재)
       ├─ photos ── portfolio_items  (현장사진 → 외부 시공사례)
       └─ documents         (홈택스 RPA 발급 증명서)
blog_posts                   (포트폴리오 자동 발행 초안)
"""
from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Role(str, enum.Enum):
    ADMIN = "admin"        # 대표/관리자/경영진
    WORKER = "worker"      # 현장 작업자/일반 직원
    MARKETER = "marketer"  # 마케터


class RequestType(str, enum.Enum):
    OVERTIME = "overtime"   # 연장근로
    ANNUAL = "annual"       # 연차
    HALF_DAY = "half_day"   # 반차


class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class DocType(str, enum.Enum):
    VAT_STANDARD = "vat_standard"            # 부가가치세 과세표준증명
    FINANCIAL_STATEMENT = "financial_stmt"   # 표준재무제표증명
    BIZ_REGISTRATION = "biz_registration"    # 사업자등록증명
    CORP_SEAL = "corp_seal"                  # 법인인감증명서 (인터넷등기소)


class DocStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    emp_no: Mapped[str] = mapped_column(String(20), unique=True, index=True)  # 사원번호
    name: Mapped[str] = mapped_column(String(50))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.WORKER)
    password_hash: Mapped[str] = mapped_column(String(200))
    department: Mapped[str | None] = mapped_column(String(50))
    hourly_wage: Mapped[int] = mapped_column(Integer, default=10_320)
    annual_leave_days: Mapped[float] = mapped_column(Float, default=15.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    attendance: Mapped[list["Attendance"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    requests: Mapped[list["WorkRequest"]] = relationship(
        back_populates="user", foreign_keys="WorkRequest.user_id", cascade="all, delete-orphan"
    )
    photos: Mapped[list["Photo"]] = relationship(back_populates="uploader")


class Attendance(Base):
    """하루 1행. 출근/퇴근 각각 좌표와 기준지점 거리 기록(감사 추적용)."""
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("user_id", "work_date", name="uq_attendance_user_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    work_date: Mapped[date] = mapped_column(Date, index=True)
    check_in: Mapped[datetime | None] = mapped_column(DateTime)
    check_out: Mapped[datetime | None] = mapped_column(DateTime)
    in_lat: Mapped[float | None] = mapped_column(Float)
    in_lng: Mapped[float | None] = mapped_column(Float)
    out_lat: Mapped[float | None] = mapped_column(Float)
    out_lng: Mapped[float | None] = mapped_column(Float)
    site_name: Mapped[str | None] = mapped_column(String(100))
    in_distance_m: Mapped[float | None] = mapped_column(Float)
    out_distance_m: Mapped[float | None] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(String(200))

    user: Mapped[User] = relationship(back_populates="attendance")


class WorkRequest(Base):
    """연장근로/연차 전자결재."""
    __tablename__ = "work_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[RequestType] = mapped_column(Enum(RequestType))
    target_date: Mapped[date] = mapped_column(Date, index=True)
    hours: Mapped[float] = mapped_column(Float, default=0.0)   # 연장근로 시간 (연차는 0)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[RequestStatus] = mapped_column(Enum(RequestStatus), default=RequestStatus.PENDING, index=True)
    approver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime)
    reject_reason: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="requests", foreign_keys=[user_id])
    approver: Mapped[User | None] = relationship(foreign_keys=[approver_id])


class Photo(Base):
    """현장 시공 사진. is_public = 마케터의 '외부 노출용 파란 체크'."""
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    uploader_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    site_name: Mapped[str] = mapped_column(String(100), index=True)
    tags: Mapped[str] = mapped_column(String(200), default="")  # 콤마 구분
    file_path: Mapped[str] = mapped_column(String(300))
    thumb_path: Mapped[str] = mapped_column(String(300))
    original_name: Mapped[str] = mapped_column(String(200))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    uploader: Mapped[User] = relationship(back_populates="photos")

    @property
    def tag_list(self) -> list[str]:
        return [t for t in self.tags.split(",") if t]


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    site_name: Mapped[str] = mapped_column(String(100))
    markdown: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str] = mapped_column(String(300))
    channel: Mapped[str] = mapped_column(String(50), default="local")  # local / naver / wordpress ...
    external_url: Mapped[str | None] = mapped_column(String(300))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    items: Mapped[list["PortfolioItem"]] = relationship(back_populates="post")


class PortfolioItem(Base):
    """외부 랜딩페이지 '시공 사례' 갤러리 DB. 랜딩페이지는 이 테이블(또는 JSON export)만 읽는다."""
    __tablename__ = "portfolio_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    photo_id: Mapped[int] = mapped_column(ForeignKey("photos.id"), unique=True)
    post_id: Mapped[int | None] = mapped_column(ForeignKey("blog_posts.id"))
    site_name: Mapped[str] = mapped_column(String(100), index=True)
    tags: Mapped[str] = mapped_column(String(200), default="")
    public_path: Mapped[str] = mapped_column(String(300))
    caption: Mapped[str | None] = mapped_column(String(300))
    published_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    photo: Mapped[Photo] = relationship()
    post: Mapped[BlogPost | None] = relationship(back_populates="items")


class Document(Base):
    """홈택스 RPA 발급 이력."""
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_type: Mapped[DocType] = mapped_column(Enum(DocType))
    status: Mapped[DocStatus] = mapped_column(Enum(DocStatus), default=DocStatus.QUEUED)
    file_path: Mapped[str | None] = mapped_column(String(300))
    error: Mapped[str | None] = mapped_column(Text)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    requested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
