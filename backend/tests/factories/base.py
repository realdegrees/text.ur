from factory.alchemy import SQLAlchemyModelFactory


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory for all models.
    
    For async database sessions, use with the async session fixture.
    The factory will use the sync_session to create objects synchronously.
    """

    class Meta:  # noqa: D106
        abstract = True
        sqlalchemy_session_persistence = "flush"
        sqlalchemy_session = None
