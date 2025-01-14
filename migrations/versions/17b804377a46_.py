"""empty message

Revision ID: 17b804377a46
Revises: 
Create Date: 2025-01-13 14:10:33.224009

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '17b804377a46'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('cv',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_title', sa.String(length=255), nullable=True),
    sa.Column('years_of_experience', sa.String(length=255), nullable=True),
    sa.Column('path_of_cv', sa.String(length=255), nullable=False),
    sa.Column('phone', sa.String(length=255), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('certificates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cv_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.ForeignKeyConstraint(['cv_id'], ['cv.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('education',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cv_id', sa.Integer(), nullable=False),
    sa.Column('institute_name', sa.String(length=255), nullable=True),
    sa.Column('year_of_passing', sa.Integer(), nullable=True),
    sa.Column('score', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['cv_id'], ['cv.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('experiences',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cv_id', sa.Integer(), nullable=False),
    sa.Column('organisation_name', sa.String(length=255), nullable=True),
    sa.Column('profile', sa.String(length=255), nullable=True),
    sa.Column('duration', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['cv_id'], ['cv.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('skills',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cv_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.ForeignKeyConstraint(['cv_id'], ['cv.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('skills')
    op.drop_table('experiences')
    op.drop_table('education')
    op.drop_table('certificates')
    op.drop_table('cv')
    # ### end Alembic commands ###
