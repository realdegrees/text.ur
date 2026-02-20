"""Tests for the score computation logic.

These tests call ``_compute_score`` directly with factories-created
data to verify the points formula without involving HTTP or Redis.
"""

from __future__ import annotations

import pytest
from api.routers.memberships import _compute_score
from factories import models as f
from models.enums import Emoji, Permission
from models.tables import GroupReaction, ScoreConfig
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession


async def _make_scenario(
    db: SQLModelAsyncSession,
) -> dict:
    """Create a basic group + user setup for score tests.

    Returns a dict with keys: user, other_user, admin_user, group,
    document, group_reactions (dict keyed by emoji name).
    """
    user = await db.run_sync(lambda s: f.UserFactory())
    other_user = await db.run_sync(lambda s: f.UserFactory())
    admin_user = await db.run_sync(lambda s: f.UserFactory())

    group = await db.run_sync(lambda s: f.GroupFactory())
    document = await db.run_sync(lambda s: f.DocumentFactory(group=group))

    # user is a regular member
    await db.run_sync(
        lambda s: f.MembershipFactory(user=user, group=group, accepted=True)
    )
    # other_user is a regular member
    await db.run_sync(
        lambda s: f.MembershipFactory(
            user=other_user, group=group, accepted=True
        )
    )
    # admin_user is owner (admin-level)
    await db.run_sync(
        lambda s: f.MembershipFactory(
            user=admin_user, group=group, is_owner=True, accepted=True
        )
    )

    # Create ScoreConfig with defaults
    await db.run_sync(lambda s: f.ScoreConfigFactory(group=group))

    # Create default group reactions
    emojis = [
        (Emoji.THUMBS_UP, 0),
        (Emoji.SMILE, 1),
        (Emoji.HEART, 2),
        (Emoji.FIRE, 3),
        (Emoji.PINCH, 4),
        (Emoji.NERD, 5),
    ]
    group_reactions = {}
    for emoji, order in emojis:
        gr = await db.run_sync(
            lambda s, e=emoji, o=order: f.GroupReactionFactory(
                group=group, emoji=e, order=o
            )
        )
        group_reactions[emoji] = gr

    await db.flush()

    return {
        "user": user,
        "other_user": other_user,
        "admin_user": admin_user,
        "group": group,
        "document": document,
        "group_reactions": group_reactions,
    }


class TestScoreEmpty:
    """Score should be zero when the user has no activity."""

    async def test_empty_score(self, db: SQLModelAsyncSession) -> None:
        """A member with no comments/reactions gets score 0."""
        s = await _make_scenario(db)

        score = await _compute_score(db, s["group"].id, s["user"].id)

        assert score.total == 0
        assert score.breakdown.highlights == 0
        assert score.breakdown.comments == 0
        assert score.breakdown.tags == 0
        assert score.breakdown.reactions_received == 0
        assert score.breakdown.reactions_given == 0


