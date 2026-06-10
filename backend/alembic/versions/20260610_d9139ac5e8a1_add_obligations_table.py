"""add_obligations_table

Revision ID: d9139ac5e8a1
Revises: c7f1b64a0b52
Create Date: 2026-06-10 11:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9139ac5e8a1"
down_revision: Union[str, None] = "c7f1b64a0b52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "obligations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("source_document_id", sa.String(length=36), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=False),
        sa.Column("source_excerpt", sa.Text(), nullable=False),
        sa.Column("compliance_domain", sa.String(length=255), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["source_document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("obligations", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_obligations_source_document_id"), ["source_document_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_obligations_workspace_id"), ["workspace_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("obligations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_obligations_workspace_id"))
        batch_op.drop_index(batch_op.f("ix_obligations_source_document_id"))
    op.drop_table("obligations")
