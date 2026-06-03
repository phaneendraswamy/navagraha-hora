"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def json_type():
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    decision_status = sa.Enum("NEW", "SAVED", "SKIPPED", "APPROVED", name="decisionstatus")
    decision_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "raw_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("source_job_id", sa.String(length=255), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("payload", json_type(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_raw_jobs_source"), "raw_jobs", ["source"], unique=False)
    op.create_index(op.f("ix_raw_jobs_source_job_id"), "raw_jobs", ["source_job_id"], unique=False)

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("skills", json_type(), nullable=False),
        sa.Column("preferred_roles", json_type(), nullable=False),
        sa.Column("preferred_locations", json_type(), nullable=False),
        sa.Column("experience_years", sa.Float(), nullable=False),
        sa.Column("tooling", json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("raw_job_id", sa.String(length=36), nullable=True),
        sa.Column("job_id", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("employment_type", sa.String(length=120), nullable=False),
        sa.Column("salary", sa.String(length=255), nullable=False),
        sa.Column("skills", json_type(), nullable=False),
        sa.Column("experience_required", sa.String(length=255), nullable=False),
        sa.Column("jd_text", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("posted_date", sa.String(length=80), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("match_percentage", sa.Float(), nullable=False),
        sa.Column("match_details", json_type(), nullable=False),
        sa.Column("jd_insights", json_type(), nullable=False),
        sa.Column("decision_status", decision_status, nullable=False),
        sa.ForeignKeyConstraint(["raw_job_id"], ["raw_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jobs_company"), "jobs", ["company"], unique=False)
    op.create_index(op.f("ix_jobs_decision_status"), "jobs", ["decision_status"], unique=False)
    op.create_index(op.f("ix_jobs_job_id"), "jobs", ["job_id"], unique=False)
    op.create_index(op.f("ix_jobs_source"), "jobs", ["source"], unique=False)
    op.create_index("ix_jobs_source_job_id", "jobs", ["source", "job_id"], unique=True)
    op.create_index(op.f("ix_jobs_title"), "jobs", ["title"], unique=False)

    op.create_table(
        "applications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_applications_job_id"), "applications", ["job_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_applications_job_id"), table_name="applications")
    op.drop_table("applications")
    op.drop_index(op.f("ix_jobs_title"), table_name="jobs")
    op.drop_index("ix_jobs_source_job_id", table_name="jobs")
    op.drop_index(op.f("ix_jobs_source"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_job_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_decision_status"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_company"), table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("user_profiles")
    op.drop_index(op.f("ix_raw_jobs_source_job_id"), table_name="raw_jobs")
    op.drop_index(op.f("ix_raw_jobs_source"), table_name="raw_jobs")
    op.drop_table("raw_jobs")
    sa.Enum(name="decisionstatus").drop(op.get_bind(), checkfirst=True)