class TestScoreHighlightsAndComments:
    """Points from root-level highlights and comments."""

    async def test_highlight_only(self, db: SQLModelAsyncSession) -> None:
        """A root comment with annotation but no content gives 1 pt."""
        s = await _make_scenario(db)

        await db.run_sync(
            lambda sess: f.CommentFactory(
                document=s["document"],
                user=s["user"],
                annotation={"rects": [1, 2]},
                content=None,
            )
        )
        await db.flush()

        score = await _compute_score(db, s["group"].id, s["user"].id)

        assert score.breakdown.highlights == 1
        assert score.breakdown.highlight_points == 1
        assert score.breakdown.comments == 0
        assert score.breakdown.comment_points == 0
        assert score.total == 1

    async def test_comment_only(self, db: SQLModelAsyncSession) -> None:
        """A root comment with content but empty annotation gives 5 pt."""
        s = await _make_scenario(db)

        await db.run_sync(
            lambda sess: f.CommentFactory(
                document=s["document"],
                user=s["user"],
                annotation={},
                content="some text",
            )
        )
        await db.flush()

        score = await _compute_score(db, s["group"].id, s["user"].id)

        assert score.breakdown.highlights == 0
        assert score.breakdown.comments == 1
        assert score.breakdown.comment_points == 5
        assert score.total == 5

    async def test_highlight_plus_comment(
        self, db: SQLModelAsyncSession
    ) -> None:
        """A root comment with BOTH annotation and content gives 6 pt."""
        s = await _make_scenario(db)

        await db.run_sync(
            lambda sess: f.CommentFactory(
                document=s["document"],
                user=s["user"],
                annotation={"rects": [1]},
                content="annotated text",
            )
        )
        await db.flush()

        score = await _compute_score(db, s["group"].id, s["user"].id)

        assert score.breakdown.highlights == 1
        assert score.breakdown.comments == 1
        assert score.total == 6  # 1 + 5

    async def test_replies_do_not_count(self, db: SQLModelAsyncSession) -> None:
        """Replies (parent_id != null) should not earn any points."""
        s = await _make_scenario(db)

        root = await db.run_sync(
            lambda sess: f.CommentFactory(
                document=s["document"],
                user=s["user"],
                content="root",
            )
        )
        # Reply by same user
        await db.run_sync(
            lambda sess: f.CommentFactory(
                document=s["document"],
                user=s["user"],
                parent=root,
                content="reply",
            )
        )
        await db.flush()

        score = await _compute_score(db, s["group"].id, s["user"].id)

        # Only the root comment earns points
        assert score.breakdown.comments == 1
        assert score.total == 5


class TestScoreReactions:
    """Points from reactions given and received."""

    async def test_reaction_given(self, db: SQLModelAsyncSession) -> None:
        """Giving a reaction earns giver_points (2 by default)."""
        s = await _make_scenario(db)
        gr = s["group_reactions"][Emoji.HEART]

        # other_user creates a root comment
        comment = await db.run_sync(
            lambda sess: f.CommentFactory(
                document=s["document"],
                user=s["other_user"],
                content="other's comment",
            )
        )
        # user reacts to it
        await db.run_sync(
            lambda sess: f.ReactionFactory(
                user=s["user"],
                comment=comment,
                group_reaction=gr,
            )
        )
        await db.flush()

        score = await _compute_score(db, s["group"].id, s["user"].id)

        assert score.breakdown.reactions_given == 1
        assert score.breakdown.reaction_given_points == 2

    async def test_reaction_received_from_normal(
        self, db: SQLModelAsyncSession
    ) -> None:
        """Receiving a reaction from a normal user earns points (2)."""
        s = await _make_scenario(db)
        gr = s["group_reactions"][Emoji.THUMBS_UP]

        comment = await db.run_sync(
            lambda sess: f.CommentFactory(
                document=s["document"],
                user=s["user"],
                content="my comment",
            )
        )
        # other_user (normal) reacts
        await db.run_sync(
            lambda sess: f.ReactionFactory(
                user=s["other_user"],
                comment=comment,
                group_reaction=gr,
            )
        )
        await db.flush()

        score = await _compute_score(db, s["group"].id, s["user"].id)

        assert score.breakdown.reactions_received == 1
        assert score.breakdown.reactions_received_from_admin == 0
        assert score.breakdown.reaction_received_points == 2

    async def test_reaction_received_from_admin(
        self, db: SQLModelAsyncSession
    ) -> None:
        """Receiving a reaction from an admin/owner earns admin_points (4)."""
        s = await _make_scenario(db)
        gr = s["group_reactions"][Emoji.FIRE]

        comment = await db.run_sync(
            lambda sess: f.CommentFactory(
                document=s["document"],
                user=s["user"],
                content="my comment",
            )
        )
        # admin_user (owner) reacts
        await db.run_sync(
            lambda sess: f.ReactionFactory(
                user=s["admin_user"],
                comment=comment,
                group_reaction=gr,
            )
        )
        await db.flush()

        score = await _compute_score(db, s["group"].id, s["user"].id)

        assert score.breakdown.reactions_received == 1
        assert score.breakdown.reactions_received_from_admin == 1
        assert score.breakdown.reaction_received_points == 4


