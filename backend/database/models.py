from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text, ForeignKey

from backend.database.db import Base


def time_now() -> datetime:
    return datetime.now(timezone.utc)

# Stores file metadata, not the actual file content
class FileRecord(Base): 
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    original_name: Mapped[str] = mapped_column(
        String(255),
        nullable = False
    )

    stored_name: Mapped[str] = mapped_column(
        String(255),
        nullable = False,
        unique = True
    )   

    extension : Mapped[str] = mapped_column(
        String(20),
        nullable = False
    )

    category : Mapped[str] = mapped_column(
        String(20),
        nullable = False
    )

    size_bytes : Mapped[int] = mapped_column(
        Integer,
        nullable = False
    )

    storage_path : Mapped[str] = mapped_column(
        String(500),
        nullable = False,
        unique = True
    )

    status : Mapped[str] = mapped_column(
        String(30),
        default = "uploaded"
    )

    created_at : Mapped[datetime] = mapped_column(
        default = time_now
    )

    updated_at: Mapped[datetime] = mapped_column(
        default = time_now,
        onupdate = time_now
    )

    analysis_jobs: Mapped[list["AnalysisJob"]] = relationship(
        back_populates="file",
        passive_deletes=True,
    )

    reports: Mapped[list["Report"]] = relationship(
        back_populates="file",
        passive_deletes=True,
    )


# Stores every time the user analyzes a CSV file.
class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

     
    file_id: Mapped[int] = mapped_column(
        ForeignKey(
            "files.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
 
    status: Mapped[str] = mapped_column(
        String(30),
        default = "pending"
    ) 

    requested_options: Mapped[str | None] = mapped_column(
        Text,
        nullable = True 
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable = True 
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable = True 
    )

    created_at : Mapped[datetime] = mapped_column(
        default = time_now
    )
    
    completed_at: Mapped[datetime | None] = mapped_column(
        default = None
    ) 

    file: Mapped["FileRecord"] = relationship(
        back_populates="analysis_jobs",
    )

# Stores information about generated reports
class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    file_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "files.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    report_type: Mapped[str] = mapped_column(
        String(30),
        nullable = False   
    )

    storage_path : Mapped[str] = mapped_column(
        String(500),
        nullable = False,
        unique = True
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default = "pending"
    )

    created_at : Mapped[datetime] = mapped_column(
        default = time_now
    )

    file: Mapped["FileRecord"] = relationship(
        back_populates="reports",
    )

# Stores important application actions permanently in the database.
class AutomationLog(Base):
    __tablename__ = "automation_logs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    target: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        default=time_now
    )


# Stores non-secret application settings.
class AppSetting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True
    )

    value: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    updated_at: Mapped[datetime] = mapped_column(
        default=time_now,
        onupdate=time_now
    )


# Stores metadata about trained ML models, not the model file itself.
class MLModelRecord(Base):
    __tablename__ = "ml_models"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    model_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    feature_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    target_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    metrics: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    storage_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        default=time_now
    )






    







