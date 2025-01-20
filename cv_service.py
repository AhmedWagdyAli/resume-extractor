from models import Certificates, Skills, CV, Experiences
import re
from dateutil import parser
import datetime


class CVService:
    def __init__(self, db):
        self.db = db

    def save_cv(self, parsed_data):
        """Save parsed data into the database."""
        phone = parsed_data["phone_1"]
        email = parsed_data["email"]

        job_title = (
            parsed_data["professional_experience"][0]["profile"]
            .split(":")[0]
            .split(",")[0]
            .split("\n")[0]
            .split(" ")[0]
        )

        if len(job_title) > 50:
            job_title = job_title[:50]

        # Extract the first number from professional_experience_in_years
        experience_years_str = re.findall(
            r"\d+", str(parsed_data["professional_experience_in_years"])
        )
        experience_years = int(experience_years_str[0]) if experience_years_str else 0

        total_experience_months = 0
        if experience_years < 1:
            for experience in parsed_data["professional_experience"]:
                duration = experience["duration"]
                if "-" in duration:
                    start_date_str, end_date_str = duration.split("-")
                    start_date = parser.parse(start_date_str.strip())
                    if end_date_str.strip().lower() in ["present", "today"]:
                        end_date = datetime.datetime.now()
                    else:
                        end_date = parser.parse(end_date_str.strip())
                    months = (end_date.year - start_date.year) * 12 + (
                        end_date.month - start_date.month
                    )
                else:
                    years_months = re.findall(r"\d+", duration)
                    months = (
                        int(years_months[0]) * 12 + int(years_months[1])
                        if len(years_months) == 2
                        else 0
                    )
                total_experience_months += months
            parsed_data["professional_experience_in_years"] = (
                total_experience_months // 12
            )
        cv = CV(
            job_title=job_title,
            path_of_cv=parsed_data["path_of_cv"],
            years_of_experience=parsed_data["professional_experience_in_years"],
            phone=phone,
            email=email,
        )
        self.db.session.add(cv)
        self.db.session.flush()  # Get the ID for CV

        # Insert certificates
        """ for cert in parsed_data["education"]:
            if cert:
                certificate = Certificates(cv_id=cv.id, =cert)
                self.db.session.add(certificate)
        """
        # Insert skills
        for skill in parsed_data["skills"]:
            if skill:
                skill_entry = Skills(cv_id=cv.id, name=skill)
                self.db.session.add(skill_entry)

        for experience in parsed_data["professional_experience"]:
            if len(experience.get("profile")) > 255:
                experience["profile"] = experience.get("profile")[:255]
            experience_entry = Experiences(
                cv_id=cv.id,
                organisation_name=experience.get("organisation_name"),
                duration=experience.get("duration"),
                profile=experience.get("profile"),
            )
            self.db.session.add(experience_entry)
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