class TestScoreTags:
    """Points from tags on root comments."""

    async def test_tag_points(self, db: SQLModelAsyncSession) -> None:
        """Each tag on a root comment earns 2 pts."""
        s = await _make_scenario(db)

        comment = await db.run_sync(
            lambda sess: f.CommentFactory(
                document=s["document"],
                user=s["user"],
                content="tagged comment",
            )
        )

        # Create tags and associate them
        from models.tables import CommentTag, Tag

        tag1 = await db.run_sync(
            lambda sess: Tag(
                document_id=s["document"].id,
                label="tag1",
                color="#ff0000",
            )
        )
        tag2 = await db.run_sync(
            lambda sess: Tag(
                document_id=s["document"].id,
                label="tag2",
                color="#00ff00",
            )
        )
        db.add(tag1)
        db.add(tag2)
        await db.flush()

        ct1 = CommentTag(comment_id=comment.id, tag_id=tag1.id, order=0)
        ct2 = CommentTag(comment_id=comment.id, tag_id=tag2.id, order=1)
        db.add(ct1)
        db.add(ct2)
        await db.flush()

        score = await _compute_score(db, s["group"].id, s["user"].id)

        assert score.breakdown.tags == 2
        assert score.breakdown.tag_points == 4


class TestScoreDocumentFilter:
    """Score scoped to a single document via document_id."""

    async def test_filter_by_document(self, db: SQLModelAsyncSession) -> None:
        """Only activity on the specified document is counted."""
        s = await _make_scenario(db)

        # Create a second document in the same group
        doc2 = await db.run_sync(
            lambda sess: f.DocumentFactory(group=s["group"])
        )
        await db.flush()

        # Comment on doc1
        await db.run_sync(
            lambda sess: f.CommentFactory(
                document=s["document"],
                user=s["user"],
                content="on doc1",
            )
        )
        # Comment on doc2
        await db.run_sync(
            lambda sess: f.CommentFactory(
                document=doc2,
                user=s["user"],
                content="on doc2",
            )
        )
        await db.flush()

        # Unfiltered: both comments
        score_all = await _compute_score(db, s["group"].id, s["user"].id)
        assert score_all.breakdown.comments == 2
        assert score_all.total == 10  # 2 * 5

        # Filtered to doc1
        score_doc1 = await _compute_score(
            db, s["group"].id, s["user"].id, document_id=s["document"].id
        )
        assert score_doc1.breakdown.comments == 1
        assert score_doc1.total == 5

        # Filtered to doc2
        score_doc2 = await _compute_score(
            db, s["group"].id, s["user"].id, document_id=doc2.id
        )
        assert score_doc2.breakdown.comments == 1
        assert score_doc2.total == 5

    async def test_filter_empty_document(
        self, db: SQLModelAsyncSession
    ) -> None:
        """Filtering to a document with no activity gives zero score."""
        s = await _make_scenario(db)

        doc_empty = await db.run_sync(
            lambda sess: f.DocumentFactory(group=s["group"])
        )
        await db.flush()

        # Activity only on the original document
        await db.run_sync(
            lambda sess: f.CommentFactory(
                document=s["document"],
                user=s["user"],
                content="only here",
            )
        )
        await db.flush()

        score = await _compute_score(
            db, s["group"].id, s["user"].id, document_id=doc_empty.id
        )
        assert score.total == 0
        assert score.breakdown.comments == 0

    async def test_filter_reactions_scoped(
        self, db: SQLModelAsyncSession
    ) -> None:
        """Reaction counts are scoped to the specified document."""
        s = await _make_scenario(db)
        gr_heart = s["group_reactions"][Emoji.HEART]
        gr_fire = s["group_reactions"][Emoji.FIRE]

        doc2 = await db.run_sync(
            lambda sess: f.DocumentFactory(group=s["group"])
        )
        await db.flush()

        # Comment + reaction on doc1
        c1 = await db.run_sync(
            lambda sess: f.CommentFactory(
                document=s["document"],
                user=s["user"],
                content="doc1 comment",
            )
        )
        await db.run_sync(
            lambda sess: f.ReactionFactory(
                user=s["other_user"],
                comment=c1,
                group_reaction=gr_heart,
            )
        )

        # Comment + reaction on doc2
        c2 = await db.run_sync(
            lambda sess: f.CommentFactory(
                document=doc2,
                user=s["user"],
                content="doc2 comment",
            )
        )
        await db.run_sync(
            lambda sess: f.ReactionFactory(
                user=s["other_user"],
                comment=c2,
                group_reaction=gr_fire,
            )
        )
        await db.flush()

        # Filter to doc1: 1 comment (5) + 1 reaction received (2) = 7
        score = await _compute_score(
            db, s["group"].id, s["user"].id, document_id=s["document"].id
        )
        assert score.breakdown.comments == 1
        assert score.breakdown.reactions_received == 1
        assert score.total == 7


