from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg
import enum
from datetime import datetime

# Revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


# --------------------
# ENUM CLASSES
# --------------------
class PlanEnum(enum.Enum):
    BASIC = "basic"
    PREMIUM = "premium"


class FrequencyEnum(enum.Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


class FactStatusEnum(enum.Enum):
    VERIFIED = "verified"
    DISPUTED = "disputed"
    NOT_VERIFIABLE = "not_verifiable"


# --------------------
# UPGRADE
# --------------------
def upgrade():
    # Create `users` table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.String(), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column(
            "plan",
            sa.Enum(PlanEnum, name="plan"),
            nullable=False
        ),
    )

    # Create `preferences` table
    op.create_table(
        "preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        # Explicitly name this enum type “frequency”
        sa.Column("frequency", sa.Enum(FrequencyEnum, name="frequency"), nullable=False),
        sa.Column("last_sent", sa.DateTime(), nullable=True),
    )

    # Create `sources` table
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("is_social", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
    )

    # Create `user_sources` table
    op.create_table(
        "user_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.UniqueConstraint("user_id", "source_id", name="uix_user_source"),
    )

    # Create `articles` table
    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("url", sa.String(), nullable=False, unique=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("raw_json", pg.JSONB(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
    )

    # Create `summaries` table
    op.create_table(
        "summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.Integer(), sa.ForeignKey("articles.id"), nullable=False, unique=True),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("author", sa.String(), nullable=True),
        sa.Column("publish_date", sa.DateTime(), nullable=True),
        sa.Column("topic", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
    )

    # Create `factchecks` table
    op.create_table(
        "factchecks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("summary_id", sa.Integer(), sa.ForeignKey("summaries.id"), nullable=False, unique=True),
        # Explicitly name this enum type “factstatus”
        sa.Column("status", sa.Enum(FactStatusEnum, name="factstatus"), nullable=False),
        sa.Column("citations", pg.JSONB(), nullable=True),
        sa.Column("checked_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
    )

    # Create `commentaries` table
    op.create_table(
        "commentaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("summary_id", sa.Integer(), sa.ForeignKey("summaries.id"), nullable=False, unique=True),
        sa.Column("commentary_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
    )

    # Create `issues` table
    op.create_table(
        "issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("date", sa.DateTime(), nullable=False, unique=True),
        sa.Column("filename_html", sa.String(), nullable=False),
        sa.Column("filename_txt", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
    )


# --------------------
# DOWNGRADE
# --------------------
def downgrade():
    op.drop_table("issues")
    op.drop_table("commentaries")
    op.drop_table("factchecks")
    op.drop_table("summaries")
    op.drop_table("articles")
    op.drop_table("user_sources")
    op.drop_table("sources")
    op.drop_table("preferences")
    op.drop_table("users")

    # Drop the enum types explicitly (in reverse order of creation)
    op.execute("DROP TYPE IF EXISTS factstatus;")
    op.execute("DROP TYPE IF EXISTS frequency;")
    op.execute("DROP TYPE IF EXISTS plan;")