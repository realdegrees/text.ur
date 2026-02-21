# ruff: noqa: D106, D101
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import factory
from factories.base import BaseFactory
from models.enums import Emoji, Permission, ViewMode, Visibility
from models.tables import (
    Comment,
    Document,
    Group,
    GroupReaction,
    Membership,
    Reaction,
    ScoreConfig,
    ShareLink,
    User,
)


class UserFactory(BaseFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    password = factory.Faker("password")
    verified = False
    secret = factory.LazyFunction(lambda: str(uuid4()))


class GroupFactory(BaseFactory):
    class Meta:
        model = Group

    name = factory.Sequence(lambda n: f"Group {n}")
    secret = factory.LazyFunction(lambda: str(uuid4()))
    default_permissions = factory.LazyFunction(lambda: [])


class MembershipFactory(BaseFactory):
    class Meta:
        model = Membership

    user = factory.SubFactory(UserFactory)
    group = factory.SubFactory(GroupFactory)
    permissions = factory.LazyFunction(lambda: [])
    is_owner = False
    accepted = True

    @factory.post_generation
    def link(self, create: bool, extracted, **kwargs) -> None:  # noqa: ANN001, ANN003
        """Ensure created Membership is visible on the related User and Group objects.

        Some tests evaluate Python-side predicates that rely on in-memory
        relationship lists (e.g. group.memberships or user.memberships). When
        factories persist objects using a session with "commit" persistence the
        relationship collections may not be populated on detached instances. This
        hook attempts to append the newly-created membership into the in-memory
        collections when possible so predicates operate on expected objects.
        """
        # Link membership into group membership list if present
        if getattr(self, "group", None) is not None:
            if getattr(self.group, "memberships", None) is None:
                self.group.memberships = []
            # Avoid duplicate entries
            if self not in self.group.memberships:
                self.group.memberships.append(self)

        # Link membership into user membership list if present
        if getattr(self, "user", None) is not None:
            if getattr(self.user, "memberships", None) is None:
                self.user.memberships = []
            if self not in self.user.memberships:
                self.user.memberships.append(self)


class DocumentFactory(BaseFactory):
    class Meta:
        model = Document

    name = factory.Sequence(lambda n: f"document_{n}.pdf")
    s3_key = factory.Sequence(lambda n: f"documents/doc_{n}.pdf")
    size_bytes = factory.Faker("random_int", min=1000, max=1000000)
    visibility = Visibility.PRIVATE
    view_mode = ViewMode.PUBLIC
    secret = factory.LazyFunction(uuid4)
    group = factory.SubFactory(GroupFactory)


class CommentFactory(BaseFactory):
    class Meta:
        model = Comment

    visibility = Visibility.PUBLIC
    document = factory.SubFactory(DocumentFactory)
    user = factory.SubFactory(UserFactory)
    parent = None
    content = factory.Faker("paragraph")
    annotation = factory.LazyFunction(dict)


class ScoreConfigFactory(BaseFactory):
    class Meta:
        model = ScoreConfig

    group = factory.SubFactory(GroupFactory)
    highlight_points = 1
    comment_points = 5
    tag_points = 2


class GroupReactionFactory(BaseFactory):
    class Meta:
        model = GroupReaction

    group = factory.SubFactory(GroupFactory)
    emoji = Emoji.THUMBS_UP
    points = 2
    admin_points = 4
    giver_points = 2
    order = 0


class ReactionFactory(BaseFactory):
    class Meta:
        model = Reaction

    user = factory.SubFactory(UserFactory)
    comment = factory.SubFactory(CommentFactory)
    group_reaction = factory.SubFactory(GroupReactionFactory)


class ShareLinkFactory(BaseFactory):
    class Meta:
        model = ShareLink

    group = factory.SubFactory(GroupFactory)
    created_by = factory.SubFactory(UserFactory)
    permissions = factory.LazyFunction(lambda: [])
    token = factory.LazyFunction(lambda: str(uuid4()))
    expires_at = factory.LazyFunction(
        lambda: datetime.now(UTC) + timedelta(days=7)
    )
    label = factory.Faker("sentence")
