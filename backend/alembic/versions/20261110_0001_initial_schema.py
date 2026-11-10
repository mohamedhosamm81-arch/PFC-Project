"""Initial PFC schema: users, sessions, tickets, audit trail, rooms, sequence.

Revision ID: 20261110_0001
Revises:
Create Date: 2026-11-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261110_0001"
down_revision = None
branch_labels = None
depends_on = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}

USER_ROLE = sa.Enum(
    "admin",
    "reception",
    "doctor",
    "branch_staff",
    name="user_role",
)
LOCATION = sa.Enum(
    "Reception",
    "CMO",
    "Pharmacy",
    "Laboratory",
    "Radiology",
    "Cashier",
    name="location",
)
TICKET_STATUS = sa.Enum(
    "WAITING",
    "SERVING",
    "LATE",
    "DONE",
    name="ticket_status",
)
TRANSFER_ACTION = sa.Enum(
    "ISSUED",
    "SERVING",
    "TRANSFER",
    "LATE",
    "RECALL",
    "DONE",
    name="transfer_action",
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("role", USER_ROLE, nullable=False),
        sa.Column("assigned_station", LOCATION, nullable=True),
        sa.Column(
            "default_shift_start",
            sa.Time(),
            server_default=sa.text("'08:00:00'"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(role = 'admin' AND assigned_station IS NULL) OR "
            "(role <> 'admin' AND assigned_station IS NOT NULL)",
            name="ck_users_role_station",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_users_username"),
        **TABLE_OPTIONS,
    )
    op.create_index("ix_users_role_active", "users", ["role", "is_active"], unique=False)

    op.create_table(
        "ticket_sequence",
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("next_ticket_code", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.CheckConstraint("id = 1", name="ck_ticket_sequence_singleton"),
        sa.CheckConstraint(
            "next_ticket_code BETWEEN 1 AND 999",
            name="ck_ticket_sequence_code_range",
        ),
        sa.PrimaryKeyConstraint("id"),
        **TABLE_OPTIONS,
    )

    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("floor_number", sa.SmallInteger(), nullable=False),
        sa.Column("station", LOCATION, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.CheckConstraint("floor_number > 0", name="ck_rooms_floor_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_rooms_code"),
        **TABLE_OPTIONS,
    )
    op.create_index(
        "ix_rooms_floor_station", "rooms", ["floor_number", "station"], unique=False
    )

    op.create_table(
        "employee_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("station", LOCATION, nullable=False),
        sa.Column("shift_start_scheduled", sa.DateTime(), nullable=False),
        sa.Column("start_session_at", sa.DateTime(), nullable=False),
        sa.Column("end_session_at", sa.DateTime(), nullable=True),
        sa.Column(
            "is_late_start", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "late_minutes", sa.SmallInteger(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "active_user_id",
            sa.Integer(),
            sa.Computed(
                "CASE WHEN end_session_at IS NULL THEN user_id ELSE NULL END",
                persisted=True,
            ),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "late_minutes >= 0", name="ck_employee_sessions_late_nonnegative"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_employee_sessions_user",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        **TABLE_OPTIONS,
    )
    op.create_index(
        "ix_employee_sessions_user_start",
        "employee_sessions",
        ["user_id", "start_session_at"],
        unique=False,
    )
    op.create_index(
        "ix_employee_sessions_start",
        "employee_sessions",
        ["start_session_at"],
        unique=False,
    )
    op.create_index(
        "uq_employee_sessions_active_user",
        "employee_sessions",
        ["active_user_id"],
        unique=True,
    )

    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticket_code", sa.SmallInteger(), nullable=False),
        sa.Column("initial_destination", LOCATION, nullable=False),
        sa.Column("current_location", LOCATION, nullable=False),
        sa.Column(
            "status",
            TICKET_STATUS,
            server_default=sa.text("'WAITING'"),
            nullable=False,
        ),
        sa.Column(
            "is_overbooked", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("assigned_user_id", sa.Integer(), nullable=True),
        sa.Column("late_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "active_ticket_code",
            sa.SmallInteger(),
            sa.Computed(
                "CASE WHEN status <> 'DONE' THEN ticket_code ELSE NULL END",
                persisted=True,
            ),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "ticket_code BETWEEN 1 AND 999", name="ck_tickets_code_range"
        ),
        sa.CheckConstraint(
            "initial_destination <> 'Cashier'",
            name="ck_tickets_cashier_not_initial",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_user_id"],
            ["users.id"],
            name="fk_tickets_assigned_user",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        **TABLE_OPTIONS,
    )
    op.create_index(
        "ix_tickets_current_location_status",
        "tickets",
        ["current_location", "status"],
        unique=False,
    )
    op.create_index("ix_tickets_ticket_code", "tickets", ["ticket_code"], unique=False)
    op.create_index("ix_tickets_created_at", "tickets", ["created_at"], unique=False)
    op.create_index(
        "ix_tickets_assigned_user", "tickets", ["assigned_user_id"], unique=False
    )
    op.create_index(
        "uq_tickets_active_ticket_code",
        "tickets",
        ["active_ticket_code"],
        unique=True,
    )

    op.create_table(
        "ticket_transfers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("from_location", LOCATION, nullable=True),
        sa.Column("to_location", LOCATION, nullable=True),
        sa.Column("transferred_by", sa.Integer(), nullable=False),
        sa.Column(
            "transferred_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column("action_type", TRANSFER_ACTION, nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            name="fk_ticket_transfers_ticket",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["transferred_by"],
            ["users.id"],
            name="fk_ticket_transfers_user",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        **TABLE_OPTIONS,
    )
    op.create_index(
        "ix_ticket_transfers_ticket_time",
        "ticket_transfers",
        ["ticket_id", "transferred_at"],
        unique=False,
    )
    op.create_index(
        "ix_ticket_transfers_action", "ticket_transfers", ["action_type"], unique=False
    )

    op.execute(
        sa.text(
            "INSERT INTO ticket_sequence (id, next_ticket_code) VALUES (1, 1)"
        )
    )


def downgrade() -> None:
    op.drop_table("ticket_transfers")
    op.drop_table("tickets")
    op.drop_table("employee_sessions")
    op.drop_table("ticket_sequence")
    op.drop_table("rooms")
    op.drop_table("users")
