from unittest.mock import Mock

from django.contrib import admin
from django.test import RequestFactory, SimpleTestCase

from employees.admin.employee import EmployeeAdmin
from employees.models import Employee


class EmployeeAdminTests(SimpleTestCase):
    def setUp(self):
        self.employee_admin = admin.site._registry[Employee]

    def test_employee_admin_is_registered(self):
        self.assertIsInstance(self.employee_admin, EmployeeAdmin)
        self.assertEqual(
            self.employee_admin.list_display,
            ("corp_id", "first_name", "last_name", "email", "status"),
        )
        self.assertEqual(self.employee_admin.list_filter, ("status",))
        self.assertEqual(
            self.employee_admin.readonly_fields, ("created_at", "updated_at")
        )

    def test_admin_form_and_search(self):
        request = RequestFactory().get("/admin/employees/employee/")
        request.user = Mock()
        request.user.has_perm.return_value = True

        form = self.employee_admin.get_form(request)
        self.assertEqual(
            set(form.base_fields),
            {"corp_id", "first_name", "last_name", "email", "status"},
        )
        for search in ("123", "Alex"):
            with self.subTest(search=search):
                queryset, _ = self.employee_admin.get_search_results(
                    request, Employee.objects.all(), search
                )
                self.assertIn("corp_id", str(queryset.query))
