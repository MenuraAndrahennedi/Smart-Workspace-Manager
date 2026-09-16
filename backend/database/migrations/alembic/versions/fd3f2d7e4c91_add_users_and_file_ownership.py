"""add users and file ownership

Revision ID: fd3f2d7e4c91
Revises: 9883f709a4d2
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fd3f2d7e4c91"
down_revision: Union[str, Sequence[str], None] = "9883f709a4d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEGACY_USER_EMAIL = "legacy@local.invalid"
LEGACY_PASSWORD_HASH = "legacy-user-created-by-migration"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("email"),
    )

    op.execute(
        sa.text(
            """
            INSERT INTO users (email, password_hash)
            VALUES (:email, :password_hash)
            """
        ).bindparams(
            email=LEGACY_USER_EMAIL,
            password_hash=LEGACY_PASSWORD_HASH,
        )
    )

    with op.batch_alter_table("files") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE files
            SET user_id = (
                SELECT id FROM users WHERE email = :email
            )
            WHERE user_id IS NULL
            """
        ).bindparams(email=LEGACY_USER_EMAIL)
    )

    with op.batch_alter_table("files") as batch_op:
        batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_index("ix_files_user_id", ["user_id"])
        batch_op.create_foreign_key(
            "fk_files_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("files") as batch_op:
        batch_op.drop_constraint("fk_files_user_id_users", type_="foreignkey")
        batch_op.drop_index("ix_files_user_id")
        batch_op.drop_column("user_id")

    op.drop_table("users")
