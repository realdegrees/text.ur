"""Remove the 'manage_share_links' permission from various tables.

Revision ID: 65015c842a3c
Revises: 174194a9a028
Create Date: 2025-11-27 11:34:50.879585

"""
from typing import Sequence, Union
import sqlmodel
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '65015c842a3c'
down_revision: Union[str, None] = '174194a9a028'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove "manage_share_links" from permissions in the sharelink table
    op.execute("""
        UPDATE sharelink
        SET permissions = array_remove(permissions, 'manage_share_links')
        WHERE permissions IS NOT NULL;
    """)

    # Remove "manage_share_links" from default_permissions in the group table
    op.execute("""
        UPDATE "group"
        SET default_permissions = array_remove(default_permissions, 'manage_share_links')
        WHERE default_permissions IS NOT NULL;
    """)

    # Remove "manage_share_links" from permissions in the membership table
    op.execute("""
        UPDATE membership
        SET permissions = array_remove(permissions, 'manage_share_links')
        WHERE permissions IS NOT NULL;
    """)

def downgrade() -> None:
    """Downgrade logic is not implemented as removing permissions is irreversible."""
    pass