class TestScoreCombined:
    """Full scenario combining all point sources."""

    async def test_combined_score(self, db: SQLModelAsyncSession) -> None:
        """Verify the total across highlights, comments, tags, and reactions."""
        s = await _make_scenario(db)
        gr_smile = s["group_reactions"][Emoji.SMILE]
        gr_nerd = s["group_reactions"][Emoji.NERD]
        gr_heart = s["group_reactions"][Emoji.HEART]

        # Root comment with highlight + content = 6 pts
        comment = await db.run_sync(
            lambda sess: f.CommentFactory(
                document=s["document"],
                user=s["user"],
                annotation={"rects": [1]},
                content="full comment",
            )
        )

        # 1 tag = 2 pts
        from models.tables import CommentTag, Tag

        tag = await db.run_sync(
            lambda sess: Tag(
                document_id=s["document"].id,
                label="test",
                color="#000000",
            )
        )
        db.add(tag)
        await db.flush()
        db.add(CommentTag(comment_id=comment.id, tag_id=tag.id, order=0))
        await db.flush()

        # 1 reaction from normal user = 2 pts (points)
        await db.run_sync(
            lambda sess: f.ReactionFactory(
                user=s["other_user"],
                comment=comment,
                group_reaction=gr_smile,
            )
        )

        # 1 reaction from admin = 4 pts (admin_points)
        await db.run_sync(
            lambda sess: f.ReactionFactory(
                user=s["admin_user"],
                comment=comment,
                group_reaction=gr_nerd,
            )
        )

        # User reacts to someone else's comment = 2 pts (giver_points)
        other_comment = await db.run_sync(
            lambda sess: f.CommentFactory(
                document=s["document"],
                user=s["other_user"],
                content="other",
            )
        )
        await db.run_sync(
            lambda sess: f.ReactionFactory(
                user=s["user"],
                comment=other_comment,
                group_reaction=gr_heart,
            )
        )
        await db.flush()

        score = await _compute_score(db, s["group"].id, s["user"].id)

        # 1 highlight (1) + 1 comment (5) + 1 tag (2)
        # + 1 normal reaction received (2) + 1 admin reaction received (4)
        # + 1 reaction given (2)
        expected = 1 + 5 + 2 + 2 + 4 + 2
        assert score.total == expected
        assert score.breakdown.highlights == 1
        assert score.breakdown.comments == 1
        assert score.breakdown.tags == 1
        assert score.breakdown.reactions_received == 2
        assert score.breakdown.reactions_received_from_admin == 1
        assert score.breakdown.reactions_given == 1
