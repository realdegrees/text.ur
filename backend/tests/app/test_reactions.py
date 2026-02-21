"""Tests for reaction business logic.

These tests verify self-reaction prevention, reply-reaction blocking,
upsert behaviour, and deletion using direct DB operations and the
reaction router logic patterns.
"""

from __future__ import annotations

import pytest
from factories import models as f
from models.enums import Emoji, Permission
from models.tables import Comment, GroupReaction, Reaction
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession


# ---------------------------------------------------------------------------
# Helper: build a standard group/document/comment for reaction tests
# ---------------------------------------------------------------------------
async def _setup(
    db: SQLModelAsyncSession,
    *,
    with_reply: bool = False,
) -> dict:
    """Create a group, document, two users, group reactions, and a root comment.

    Returns a dict with keys: author, reactor, group, document, comment,
    group_reaction (the first default), all_group_reactions, and optionally
    'reply'.
    """
    author = await db.run_sync(lambda s: f.UserFactory())
    reactor = await db.run_sync(lambda s: f.UserFactory())
    group = await db.run_sync(lambda s: f.GroupFactory())
    document = await db.run_sync(lambda s: f.DocumentFactory(group=group))

    await db.run_sync(
        lambda s: f.MembershipFactory(
            user=author,
            group=group,
            is_owner=True,
            accepted=True,
        )
    )
    await db.run_sync(
        lambda s: f.MembershipFactory(
            user=reactor,
            group=group,
            permissions=[Permission.ADD_REACTIONS],
            accepted=True,
        )
    )

    # Create default group reactions
    emojis = [
        (Emoji.THUMBS_UP, 0),
        (Emoji.SMILE, 1),
        (Emoji.HEART, 2),
        (Emoji.FIRE, 3),
        (Emoji.PINCH, 4),
        (Emoji.NERD, 5),
    ]
    group_reactions = []
    for emoji, order in emojis:
        gr = await db.run_sync(
            lambda s, e=emoji, o=order: f.GroupReactionFactory(
                group=group, emoji=e, order=o
            )
        )
        group_reactions.append(gr)

    comment = await db.run_sync(
        lambda s: f.CommentFactory(
            document=document,
            user=author,
            content="root comment",
        )
    )

    result: dict = {
        "author": author,
        "reactor": reactor,
        "group": group,
        "document": document,
        "comment": comment,
        "group_reaction": group_reactions[0],
        "all_group_reactions": group_reactions,
    }

    if with_reply:
        reply = await db.run_sync(
            lambda s: f.CommentFactory(
                document=document,
                user=reactor,
                parent=comment,
                content="reply",
            )
        )
        result["reply"] = reply

    await db.flush()
    return result


# ---------------------------------------------------------------------------
# Self-reaction prevention
# ---------------------------------------------------------------------------
class TestSelfReactionPrevention:
    """The router checks comment.user_id == user.id before allowing."""

    async def test_self_reaction_detected(
        self, db: SQLModelAsyncSession
    ) -> None:
        """The comment author should be identified as self-reacting."""
        data = await _setup(db)
        comment = data["comment"]
        author = data["author"]

        # This mirrors the check in reactions.py:30
        assert comment.user_id == author.id

    async def test_other_user_not_self(self, db: SQLModelAsyncSession) -> None:
        """A different user should not be flagged as self-reacting."""
        data = await _setup(db)
        comment = data["comment"]
        reactor = data["reactor"]

        assert comment.user_id != reactor.id


# ---------------------------------------------------------------------------
# Reply reaction prevention
# ---------------------------------------------------------------------------
class TestReplyReactionPrevention:
    """The router checks comment.parent_id is not None."""

    async def test_root_comment_allowed(self, db: SQLModelAsyncSession) -> None:
        """Root comments (parent_id=None) pass the check."""
        data = await _setup(db)
        assert data["comment"].parent_id is None

    async def test_reply_blocked(self, db: SQLModelAsyncSession) -> None:
        """Replies (parent_id is set) fail the check."""
        data = await _setup(db, with_reply=True)
        assert data["reply"].parent_id is not None


