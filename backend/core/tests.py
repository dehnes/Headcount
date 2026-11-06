import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command, get_commands, load_command_class
from django.test import SimpleTestCase


class SettingsTests(SimpleTestCase):
    def check_settings(self, module, assertions):
        environment = os.environ.copy()
        environment.update(
            {
                "DJANGO_SETTINGS_MODULE": module,
                "DJANGO_SECRET_KEY": "test-secret-from-environment",
                "DJANGO_ALLOWED_HOSTS": "example.com",
            }
        )
        environment.pop("DJANGO_DEBUG", None)
        environment.pop("DJANGO_SECURE_SSL_REDIRECT", None)
        environment.pop("DATABASE_URL", None)
        subprocess.run(
            [sys.executable, "-c", "from django.conf import settings\n" + assertions],
            cwd=Path(__file__).resolve().parent.parent,
            env=environment,
            check=True,
        )

    def test_development_settings(self):
        self.check_settings(
            "core.settings.development",
            "assert settings.DEBUG is True\n"
            "assert settings.SECRET_KEY == 'test-secret-from-environment'\n"
            "assert settings.ALLOWED_HOSTS == ['example.com']\n"
            "assert settings.DATABASES['default']['NAME'] == str(settings.BASE_DIR / 'db.sqlite3')",
        )

    def test_production_settings(self):
        self.check_settings(
            "core.settings.production",
            "assert settings.DEBUG is False\n"
            "assert settings.SECRET_KEY == 'test-secret-from-environment'\n"
            "assert settings.ALLOWED_HOSTS == ['example.com']\n"
            "assert settings.SECURE_SSL_REDIRECT is True\n"
            "assert settings.SESSION_COOKIE_SECURE is True\n"
            "assert settings.CSRF_COOKIE_SECURE is True",
        )


class RunserverTests(SimpleTestCase):
    def test_default_and_explicit_ports(self):
        self.assertEqual(get_commands()["runserver"], "core")
        for arguments, expected_port in (((), "8001"), (("127.0.0.1:8123",), "8123")):
            with self.subTest(arguments=arguments):
                command = load_command_class("core", "runserver")
                with patch.object(command, "run"):
                    call_command(command, *arguments)
                self.assertEqual(command.port, expected_port)
