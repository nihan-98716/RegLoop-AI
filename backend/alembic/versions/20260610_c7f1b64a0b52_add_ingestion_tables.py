"""add_ingestion_tables

Revision ID: c7f1b64a0b52
Revises: b2484524073e
Create Date: 2026-06-10 10:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7f1b64a0b52"
down_revision: Union[str, None] = "b2484524073e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section_label", sa.String(length=255), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("document_chunks", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_document_chunks_document_id"), ["document_id"], unique=False)

    op.create_table(
        "responsibility_owners",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("policy_area", sa.String(length=255), nullable=False),
        sa.Column("owner_name", sa.String(length=255), nullable=False),
        sa.Column("owner_role", sa.String(length=255), nullable=True),
        sa.Column("owner_email", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("responsibility_owners", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_responsibility_owners_workspace_id"), ["workspace_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("responsibility_owners", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_responsibility_owners_workspace_id"))
    op.drop_table("responsibility_owners")

    with op.batch_alter_table("document_chunks", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_document_chunks_document_id"))
    op.drop_table("document_chunks")
