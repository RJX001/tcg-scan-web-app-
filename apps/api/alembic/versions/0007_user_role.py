"""user role + account numbers

Revision ID: 0007_user_role
Revises: 0006_user_comps_days
Create Date: 2026-06-12

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_user_role"
down_revision: str | None = "0006_user_comps_days"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS user_account_seq START 10")

    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(32),
            nullable=False,
            server_default="user",
        ),
    )
    op.add_column("users", sa.Column("account_seq", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("account_number", sa.String(16), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM users ORDER BY created_at")).fetchall()
    for row in rows:
        seq = conn.execute(sa.text("SELECT nextval('user_account_seq')")).scalar()
        conn.execute(
            sa.text("UPDATE users SET account_seq=:s, account_number=:n WHERE id=:i"),
            {"s": seq, "n": f"{seq:06d}", "i": row[0]},
        )

    op.alter_column("users", "account_seq", nullable=False)
    op.alter_column("users", "account_number", nullable=False)
    op.create_unique_constraint("uq_users_account_seq", "users", ["account_seq"])
    op.create_unique_constraint("uq_users_account_number", "users", ["account_number"])
    op.create_index("ix_users_account_number", "users", ["account_number"])

    op.execute(
        "UPDATE users SET role = 'owner' WHERE email = 'RJ_OWNER_EMAIL_HERE'"
    )


def downgrade() -> None:
    op.drop_index("ix_users_account_number", table_name="users")
    op.drop_constraint("uq_users_account_number", "users", type_="unique")
    op.drop_constraint("uq_users_account_seq", "users", type_="unique")
    op.drop_column("users", "account_number")
    op.drop_column("users", "account_seq")
    op.drop_column("users", "role")
    op.execute("DROP SEQUENCE IF EXISTS user_account_seq")
