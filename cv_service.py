from models import Education, Skills, CV, Experiences, Certificates, Projects, JobTitle
import re
from dateutil import parser
import datetime


class CVService:
    def __init__(self, db):
        self.db = db

    def save_cv(self, parsed_data):
        # Save parsed data into the database
        phone = parsed_data.get("phone_1")
        email = parsed_data.get("email")
        job_title = parsed_data.get("job_title", "").lower()

        if not job_title:
            job_title = "no job title"

        if len(job_title) > 50:
            job_title = job_title[:50]

        cv = CV(
            job_title=job_title,
            path_of_cv=parsed_data.get("path_of_cv"),
            path_of_coded_cv=parsed_data.get("path_of_coded_cv"),
            path_of_named_cv=parsed_data.get("path_of_named_cv"),
            path_of_original_cv=parsed_data.get("path_of_original_cv"),
            years_of_experience=parsed_data.get("professional_experience_in_years"),
            phone=phone,
            email=email,
        )
        self.db.session.add(cv)
        self.db.session.flush()  # Get the ID for CV

        # Insert common titles
        common_titles = parsed_data.get("common_titles", [])
        for title in common_titles:
            if title:
                job_title_entry = JobTitle(cv_id=cv.id, title=title)
                self.db.session.add(job_title_entry)

        # Insert skills
        for skill in parsed_data.get("skills", []):
            if skill:
                skill_entry = Skills(cv_id=cv.id, name=skill)
                self.db.session.add(skill_entry)

        for experience in parsed_data.get("professional_experience", []):
            if len(experience.get("profile", "")) > 255:
                experience["profile"] = experience.get("profile")[:255]
            experience_entry = Experiences(
                cv_id=cv.id,
                organisation_name=experience.get("organisation_name"),
                duration=experience.get("duration"),
                profile=experience.get("profile"),
                total_of_years_spent_at_job=experience.get("total_time_spent_at_job"),
            )
            self.db.session.add(experience_entry)

        for education in parsed_data.get("education", []):
            if len(education.get("institute_name", "")) > 255:
                education["institute_name"] = education.get("institute_name")[:255]
            education_entry = Education(
                cv_id=cv.id,
                institute_name=education.get("institute_name"),
                year_of_passing=education.get("year_of_passing"),
                score=education.get("score"),
            )
            self.db.session.add(education_entry)

        if parsed_data.get("projects"):
            for project in parsed_data.get("projects", []):
                if len(project.get("title", "")) > 255:
                    project["title"] = project.get("title")[:255]
                project_entry = Projects(
                    cv_id=cv.id,
                    title=project.get("title"),
                    duration_of_project=project.get("duration_of_project"),
                    date=project.get("date"),
                    description=project.get("description", "")[:255],
                )
                self.db.session.add(project_entry)

        # Commit to the database
        self.db.session.commit()
        return cv.id

    def get_cv(self, cv_id):
        cv = CV.query.filter_by(id=cv_id).first()

        if not cv:
            return "CV not found", 404

        # Fetch related objects using .all()
        skills = [skill.name for skill in cv.skills.all()]
        experiences = [exp for exp in cv.experiences.all()]

        if cv:
            return cv, skills, experiences
        return None
