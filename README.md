# Headcount

## Backend

The Django backend uses uv and Python 3.15. From the project root:

```sh
cd backend
uv sync
test -e .env || cp .env.example .env
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Set `DJANGO_SECRET_KEY` in `.env` to the generated value. The local `.env` is ignored by Git; never commit secrets. An existing local `.env` already contains a development-only key, so do not overwrite it unless you intend to change the key.

```sh
uv run python manage.py migrate
uv run python manage.py runserver
```

The development server defaults to `http://127.0.0.1:8001/`. In VS Code, press F5 and select **Django: Run Server** to launch it with the debugger.

Users sign in with their email address and password. Create an administrator with `uv run python manage.py createsuperuser`.

The custom user model must be present before the first migration. If an existing database was migrated before the `users` app was added, Django will report an inconsistent migration history. Preserve that database and configure a fresh database using `DATABASE_URL` in `.env` before running migrations; migrating existing user data requires a separate data migration.

Development settings are the default. Configuration is read from `backend/.env`, with existing environment variables taking precedence. SQLite is the default database; `DATABASE_URL` can override it, but other database engines require their corresponding Python driver.

For deployment, set `DJANGO_SETTINGS_MODULE=core.settings.production`, provide a new secret in `DJANGO_SECRET_KEY`, and set `DJANGO_ALLOWED_HOSTS` to a comma-separated list of hostnames. Production defaults to HTTPS redirects and secure cookies. Configure HTTPS and any reverse proxy appropriately; enable HSTS with `DJANGO_SECURE_HSTS_SECONDS` only after confirming HTTPS works for the deployment. Run `uv run python manage.py check --deploy` and follow Django's deployment checklist before going live.

Run the backend tests with `uv run python manage.py test`.
