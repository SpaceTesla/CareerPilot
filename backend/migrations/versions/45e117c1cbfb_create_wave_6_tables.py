"""create_wave_6_tables

Revision ID: 45e117c1cbfb
Revises: 90c09ec38235
Create Date: 2026-06-10 10:26:51.904460

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45e117c1cbfb'
down_revision: Union[str, Sequence[str], None] = '90c09ec38235'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. agent_sessions
    op.create_table(
        'agent_sessions',
        sa.Column('id', sa.UUID(as_uuid=False), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('thread_id', sa.String(length=255), nullable=False),
        sa.Column('current_status', sa.String(length=50), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('thread_id')
    )
    op.create_index('idx_agent_sessions_user_id', 'agent_sessions', ['user_id'])
    op.create_index('idx_agent_sessions_thread_id', 'agent_sessions', ['thread_id'])

    # 2. agent_checkpoints
    op.create_table(
        'agent_checkpoints',
        sa.Column('thread_id', sa.String(length=255), nullable=False),
        sa.Column('checkpoint_id', sa.String(length=255), nullable=False),
        sa.Column('parent_id', sa.String(length=255), nullable=True),
        sa.Column('checkpoint', sa.LargeBinary(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['thread_id'], ['agent_sessions.thread_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('thread_id', 'checkpoint_id')
    )
    op.create_index('idx_agent_checkpoints_lookup', 'agent_checkpoints', ['thread_id', sa.text('checkpoint_id DESC')])

    # 3. agent_runs
    op.create_table(
        'agent_runs',
        sa.Column('id', sa.UUID(as_uuid=False), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('thread_id', sa.String(length=255), nullable=False),
        sa.Column('trigger_source', sa.String(length=100), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tokens_used', sa.Integer(), server_default='0', nullable=False),
        sa.Column('estimated_cost', sa.Numeric(precision=10, scale=6), server_default='0.000000', nullable=False),
        sa.Column('success', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['thread_id'], ['agent_sessions.thread_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. agent_decision_logs
    op.create_table(
        'agent_decision_logs',
        sa.Column('id', sa.UUID(as_uuid=False), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('thread_id', sa.String(length=255), nullable=False),
        sa.Column('run_id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('current_node', sa.String(length=100), nullable=False),
        sa.Column('routing_decision', sa.String(length=100), nullable=False),
        sa.Column('reasoning_explanation', sa.Text(), nullable=False),
        sa.Column('state_snapshot_before', sa.JSON(), nullable=False),
        sa.Column('state_snapshot_after', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['thread_id'], ['agent_sessions.thread_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_decision_logs_thread_id', 'agent_decision_logs', ['thread_id'])
    op.create_index('idx_decision_logs_run_id', 'agent_decision_logs', ['run_id'])

    # 5. research_memories
    op.create_table(
        'research_memories',
        sa.Column('id', sa.UUID(as_uuid=False), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('company_domain', sa.String(length=255), nullable=True),
        sa.Column('role_category', sa.String(length=150), nullable=True),
        sa.Column('structured_data', sa.JSON(), nullable=False),
        sa.Column('raw_sources', sa.JSON(), nullable=False),
        sa.Column('confidence_score', sa.Numeric(precision=3, scale=2), server_default='1.00', nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_name', 'role_category', name='uq_research_memories_lookup')
    )
    op.create_index('idx_research_memories_expires', 'research_memories', ['expires_at'])

    # 6. agent_intelligence_reports
    op.create_table(
        'agent_intelligence_reports',
        sa.Column('id', sa.UUID(as_uuid=False), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('thread_id', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('overall_health_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('position_delta_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('fit_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('structured_explanation', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['thread_id'], ['agent_sessions.thread_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_intelligence_reports_user_id', 'agent_intelligence_reports', ['user_id'])
    op.create_index('idx_intelligence_reports_thread', 'agent_intelligence_reports', ['thread_id'])

    # 7. interaction_summaries
    op.create_table(
        'interaction_summaries',
        sa.Column('id', sa.UUID(as_uuid=False), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('thread_id', sa.String(length=255), nullable=False),
        sa.Column('summary_text', sa.Text(), nullable=False),
        sa.Column('start_message_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_message_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['thread_id'], ['agent_sessions.thread_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_interaction_summaries_thread', 'interaction_summaries', ['thread_id'])

    # 8. interaction_memories
    op.create_table(
        'interaction_memories',
        sa.Column('id', sa.UUID(as_uuid=False), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('thread_id', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('summary_id', sa.UUID(as_uuid=False), nullable=True),
        sa.Column('tokens_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['thread_id'], ['agent_sessions.thread_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['summary_id'], ['interaction_summaries.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_interaction_memories_thread', 'interaction_memories', ['thread_id'])
    op.create_index('idx_interaction_memories_user', 'interaction_memories', ['user_id'])

    # 9. agent_approval_requests
    op.create_table(
        'agent_approval_requests',
        sa.Column('id', sa.UUID(as_uuid=False), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('thread_id', sa.String(length=255), nullable=False),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['thread_id'], ['agent_sessions.thread_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_approval_requests_user', 'agent_approval_requests', ['user_id'])
    op.create_index('idx_approval_requests_status', 'agent_approval_requests', ['status'])

    # 10. agent_approval_audit_logs
    op.create_table(
        'agent_approval_audit_logs',
        sa.Column('id', sa.UUID(as_uuid=False), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('approval_request_id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('actor_id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('action_taken', sa.String(length=50), nullable=False),
        sa.Column('changes_made', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['approval_request_id'], ['agent_approval_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_approval_audit_request', 'agent_approval_audit_logs', ['approval_request_id'])

    # 11. Add search_vector to job_postings and trigger
    from sqlalchemy.dialects.postgresql import TSVECTOR
    op.add_column('job_postings', sa.Column('search_vector', TSVECTOR, nullable=True))
    op.create_index('idx_job_postings_search_vector', 'job_postings', ['search_vector'], postgresql_using='gin')

    op.execute("""
