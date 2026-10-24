"""Các enum nghiệp vụ (giá trị lưu trong CSDL là chuỗi tiếng Anh viết hoa)."""

from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    MANAGER = "MANAGER"
    MARKETER = "MARKETER"


class CampaignGoal(StrEnum):
    AWARENESS = "AWARENESS"
    TRAFFIC = "TRAFFIC"
    LEADS = "LEADS"
    SALES = "SALES"


class CampaignStatus(StrEnum):
    PLANNED = "PLANNED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ContentType(StrEnum):
    SOCIAL_POST = "SOCIAL_POST"
    EMAIL = "EMAIL"
    AD_COPY = "AD_COPY"
    VIDEO_SCRIPT = "VIDEO_SCRIPT"
    OTHER = "OTHER"


class ContentStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PUBLISHED = "PUBLISHED"


class ContentOrigin(StrEnum):
    MANUAL = "MANUAL"
    AI = "AI"


class ReviewDecision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ScheduleStatus(StrEnum):
    PLANNED = "PLANNED"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class MetricSource(StrEnum):
    MANUAL = "MANUAL"
    CSV = "CSV"
    SEED = "SEED"


class AiMessageRole(StrEnum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"


class AiMessageStatus(StrEnum):
    STREAMING = "STREAMING"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"
    STOPPED = "STOPPED"


class AiActionStatus(StrEnum):
    PROPOSED = "PROPOSED"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
