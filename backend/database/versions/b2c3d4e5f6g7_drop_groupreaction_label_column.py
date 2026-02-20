"""drop groupreaction label column

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-20 18:00:00.000000

"""

from typing import Sequence, Union

import sqlmodel
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("groupreaction", "label")


def downgrade() -> None:
    op.add_column(
        "groupreaction",
        sa.Column(
            "label",
            sqlmodel.sql.sqltypes.AutoString(length=50),
            nullable=False,
            server_default="",
        ),
    )
