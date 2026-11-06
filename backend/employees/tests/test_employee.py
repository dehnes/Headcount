from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from employees.models import Employee


class EmployeeTests(SimpleTestCase):
    def make_employee(self, **overrides):
        fields = {
            "corp_id": 123456,
            "first_name": "Alex",
            "last_name": "Example",
            "email": "alex@example.com",
            "status": Employee.Status.ONBOARDING,
        }
        fields.update(overrides)
        return Employee(**fields)

    def test_valid_employee_and_corporate_id_boundaries(self):
        for corp_id in (1, 123456, 99999999):
            with self.subTest(corp_id=corp_id):
                employee = self.make_employee(corp_id=corp_id)
                employee.full_clean(validate_unique=False, validate_constraints=False)
                self.assertEqual(employee.corp_id, corp_id)
                self.assertEqual(str(employee), "Alex Example")
        self.assertTrue(Employee._meta.get_field("corp_id").unique)

    def test_invalid_corporate_ids(self):
        for corp_id in (0, -1, 100000000, "not-a-number"):
            with self.subTest(corp_id=corp_id), self.assertRaises(ValidationError):
                self.make_employee(corp_id=corp_id).full_clean(
                    validate_unique=False, validate_constraints=False
                )

    def test_invalid_status(self):
        with self.assertRaises(ValidationError):
            self.make_employee(status="unknown").full_clean(
                validate_unique=False, validate_constraints=False
            )

    def test_field_labels_and_automatic_timestamps(self):
        expected_labels = {
            "corp_id": "corporate ID",
            "first_name": "first name",
            "last_name": "last name",
            "email": "email address",
            "status": "employment status",
            "created_at": "created at",
            "updated_at": "updated at",
        }
        for field_name, label in expected_labels.items():
            with self.subTest(field=field_name):
                self.assertEqual(
                    Employee._meta.get_field(field_name).verbose_name, label
                )
        self.assertTrue(Employee._meta.get_field("created_at").auto_now_add)
        self.assertTrue(Employee._meta.get_field("updated_at").auto_now)
