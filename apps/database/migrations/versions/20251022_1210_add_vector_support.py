"""Add vector support for semantic search

Revision ID: 002_vector_support
Revises: 001_initial
Create Date: 2025-10-22 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_vector_support'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""

    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Add embedding column to tasks table for semantic search
    op.add_column('tasks', sa.Column('embedding', sa.dialects.postgresql.ARRAY(sa.Float()), nullable=True))

    # Create index for vector similarity search
    # Using HNSW for fast approximate nearest neighbor search
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS tasks_embedding_idx
        ON tasks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )

    # Add embedding column to knowledge_base for pattern matching
    op.add_column('knowledge_base', sa.Column('embedding', sa.dialects.postgresql.ARRAY(sa.Float()), nullable=True))

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS knowledge_base_embedding_idx
        ON knowledge_base
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )

    # Create conversation_embeddings table for semantic conversation search
    op.create_table(
        'conversation_embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=False),
        sa.Column('embedding', sa.dialects.postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS conversation_embeddings_idx
        ON conversation_embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_table('conversation_embeddings')
    op.drop_column('knowledge_base', 'embedding')
    op.drop_column('tasks', 'embedding')
    op.execute('DROP EXTENSION IF EXISTS vector')
