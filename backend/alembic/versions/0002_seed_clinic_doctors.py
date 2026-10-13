"""seed the clinic's doctor roster

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13 10:05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DOCTORS = [
    {"full_name": "Dr. Meera Iyer", "specialty": "Cardiology", "room": "B-204"},
    {"full_name": "Dr. Rohan Kapoor", "specialty": "Orthopaedics", "room": "A-112"},
    {"full_name": "Dr. Sana Qureshi", "specialty": "Dermatology", "room": "C-018"},
    {"full_name": "Dr. Vikram Reddy", "specialty": "General Medicine", "room": "A-101"},
    {"full_name": "Dr. Priya Menon", "specialty": "Paediatrics", "room": "D-007"},
    {"full_name": "Dr. Arjun Bose", "specialty": "Neurology", "room": "B-310"},
]

doctors_table = sa.table(
    "doctors",
    sa.column("full_name", sa.String),
    sa.column("specialty", sa.String),
    sa.column("room", sa.String),
)


def upgrade() -> None:
    op.bulk_insert(doctors_table, DOCTORS)


def downgrade() -> None:
    names = [d["full_name"] for d in DOCTORS]
    op.execute(doctors_table.delete().where(doctors_table.c.full_name.in_(names)))
