"""Workspace and Document ORM models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Workspace(Base):
    """A compliance review workspace containing all uploaded documents."""

    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="select",
    )
    responsibility_owners: Mapped[list["ResponsibilityOwner"]] = relationship(
        "ResponsibilityOwner",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="select",
    )
    obligations: Mapped[list["Obligation"]] = relationship(
        "Obligation",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="select",
    )


class Document(Base):
    """An uploaded file associated with a workspace."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # regulation | policy | responsibility_matrix
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    workspace: Mapped["Workspace"] = relationship(
        "Workspace", back_populates="documents"
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="select",
    )
    obligations: Mapped[list["Obligation"]] = relationship(
        "Obligation",
        back_populates="source_document",
        cascade="all, delete-orphan",
        lazy="select",
    )


class DocumentChunk(Base):
    """Normalized extracted text from a PDF document."""

    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    document: Mapped["Document"] = relationship(
        "Document", back_populates="chunks"
    )


class ResponsibilityOwner(Base):
    """Parsed owner row from the uploaded responsibility matrix."""

    __tablename__ = "responsibility_owners"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    policy_area: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    workspace: Mapped["Workspace"] = relationship(
        "Workspace", back_populates="responsibility_owners"
    )


class Obligation(Base):
    """Structured regulatory obligation extracted from the regulation."""

    __tablename__ = "obligations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    source_document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    source_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    compliance_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    workspace: Mapped["Workspace"] = relationship(
        "Workspace", back_populates="obligations"
    )
    source_document: Mapped["Document"] = relationship(
        "Document", back_populates="obligations"
    )
