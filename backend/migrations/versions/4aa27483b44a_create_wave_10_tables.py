"""create_wave_10_tables

Revision ID: 4aa27483b44a
Revises: bb2b3a05cd78
Create Date: 2026-06-10 21:01:45.720404

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4aa27483b44a'
down_revision: Union[str, Sequence[str], None] = 'bb2b3a05cd78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('career_strategy_reviews',
    sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('user_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('goals_snapshot', sa.JSON(), nullable=False),
    sa.Column('health_score_start', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('health_score_end', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('insights_summary', sa.Text(), nullable=False),
    sa.Column('feedback_text', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_career_strategy_reviews_user_id'), 'career_strategy_reviews', ['user_id'], unique=False)
    
    op.create_table('gap_retrieval_logs',
    sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('user_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('query_vector_id', sa.String(length=255), nullable=True),
    sa.Column('postgres_query_string', sa.Text(), nullable=True),
    sa.Column('adjacent_results_count', sa.Integer(), nullable=False),
    sa.Column('user_feedback_score', sa.Integer(), nullable=True),
    sa.Column('pipeline_duration_ms', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_gap_retrieval_logs_user_id'), 'gap_retrieval_logs', ['user_id'], unique=False)
    
    op.create_table('user_digests',
    sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('user_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('sent_at', sa.DateTime(), nullable=True),
    sa.Column('health_score_snapshot', sa.JSON(), nullable=False),
    sa.Column('market_insight_summary', sa.Text(), nullable=False),
    sa.Column('position_delta_snapshot', sa.JSON(), nullable=False),
    sa.Column('recommendations_snapshot', sa.JSON(), nullable=False),
    sa.Column('delivery_status', sa.String(length=50), nullable=False),
    sa.Column('opened_at', sa.DateTime(), nullable=True),
    sa.Column('clicked_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_digests_user_id'), 'user_digests', ['user_id'], unique=False)
    
    op.create_table('strategy_action_items',
    sa.Column('id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('review_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('description', sa.String(length=255), nullable=False),
    sa.Column('difficulty', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('target_date', sa.Date(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['review_id'], ['career_strategy_reviews.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_strategy_action_items_review_id'), 'strategy_action_items', ['review_id'], unique=False)
    
    op.add_column('user_preferences', sa.Column('digest_delivery_day', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('user_preferences', sa.Column('digest_delivery_hour', sa.Integer(), nullable=False, server_default='9'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user_preferences', 'digest_delivery_hour')
    op.drop_column('user_preferences', 'digest_delivery_day')
    op.drop_index(op.f('ix_strategy_action_items_review_id'), table_name='strategy_action_items')
    op.drop_table('strategy_action_items')
    op.drop_index(op.f('ix_user_digests_user_id'), table_name='user_digests')
    op.drop_table('user_digests')
    op.drop_index(op.f('ix_gap_retrieval_logs_user_id'), table_name='gap_retrieval_logs')
    op.drop_table('gap_retrieval_logs')
    op.drop_index(op.f('ix_career_strategy_reviews_user_id'), table_name='career_strategy_reviews')
    op.drop_table('career_strategy_reviews')
