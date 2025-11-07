from factory.alchemy import SQLAlchemyModelFactory


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory for all models."""

    class Meta:  # noqa: D106
        abstract = True
        sqlalchemy_session_persistence = "commit"
        sqlalchemy_session = None
