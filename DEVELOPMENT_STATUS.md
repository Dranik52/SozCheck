# Development status

## Completed

- Architecture approved; product name set to SözCheck.
- Django 6.1 project, six domain apps, environment-specific settings, custom user model, PostgreSQL URL support, and SQLite local fallback.
- Account registration, login, logout, project CRUD, owner/member access, and owner-managed project membership.
- CSV and nested JSON parsing with configurable CSV columns, validation reports, UTF-8 checks, duplicate and empty-value detection, and 5 MB limit.
- Original uploads stored under generated safe paths with SHA-256 hashes; project deletion removes its associated private files.
- Structured OpenAI Responses and Gemini Interactions provider adapters, schema validation, prompt versioning, placeholder and length checks, and stored analysis history.
- Dashboard metrics, filtered/paginated localization table, project-scoped analysis details, and review queue.
- Human approval, rejection, manual editing, and append-only review records with actor and timestamp.
- Simulated UI components for game buttons, dialogue, character messages, settings, rewards, and quests, with language switching and overflow warnings.
- CSV and JSON downloads preserve unmapped CSV columns or nested JSON structure, apply approved corrections on request, and block placeholder damage.
- README, environment example, requirements, Django admin views, and `.gitignore`.

## Verification

- Dependencies installed in `.venv`: Django 6.1.2, django-environ 0.14.0, psycopg 3.3.6.
- `manage.py check`: passed.
- All migrations applied locally with SQLite; `makemigrations --check --dry-run`: no changes detected.
- Automated Django suite: 41 tests passed, including uploads, access control, analysis validation, review decisions, simulator access, and exports.
- Local server started successfully; landing and signup returned HTTP 200, and unauthenticated dashboard correctly redirected to login.
- Provider SDKs are optional and are not installed in the core environment.

## Current limits

- OpenAI and Gemini API calls have not been live-tested because no API credentials were supplied. Install `requirements/ai.txt` and configure `.env` to enable provider analysis.
- PostgreSQL has not been exercised in this environment; local verification used SQLite.
- File imports are capped at 5 MB and processed synchronously. Larger uploads need background jobs before production use.
- Reviewer accounts must already be registered before the project owner can add them.
- XML, bulk analysis, password reset email delivery, and API endpoints are outside this MVP.

## Recommended next step

- Configure a PostgreSQL database and an AI provider key, then run the end-to-end upload, analyze, review, and export demonstration with a representative localization file.
