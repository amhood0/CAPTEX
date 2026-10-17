"""Add optional names to test runs without changing existing history."""
from alembic import op
import sqlalchemy as sa

revision = "003_run_names"
down_revision = "002_builtin_demos"
branch_labels = None
depends_on = None


def upgrade():
    if "name" not in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("test_runs")}:
        op.add_column("test_runs", sa.Column("name", sa.String(255), nullable=True))


def downgrade():
    op.drop_column("test_runs", "name")
