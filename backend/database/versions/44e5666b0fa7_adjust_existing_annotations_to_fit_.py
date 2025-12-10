"""adjust existing annotations to fit schema

Revision ID: 44e5666b0fa7
Revises: 209faa01502d
Create Date: 2025-12-10 21:07:51.588650

"""
from typing import Sequence, Union
import sqlmodel
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44e5666b0fa7'
down_revision: Union[str, None] = '209faa01502d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate existing annotations to match new Annotation schema."""
    conn = op.get_bind()
    
    # Update all comments with annotations to match the new schema
    # Using PostgreSQL JSONB functions to transform the data
    conn.execute(sa.text("""
        UPDATE comment
        SET annotation = jsonb_build_object(
            'text', annotation->>'text',
            'boundingBoxes', (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'page_number', (box->>'pageNumber')::int,
                        'x', (box->>'x')::float,
                        'y', (box->>'y')::float,
                        'width', (box->>'width')::float,
                        'height', (box->>'height')::float
                    )
                )
                FROM jsonb_array_elements(annotation->'boundingBoxes') AS box
            )
        )
        WHERE annotation IS NOT NULL
    """))


def downgrade() -> None:
    """Revert annotations back to old schema (color field cannot be restored)."""
    conn = op.get_bind()
    
    conn.execute(sa.text("""
        UPDATE comment
        SET annotation = jsonb_build_object(
            'text', annotation->>'text',
            'boundingBoxes', (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'pageNumber', (box->>'page_number')::int,
                        'x', (box->>'x')::float,
                        'y', (box->>'y')::float,
                        'width', (box->>'width')::float,
                        'height', (box->>'height')::float
                    )
                )
                FROM jsonb_array_elements(annotation->'boundingBoxes') AS box
            )
        )
        WHERE annotation IS NOT NULL
    """))
