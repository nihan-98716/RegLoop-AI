"""Workspace and Document ORM models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Forward-declare coverage/risk literals for documentation clarity
# fully_covered | partially_covered | not_covered
# high | medium | low


def generate_uuid() -> str:
    """Generate a random UUID string."""
    return str(uuid.uuid4())


class Workspace(Base):
    """A compliance review workspace containing all uploaded documents."""

    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
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
    policy_pull_requests: Mapped[list["PolicyPullRequest"]] = relationship(
        "PolicyPullRequest",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="select",
    )


class Document(Base):
    """An uploaded file associated with a workspace."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
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
    policy_mappings: Mapped[list["PolicyMapping"]] = relationship(
        "PolicyMapping",
        back_populates="policy_document",
        foreign_keys="PolicyMapping.policy_document_id",
        lazy="select",
    )


class DocumentChunk(Base):
    """Normalized extracted text from a PDF document."""

    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
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
    policy_mappings: Mapped[list["PolicyMapping"]] = relationship(
        "PolicyMapping",
        back_populates="policy_chunk",
        foreign_keys="PolicyMapping.document_chunk_id",
        lazy="select",
    )


class ResponsibilityOwner(Base):
    """Parsed owner row from the uploaded responsibility matrix."""

    __tablename__ = "responsibility_owners"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
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


class PolicyMapping(Base):
    """Maps a single obligation to a matching policy chunk or records a no-match."""

    __tablename__ = "policy_mappings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    obligation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("obligations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_document_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_chunk_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    policy_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    mapping_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    is_no_match: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    obligation: Mapped["Obligation"] = relationship(
        "Obligation", back_populates="policy_mappings"
    )
    policy_document: Mapped["Document | None"] = relationship(
        "Document", back_populates="policy_mappings", foreign_keys=[policy_document_id]
    )
    policy_chunk: Mapped["DocumentChunk | None"] = relationship(
        "DocumentChunk", back_populates="policy_mappings", foreign_keys=[document_chunk_id]
    )
    gap_analyses: Mapped[list["GapAnalysis"]] = relationship(
        "GapAnalysis",
        back_populates="policy_mapping",
        foreign_keys="GapAnalysis.policy_mapping_id",
        lazy="select",
    )


class Obligation(Base):
    """Structured regulatory obligation extracted from the regulation."""

    __tablename__ = "obligations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
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
    policy_mappings: Mapped[list["PolicyMapping"]] = relationship(
        "PolicyMapping",
        back_populates="obligation",
        cascade="all, delete-orphan",
        lazy="select",
    )
    gap_analyses: Mapped[list["GapAnalysis"]] = relationship(
        "GapAnalysis",
        back_populates="obligation",
        cascade="all, delete-orphan",
        lazy="select",
    )
    policy_pull_requests: Mapped[list["PolicyPullRequest"]] = relationship(
        "PolicyPullRequest",
        back_populates="obligation",
        cascade="all, delete-orphan",
        lazy="select",
    )


class GapAnalysis(Base):
    """Coverage assessment for a single regulatory obligation."""

    __tablename__ = "gap_analyses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    obligation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("obligations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_mapping_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("policy_mappings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # fully_covered | partially_covered | not_covered
    coverage_status: Mapped[str] = mapped_column(String(50), nullable=False)
    # high | medium | low
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    source_citations: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    obligation: Mapped["Obligation"] = relationship(
        "Obligation", back_populates="gap_analyses"
    )
    policy_mapping: Mapped["PolicyMapping | None"] = relationship(
        "PolicyMapping", back_populates="gap_analyses", foreign_keys=[policy_mapping_id]
    )
    policy_pull_requests: Mapped[list["PolicyPullRequest"]] = relationship(
        "PolicyPullRequest",
        back_populates="gap_analysis",
        cascade="all, delete-orphan",
        lazy="select",
    )


class PolicyPullRequest(Base):
    """Reviewable AI-generated policy amendment."""

    __tablename__ = "policy_pull_requests"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    obligation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("obligations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gap_analysis_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("gap_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    gap_description: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_amendment: Mapped[str] = mapped_column(Text, nullable=False)
    regulatory_citation: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_owner_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("responsibility_owners.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    before_text: Mapped[str] = mapped_column(Text, nullable=False)
    after_text: Mapped[str] = mapped_column(Text, nullable=False)
    # pending | approved | rejected | modified | escalated
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    workspace: Mapped["Workspace"] = relationship(
        "Workspace", back_populates="policy_pull_requests"
    )
    obligation: Mapped["Obligation"] = relationship(
        "Obligation", back_populates="policy_pull_requests"
    )
    gap_analysis: Mapped["GapAnalysis"] = relationship(
        "GapAnalysis", back_populates="policy_pull_requests"
    )
    suggested_owner: Mapped["ResponsibilityOwner | None"] = relationship(
        "ResponsibilityOwner"
    )
    review_actions: Mapped[list["ReviewAction"]] = relationship(
        "ReviewAction",
        back_populates="policy_pull_request",
        cascade="all, delete-orphan",
        lazy="select",
    )


class ReviewAction(Base):
    """Human review action taken on a policy pull request."""

    __tablename__ = "review_actions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=generate_uuid
    )
    policy_pull_request_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("policy_pull_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # approve | reject | modify | escalate
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    reviewer_label: Mapped[str] = mapped_column(String(255), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    modified_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    policy_pull_request: Mapped["PolicyPullRequest"] = relationship(
        "PolicyPullRequest", back_populates="review_actions"
    )
