"""Install ready-to-run demonstration data once, preserving user records."""
from alembic import op
from sqlalchemy.orm import Session
from app.services.demos import seed_demos

revision = "002_builtin_demos"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade():
    with Session(bind=op.get_bind()) as db:
        seed_demos(db)
        db.commit()


def downgrade():
    # Demo records may now contain user edits and run history; preserve them.
    pass