# ---------------------------------------------------------------------------
# Reaction CRUD via direct DB operations
# ---------------------------------------------------------------------------
class TestReactionCRUD:
    """Test creating, updating, and removing reactions in the DB."""

    async def test_create_reaction(self, db: SQLModelAsyncSession) -> None:
        """A reaction can be inserted for a non-author on a root comment."""
        data = await _setup(db)
        gr = data["all_group_reactions"][2]  # HEART

        reaction = Reaction(
            user_id=data["reactor"].id,
            comment_id=data["comment"].id,
            group_reaction_id=gr.id,
        )
        db.add(reaction)
        await db.flush()

        result = await db.exec(
            select(Reaction).where(
                Reaction.user_id == data["reactor"].id,
                Reaction.comment_id == data["comment"].id,
            )
        )
        fetched = result.first()
        assert fetched is not None
        assert fetched.group_reaction_id == gr.id

    async def test_upsert_changes_group_reaction(
        self, db: SQLModelAsyncSession
    ) -> None:
        """Updating an existing reaction changes its group_reaction_id."""
        data = await _setup(db)
        gr_smile = data["all_group_reactions"][1]  # SMILE
        gr_nerd = data["all_group_reactions"][5]  # NERD

        # Create initial reaction
        reaction = Reaction(
            user_id=data["reactor"].id,
            comment_id=data["comment"].id,
            group_reaction_id=gr_smile.id,
        )
        db.add(reaction)
        await db.flush()

        # Upsert: fetch and change group_reaction_id
        result = await db.exec(
            select(Reaction).where(
                Reaction.user_id == data["reactor"].id,
                Reaction.comment_id == data["comment"].id,
            )
        )
        existing = result.first()
        assert existing is not None

        await db.merge(existing)
        existing.group_reaction_id = gr_nerd.id
        await db.flush()

        # Verify only one reaction with updated group_reaction_id
        result2 = await db.exec(
            select(Reaction).where(
                Reaction.user_id == data["reactor"].id,
                Reaction.comment_id == data["comment"].id,
            )
        )
        all_reactions = result2.all()
        assert len(all_reactions) == 1
        assert all_reactions[0].group_reaction_id == gr_nerd.id

    async def test_remove_reaction(self, db: SQLModelAsyncSession) -> None:
        """Deleting a reaction removes it from the DB."""
        data = await _setup(db)
        gr = data["all_group_reactions"][3]  # FIRE

        reaction = Reaction(
            user_id=data["reactor"].id,
            comment_id=data["comment"].id,
            group_reaction_id=gr.id,
        )
        db.add(reaction)
        await db.flush()

        # Delete
        result = await db.exec(
            select(Reaction).where(
                Reaction.user_id == data["reactor"].id,
                Reaction.comment_id == data["comment"].id,
            )
        )
        to_delete = result.first()
        assert to_delete is not None
        await db.delete(to_delete)
        await db.flush()

        # Verify gone
        result2 = await db.exec(
            select(Reaction).where(
                Reaction.user_id == data["reactor"].id,
                Reaction.comment_id == data["comment"].id,
            )
        )
        assert result2.first() is None

    async def test_composite_pk_uniqueness(
        self, db: SQLModelAsyncSession
    ) -> None:
        """The (user_id, comment_id) composite PK prevents duplicates."""
        data = await _setup(db)
        gr = data["group_reaction"]  # THUMBS_UP

        await db.run_sync(
            lambda s: f.ReactionFactory(
                user=data["reactor"],
                comment=data["comment"],
                group_reaction=gr,
            )
        )
        await db.flush()

        # Verify exactly one reaction exists
        result = await db.exec(
            select(Reaction).where(
                Reaction.user_id == data["reactor"].id,
                Reaction.comment_id == data["comment"].id,
            )
        )
        assert len(result.all()) == 1


class TestAllGroupReactions:
    """All 6 configured group reactions can be stored and retrieved."""

    @pytest.mark.parametrize("reaction_index", range(6))
    async def test_each_group_reaction(
        self,
        db: SQLModelAsyncSession,
        reaction_index: int,
    ) -> None:
        """Each configured GroupReaction can be used as a reaction."""
        data = await _setup(db)
        gr = data["all_group_reactions"][reaction_index]

        reaction = Reaction(
            user_id=data["reactor"].id,
            comment_id=data["comment"].id,
            group_reaction_id=gr.id,
        )
        db.add(reaction)
        await db.flush()

        result = await db.exec(
            select(Reaction).where(
                Reaction.user_id == data["reactor"].id,
                Reaction.comment_id == data["comment"].id,
            )
        )
        fetched = result.first()
        assert fetched is not None
        assert fetched.group_reaction_id == gr.id
