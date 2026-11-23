"""Serialize first-run local administrator enrollment."""
from alembic import op
import sqlalchemy as sa

revision = "0002_setup_state"
down_revision = "0001_research"
branch_labels = None
depends_on = None


def upgrade():
    # Earlier local startup can create current ORM tables before Alembic is invoked.
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("setup_state"):
        if {c["name"] for c in inspector.get_columns("setup_state")} != {"id", "completed_at"} or inspector.get_pk_constraint("setup_state")["constrained_columns"] != ["id"]:
            raise RuntimeError("Existing setup_state schema is incompatible; migration stopped")
        return
    op.create_table("setup_state", sa.Column("id", sa.String(), primary_key=True),
                    sa.Column("completed_at", sa.String(), nullable=False))


def downgrade():
    raise RuntimeError("Destructive downgrade disabled; restore a reviewed backup instead")
