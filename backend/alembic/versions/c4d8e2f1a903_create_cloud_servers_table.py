"""create cloud servers table for feature gating demo

Revision ID: c4d8e2f1a903
Revises: 76a2986cfdf6
Create Date: 2026-10-11 02:26:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4d8e2f1a903'
down_revision: Union[str, None] = '76a2986cfdf6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'cloud_servers',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('region', sa.String(length=50), nullable=False, server_default='ap-south-1'),
        sa.Column('vcpus', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('ram_gb', sa.Integer(), nullable=False, server_default='4'),
        sa.Column('has_load_balancer', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='RUNNING'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cloud_servers_customer_id'), 'cloud_servers', ['customer_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_cloud_servers_customer_id'), table_name='cloud_servers')
    op.drop_table('cloud_servers')
