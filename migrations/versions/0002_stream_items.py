from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = '0002_stream_items'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'stream_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('summary_id', sa.Integer(), sa.ForeignKey('summaries.id'), nullable=False, unique=True),
        sa.Column('sent_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
    )


def downgrade():
    op.drop_table('stream_items')