CREATE OR REPLACE FUNCTION job_postings_trigger_func() RETURNS trigger AS $$
begin
  new.search_vector :=
    setweight(to_tsvector('english', coalesce(new.title,'')), 'A') ||
    setweight(to_tsvector('english', coalesce(new.description,'')), 'B');
  return new;
end
$$ LANGUAGE plpgsql;
    """)
    op.execute("""
CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE
ON job_postings FOR EACH ROW EXECUTE FUNCTION job_postings_trigger_func();
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS tsvectorupdate ON job_postings;")
    op.execute("DROP FUNCTION IF EXISTS job_postings_trigger_func();")
    op.drop_index('idx_job_postings_search_vector', table_name='job_postings')
    op.drop_column('job_postings', 'search_vector')

    op.drop_index('idx_approval_audit_request', table_name='agent_approval_audit_logs')
    op.drop_table('agent_approval_audit_logs')
    op.drop_index('idx_approval_requests_status', table_name='agent_approval_requests')
    op.drop_index('idx_approval_requests_user', table_name='agent_approval_requests')
    op.drop_table('agent_approval_requests')
    op.drop_index('idx_interaction_memories_user', table_name='interaction_memories')
    op.drop_index('idx_interaction_memories_thread', table_name='interaction_memories')
    op.drop_table('interaction_memories')
    op.drop_index('idx_interaction_summaries_thread', table_name='interaction_summaries')
    op.drop_table('interaction_summaries')
    op.drop_index('idx_intelligence_reports_thread', table_name='agent_intelligence_reports')
    op.drop_index('idx_intelligence_reports_user_id', table_name='agent_intelligence_reports')
    op.drop_table('agent_intelligence_reports')
    op.drop_index('idx_research_memories_expires', table_name='research_memories')
    op.drop_table('research_memories')
    op.drop_table('agent_decision_logs')
    op.drop_table('agent_runs')
    op.drop_index('idx_agent_checkpoints_lookup', table_name='agent_checkpoints')
    op.drop_table('agent_checkpoints')
    op.drop_index('idx_agent_sessions_thread_id', table_name='agent_sessions')
    op.drop_index('idx_agent_sessions_user_id', table_name='agent_sessions')
    op.drop_table('agent_sessions')

