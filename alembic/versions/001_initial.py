"""Initial Schema"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('capabilities',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('category', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_capabilities_id'), 'capabilities', ['id'], unique=False)
    op.create_index(op.f('ix_capabilities_name'), 'capabilities', ['name'], unique=True)
    op.create_table('environments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('os', sa.String(length=100), nullable=False),
    sa.Column('os_version', sa.String(length=50), nullable=True),
    sa.Column('architecture', sa.String(length=50), nullable=True),
    sa.Column('vagrant_path', sa.String(length=500), nullable=True),
    sa.Column('ansible_inventory', sa.String(length=500), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_environments_id'), 'environments', ['id'], unique=False)
    op.create_index(op.f('ix_environments_name'), 'environments', ['name'], unique=True)
    op.create_table('capability_versions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('capability_id', sa.Integer(), nullable=False),
    sa.Column('version', sa.String(length=50), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('artifact_path', sa.String(length=500), nullable=True),
    sa.Column('repository_url', sa.String(length=500), nullable=True),
    sa.Column('commit_hash', sa.String(length=100), nullable=True),
    sa.Column('entry_point', sa.String(length=255), nullable=True),
    sa.Column('execution_command', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['capability_id'], ['capabilities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_capability_versions_capability_id'), 'capability_versions', ['capability_id'], unique=False)
    op.create_index(op.f('ix_capability_versions_id'), 'capability_versions', ['id'], unique=False)
    op.create_table('test_plans',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('capability_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['capability_id'], ['capabilities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_test_plans_capability_id'), 'test_plans', ['capability_id'], unique=False)
    op.create_index(op.f('ix_test_plans_id'), 'test_plans', ['id'], unique=False)
    op.create_table('test_cases',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('test_plan_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('test_type', sa.String(length=50), nullable=False),
    sa.Column('expected_result', sa.Text(), nullable=True),
    sa.Column('execution_order', sa.Integer(), nullable=True),
    sa.Column('timeout', sa.Integer(), nullable=True),
    sa.Column('enabled', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['test_plan_id'], ['test_plans.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_test_cases_id'), 'test_cases', ['id'], unique=False)
    op.create_index(op.f('ix_test_cases_test_plan_id'), 'test_cases', ['test_plan_id'], unique=False)
    op.create_table('test_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('capability_version_id', sa.Integer(), nullable=False),
    sa.Column('test_plan_id', sa.Integer(), nullable=False),
    sa.Column('environment_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('overall_result', sa.String(length=20), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('duration', sa.Integer(), nullable=True),
    sa.Column('initiated_by', sa.String(length=255), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['capability_version_id'], ['capability_versions.id'], ),
    sa.ForeignKeyConstraint(['environment_id'], ['environments.id'], ),
    sa.ForeignKeyConstraint(['test_plan_id'], ['test_plans.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_test_runs_capability_version_id'), 'test_runs', ['capability_version_id'], unique=False)
    op.create_index(op.f('ix_test_runs_environment_id'), 'test_runs', ['environment_id'], unique=False)
    op.create_index(op.f('ix_test_runs_id'), 'test_runs', ['id'], unique=False)
    op.create_index(op.f('ix_test_runs_test_plan_id'), 'test_runs', ['test_plan_id'], unique=False)
    op.create_table('test_results',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('test_run_id', sa.Integer(), nullable=False),
    sa.Column('test_case_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('expected_result', sa.Text(), nullable=True),
    sa.Column('actual_result', sa.Text(), nullable=True),
    sa.Column('stdout', sa.Text(), nullable=True),
    sa.Column('stderr', sa.Text(), nullable=True),
    sa.Column('exit_code', sa.Integer(), nullable=True),
    sa.Column('duration', sa.Integer(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['test_case_id'], ['test_cases.id'], ),
    sa.ForeignKeyConstraint(['test_run_id'], ['test_runs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_test_results_id'), 'test_results', ['id'], unique=False)
    op.create_index(op.f('ix_test_results_test_case_id'), 'test_results', ['test_case_id'], unique=False)
    op.create_index(op.f('ix_test_results_test_run_id'), 'test_results', ['test_run_id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_test_results_test_run_id'), table_name='test_results')
    op.drop_index(op.f('ix_test_results_test_case_id'), table_name='test_results')
    op.drop_index(op.f('ix_test_results_id'), table_name='test_results')
    op.drop_table('test_results')
    op.drop_index(op.f('ix_test_runs_test_plan_id'), table_name='test_runs')
    op.drop_index(op.f('ix_test_runs_id'), table_name='test_runs')
    op.drop_index(op.f('ix_test_runs_environment_id'), table_name='test_runs')
    op.drop_index(op.f('ix_test_runs_capability_version_id'), table_name='test_runs')
    op.drop_table('test_runs')
    op.drop_index(op.f('ix_test_cases_test_plan_id'), table_name='test_cases')
    op.drop_index(op.f('ix_test_cases_id'), table_name='test_cases')
    op.drop_table('test_cases')
    op.drop_index(op.f('ix_test_plans_id'), table_name='test_plans')
    op.drop_index(op.f('ix_test_plans_capability_id'), table_name='test_plans')
    op.drop_table('test_plans')
    op.drop_index(op.f('ix_capability_versions_id'), table_name='capability_versions')
    op.drop_index(op.f('ix_capability_versions_capability_id'), table_name='capability_versions')
    op.drop_table('capability_versions')
    op.drop_index(op.f('ix_environments_name'), table_name='environments')
    op.drop_index(op.f('ix_environments_id'), table_name='environments')
    op.drop_table('environments')
    op.drop_index(op.f('ix_capabilities_name'), table_name='capabilities')
    op.drop_index(op.f('ix_capabilities_id'), table_name='capabilities')
    op.drop_table('capabilities')
