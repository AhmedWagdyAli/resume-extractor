from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class CV(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(255), nullable=True)
    years_of_experience = db.Column(db.String(255), nullable=True)
    path_of_cv = db.Column(db.String(255), nullable=False)
    path_of_coded_cv = db.Column(db.String(255), nullable=True)
    path_of_named_cv = db.Column(db.String(255), nullable=True)
    path_of_original_cv = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    certificates = db.relationship(
        "Certificates", backref="cv", cascade="all, delete-orphan", lazy="dynamic"
    )
    skills = db.relationship(
        "Skills", backref="cv", cascade="all, delete-orphan", lazy="dynamic"
    )
    experiences = db.relationship(
        "Experiences", backref="cv", cascade="all, delete-orphan", lazy="dynamic"
    )
    projects = db.relationship(
        "Projects", backref="cv", cascade="all, delete-orphan", lazy="dynamic"
    )
    job_titles = db.relationship(
        "JobTitle", backref="cv", cascade="all, delete-orphan", lazy="dynamic"
    )

    def __repr__(self):
        return f"<CV id={self.id}, job_title={self.job_title}, path_of_cv={self.path_of_cv}>"


class JobTitle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cv_id = db.Column(
        db.Integer, db.ForeignKey("cv.id", ondelete="CASCADE"), nullable=False
    )
    title = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<JobTitle id={self.id}, title={self.title}>"


class Certificates(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cv_id = db.Column(
        db.Integer, db.ForeignKey("cv.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(255), nullable=False)


class Skills(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cv_id = db.Column(
        db.Integer, db.ForeignKey("cv.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(255), nullable=False)


class Experiences(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cv_id = db.Column(
        db.Integer, db.ForeignKey("cv.id", ondelete="CASCADE"), nullable=False
    )
    organisation_name = db.Column(db.String(255), nullable=True)
    profile = db.Column(db.String(255), nullable=True)
    duration = db.Column(db.String(255), nullable=True)
    total_of_years_spent_at_job = db.Column(db.String(255), nullable=True)


class Education(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cv_id = db.Column(
        db.Integer, db.ForeignKey("cv.id", ondelete="CASCADE"), nullable=False
    )
    institute_name = db.Column(db.String(255), nullable=True)
    year_of_passing = db.Column(db.String(255), nullable=True)
    score = db.Column(db.String(255), nullable=True)


class Projects(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cv_id = db.Column(
        db.Integer, db.ForeignKey("cv.id", ondelete="CASCADE"), nullable=False
    )
    item = db.Column(db.String(255), nullable=True)
    duration_of_project = db.Column(db.String(255), nullable=True)
    description = db.Column(db.String(255), nullable=True)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
