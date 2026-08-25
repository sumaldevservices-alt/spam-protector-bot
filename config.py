import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Bot
    BOT_TOKEN: str = Field(..., description="Telegram Bot Token")
    SUPER_ADMIN_IDS: List[int] = Field(default=[], description="Super admin user IDs")

    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL async connection URL")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379", description="Redis connection URL")

    # Webhook
    WEBHOOK_URL: str = Field(default="", description="Webhook URL for production")
    WEBHOOK_PORT: int = Field(default=8080, description="Webhook port")

    # UPI Payment
    UPI_ID: str = Field(default="akash-sumal@fam", description="UPI ID for payments")
    QR_CODE_URL: str = Field(default="https://files.catbox.moe/rf1q6n.jpg", description="QR code image URL")

    # Free Trial
    FREE_TRIAL_DAYS: int = Field(default=3, description="Free trial duration in days")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()