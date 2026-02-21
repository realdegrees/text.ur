"""add score_config and group_reaction tables, refactor reaction FK

Revision ID: a1b2c3d4e5f6
Revises: 41dea9fce499
Create Date: 2026-02-20 12:00:00.000000

"""

from typing import Sequence, Union

import sqlmodel
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "41dea9fce499"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Old ReactionType string -> Emoji character mapping
OLD_TYPE_TO_EMOJI: dict[str, str] = {
    "thumbs_up": "\U0001f44d",
    "smile": "\U0001f60a",
    "heart": "\u2764\ufe0f",
    "fire": "\U0001f525",
    "pinch": "\U0001faf0",
    "nerd": "\U0001f913",
}

DEFAULT_REACTIONS: list[dict] = [
    {"emoji": "\U0001f44d", "label": "Thumbs up", "points": 2, "admin_points": 4, "giver_points": 2, "order": 0},
    {"emoji": "\U0001f60a", "label": "Smile", "points": 2, "admin_points": 4, "giver_points": 2, "order": 1},
    {"emoji": "\u2764\ufe0f", "label": "Heart", "points": 2, "admin_points": 4, "giver_points": 2, "order": 2},
    {"emoji": "\U0001f525", "label": "Fire", "points": 2, "admin_points": 4, "giver_points": 2, "order": 3},
    {"emoji": "\U0001faf0", "label": "Pinch", "points": 2, "admin_points": 4, "giver_points": 2, "order": 4},
    {"emoji": "\U0001f913", "label": "Nerd", "points": 2, "admin_points": 4, "giver_points": 2, "order": 5},
]


def upgrade() -> None:
    # 1. Create scoreconfig table
    op.create_table(
        "scoreconfig",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("group_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("highlight_points", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("comment_points", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("tag_points", sa.Integer(), nullable=False, server_default="2"),
        sa.ForeignKeyConstraint(["group_id"], ["group.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("group_id"),
    )

    # 2. Create groupreaction table
    op.create_table(
        "groupreaction",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("group_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("emoji", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("label", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("admin_points", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("giver_points", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["group_id"], ["group.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "emoji", name="uq_groupreaction_group_emoji"),
    )

    # 3. Add group_reaction_id column (nullable initially for backfill)
    op.add_column(
        "reaction",
        sa.Column("group_reaction_id", sa.Integer(), nullable=True),
    )

    # 4. Data backfill
    conn = op.get_bind()

    # 4a. Create ScoreConfig for every existing group
    groups = conn.execute(sa.text("SELECT id FROM \"group\"")).fetchall()
    for (group_id,) in groups:
        conn.execute(
            sa.text(
                "INSERT INTO scoreconfig (group_id, highlight_points, comment_points, tag_points) "
                "VALUES (:gid, 1, 5, 2)"
            ),
            {"gid": group_id},
        )

        # 4b. Create default GroupReaction rows for each group
        for r in DEFAULT_REACTIONS:
            conn.execute(
                sa.text(
                    "INSERT INTO groupreaction (group_id, emoji, label, points, admin_points, giver_points, \"order\") "
                    "VALUES (:gid, :emoji, :label, :points, :admin_points, :giver_points, :ord)"
                ),
                {
                    "gid": group_id,
                    "emoji": r["emoji"],
                    "label": r["label"],
                    "points": r["points"],
                    "admin_points": r["admin_points"],
                    "giver_points": r["giver_points"],
                    "ord": r["order"],
                },
            )

    # 4c. Backfill reaction.group_reaction_id from old type column
    # For each old reaction type string, find the corresponding
    # GroupReaction row for that comment's group and set the FK.
    for old_type, emoji_char in OLD_TYPE_TO_EMOJI.items():
        conn.execute(
            sa.text(
                "UPDATE reaction r "
                "SET group_reaction_id = gr.id "
                "FROM comment c "
                "JOIN document d ON c.document_id = d.id "
                "JOIN groupreaction gr ON gr.group_id = d.group_id AND gr.emoji = :emoji "
                "WHERE r.comment_id = c.id AND r.type = :old_type"
            ),
            {"emoji": emoji_char, "old_type": old_type},
        )

    # 4d. Delete any reactions that couldn't be mapped (shouldn't happen, but be safe)
    conn.execute(
        sa.text("DELETE FROM reaction WHERE group_reaction_id IS NULL")
    )

    # 5. Drop old type column
    op.drop_column("reaction", "type")

    # 6. Make group_reaction_id NOT NULL + add FK
    op.alter_column(
        "reaction",
        "group_reaction_id",
        nullable=False,
    )
    op.create_foreign_key(
        "fk_reaction_group_reaction_id_groupreaction",
        "reaction",
        "groupreaction",
        ["group_reaction_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Remove FK
    op.drop_constraint(
        "fk_reaction_group_reaction_id_groupreaction",
        "reaction",
        type_="foreignkey",
    )

    # Re-add old type column
    op.add_column(
        "reaction",
        sa.Column("type", sa.String(), nullable=True),
    )

    # Backfill type from group_reaction_id
    conn = op.get_bind()
    for old_type, emoji_char in OLD_TYPE_TO_EMOJI.items():
        conn.execute(
            sa.text(
                "UPDATE reaction r "
                "SET type = :old_type "
                "FROM groupreaction gr "
                "WHERE r.group_reaction_id = gr.id AND gr.emoji = :emoji"
            ),
            {"old_type": old_type, "emoji": emoji_char},
        )

    # Drop group_reaction_id column
    op.drop_column("reaction", "group_reaction_id")

    # Drop new tables
    op.drop_table("groupreaction")
    op.drop_table("scoreconfig")
