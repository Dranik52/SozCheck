# SözCheck

SözCheck is a game localization quality assurance platform for English-to-Kazakh and English-to-Uzbek text. It flags possible issues, explains suggestions, and keeps correction decisions with human reviewers. An AI result is never presented as native-speaker verified.

## MVP features

- Account registration, login, project ownership, and project member roles.
- Project creation and editing with game genre and context.
- UTF-8 CSV and nested JSON uploads, configurable CSV columns, validation reports, and unchanged private originals.
- Translation table with search, language, issue, severity, and analysis-status filters.
- Provider-independent OpenAI and Google Gemini analysis adapters with validated structured responses.
- Deterministic placeholder and character-limit checks.
- Human review queue with approve, reject, edit, and an audit trail.
- Simulated game UI previews for buttons, dialogue, character messages, settings, rewards, and quests.
- CSV/JSON exports that preserve extra CSV columns or nested JSON paths, apply approved human corrections, and validate placeholders.

## Technology

- Python 3.12+
- Django 6.1
- PostgreSQL in production; SQLite fallback for local development
- Django Templates, HTML, CSS, and vanilla JavaScript

## Setup

Run from the project root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The app opens at http://127.0.0.1:8000. With a blank `DATABASE_URL`, development uses SQLite. To use PostgreSQL locally, create a database and role, then set `DATABASE_URL` in `.env`, for example:

```text
DATABASE_URL=postgres://sozcheck:your-password@localhost:5432/sozcheck
```

For production, set `DJANGO_SETTINGS_MODULE=config.settings.production`, a generated `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`, and a PostgreSQL `DATABASE_URL`. Production settings refuse the sample secret. Never commit `.env`, database files, or uploaded localization data.

## AI provider setup

Install the SDK(s) you plan to use:

```powershell
python -m pip install -r requirements/ai.txt
```

Set `AI_PROVIDER=openai` or `AI_PROVIDER=gemini` and the matching API key in `.env`. Optional model overrides are `OPENAI_MODEL` and `GEMINI_MODEL`. Keys stay on the server and are not included in browser JavaScript. Provider calls have not been live-tested because no API credentials were supplied.

If no provider is configured, deterministic placeholder and text-length checks remain available. Other AI analyses show a clear configuration error and do not create fabricated results.

## Database notes

The initial migration is applied with `python manage.py migrate`. For PostgreSQL backups, use the database team's normal `pg_dump` schedule and test restores; uploaded originals are stored separately under `media/` and should be included in the deployment's protected backup policy.

## Tests

Run the automated Django suite:

```powershell
python manage.py test
```

Tests mock provider behavior and never make live AI requests.

## Development status

See [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md) for the completed stages, checks, current limits, and next steps.
