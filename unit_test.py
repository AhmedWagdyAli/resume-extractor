import unittest
from unittest.mock import MagicMock
from models import CV, Skills, Experiences, db
from cv_service import CVService
from flask import Flask


class CVServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.db = db
        self.app.config["SQLALCHEMY_DATABASE_URI"] = (
            "mysql+mysqlconnector://cvflask_user:password@localhost:3306/cvflask"
        )
        db.init_app(self.app)

        self.cv_service = CVService(self.db)

        # Mock data
        self.cv_mock = CV(
            id=50,
            job_title="Developer",
            phone="1235067890",
            email="test@example.com",
            path_of_cv="test.pdf",
        )
        self.skills_mock = [
            Skills(cv_id=50, name="Python"),
            Skills(cv_id=50, name="Django"),
        ]
        self.experiences_mock = [
            Experiences(cv_id=50, organisation_name="Test Company")
        ]

        # Mock the database queries
        CV.query.filter_by = MagicMock(
            return_value=MagicMock(first=MagicMock(return_value=self.cv_mock))
        )
        Skills.query.filter_by = MagicMock(return_value=self.skills_mock)
        Experiences.query.filter_by = MagicMock(return_value=self.experiences_mock)
        # Insert mock data into the database
        """  self.db.session.add(self.cv_mock)
        self.db.session.add_all(self.skills_mock)
        self.db.session.add_all(self.experiences_mock)
        self.db.session.commit() """

    def tearDown(self):
        db.session.remove()
        self.app_context.pop()

    def test_save_cv(self):
        cv_data = {
            "job_title": "Developer",
            "phone": "1235067890",
            "email": "d",
            "path_of_cv": "test.pdf",
            "skills": ["Python", "Django"],
            "experiences": [
                {
                    "organisation_name": "Test Company",
                    "duration": "2 years",
                    "profile": "Test profile",
                }
            ],
        }
        cv_id = self.cv_service.save_cv(cv_data)
        self.assertEqual(cv_id, 50)

    def test_get_cv(self):
        cv_id = 50
        cv, skills, experiences = self.cv_service.get_cv(cv_id)
        print(cv, skills, experiences)
        self.assertEqual(cv, self.cv_mock)
        self.assertEqual([skill for skill in skills], ["Python", "Django"])
        self.assertEqual(len(experiences), 1)
        self.assertEqual(experiences[0].organisation_name, "Test Company")


if __name__ == "__main__":
    unittest.main()
