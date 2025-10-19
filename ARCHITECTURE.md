Appraise — ARCHITECTURE

Overview
--------
Appraise is a Django-based web application that provides an evaluation platform for annotation tasks. It is organized as a standard Django project with multiple apps, a small set of models for users, profiles, tasks and agendas, and a server-rendered UI using Django templates and Bootstrap (legacy v3).

High-level components
---------------------
- Django (project): central framework responsible for request routing, ORM, templating, authentication, sessions, and management commands.
  - Project root: `Appraise/` — contains core settings and WSGI entrypoint.
  - Apps: `Dashboard`, `EvalView`, `EvalData`, `Campaign`, etc.

- Authentication / user model
  - Uses Django's built-in `auth.User` model for accounts.
  - Extended user metadata is stored in `Dashboard.models.UserProfile` (OneToOne with User) which includes the `crowdee_user_id` field used for external integration.
  - A custom middleware `Appraise.middleware.CrowdeeAuthMiddleware` (runtime-registered in `Appraise/settings.py`) implements a lightweight "query-parameter SSO" for testing/crowd integration. Behavior:
    - If a request contains `?user_id=<id>` and the requester is not a superuser, middleware finds a `UserProfile` with `crowdee_user_id=<id>` or creates a `User` and `UserProfile` when missing.
    - The user is added to a default `Group` named `default` and logged in via `django.contrib.auth.login()` (the middleware sets `user.backend = 'django.contrib.auth.backends.ModelBackend'`).
    - The middleware also writes `crowdee_user_id`, `param_p` and `task_id` into `request.session` and sets a session flag `hide_ui` so templates can hide the standard site chrome for crowd tasks.
  - Note: this query-param auth flow is intentionally minimal and should not be used for public production deployments.

- Models of note
  - `auth.User` — built-in Django User model.
  - `Dashboard.models.UserProfile` — extends User with `crowdee_user_id` (unique, string) and related user sessions `UserTaskSession`.
  - Task models live under `EvalData` and define the task behavior (assignment, results, session tracking). `TaskAgenda` maps work assignments to users.

- Views & templates
  - Server-side rendering with Django templates. The main layout is `Dashboard/templates/Dashboard/base.html`. The dashboard lives in `Dashboard/templates/Dashboard/dashboard.html`.
  - Templates receive a `BASE_CONTEXT` from `Appraise/settings` and `dashboard` view computes per-user context (current task, languages, progress).
  - UI hiding: `base.html` and `dashboard.html` inspect `request.session.hide_ui` (or the immediate `hide_menu_bar` context when `?user_id` is present) to hide the navbar, title and footer and to show a bottom status bar.

- Logging
  - General application logs: `appraise.log` (configured in `Appraise/settings.py` via `LOG_HANDLER`).
  - Middleware-specific logs: `middleware.log` (separate rotating handler `MIDDLEWARE_LOG_HANDLER`).
  - `Appraise.utils._get_logger()` returns configured loggers used across the project.
  - A management command `python manage.py tail_middleware_log` was added to tail and filter `middleware.log` for debugging.

- Persistent storage
  - SQLite is used by default for local/dev. `Appraise/settings.py` selects the DB file path:
    - If environment variables for a full DB are provided (APPRAISE_DB_*), they are used (e.g., Postgres connection strings).
    - Otherwise, if `/data` exists (container mount), the DB is `/data/db.sqlite3` so a mounted host directory persists the DB file.
    - If `/data` does not exist, default is `BASE_DIR/db.sqlite3`.
  - In Docker setup, `docker-compose.yml` mounts the host `./data` directory to the container `/data`, ensuring `db.sqlite3` persists between container restarts.

- Docker and deployment (dev-focused)
  - `Dockerfile` builds a python:3.12-slim image, installs requirements, creates a non-root `app` user, copies the project, runs `collectstatic` (best-effort) and exposes port 8000.
  - The container entrypoint runs migrations then starts Django's development server `python manage.py runserver 0.0.0.0:8000` (development mode; for production replace with gunicorn/uWSGI and a production DB).
  - `docker-compose.yml` maps `./data:/data` (DB persistence) and `./static:/app/static` (optional static persistence) and exposes port 8000.

Security considerations
-----------------------
- The query-param authentication (`?user_id=...`) is insecure for public production use because:
  - It creates users without passwords, effectively trusting the query parameter caller.
  - No additional verification (signature/tokens) is performed.
- Recommended for production:
  - Replace the query-param flow with an SSO/OAuth2 flow (e.g., OAuth, SAML, or an internal token exchange).
  - Use a production DB (Postgres) instead of SQLite for concurrency and durability.
  - Use a proper WSGI server (gunicorn) behind a reverse proxy and TLS termination.
  - Harden logging and rotate/ship logs to a central logging service.

Operational notes
-----------------
- Status bar behavior: When `request.session.hide_ui` is set (via middleware), a fixed bottom status bar displays `crowdee_user_id`, `task_id` and `param_p` values for the online annotator. The flag persists in session until the session is cleared (log out or clear cookies). You can make it dismissible by updating the session via a small AJAX call.

- Middleware logging: the middleware logs lookup/create/login/session operations to both `appraise.log` and `middleware.log`. The new management command `tail_middleware_log` helps you filter by `crowdee_user_id` or follow updates.

- Where to find key code
  - `Appraise/settings.py` — DB selection, middleware registration, logging handlers
  - `Appraise/middleware.py` — `CrowdeeAuthMiddleware` (user-by-query behavior and session writes)
  - `Dashboard/models.py` — `UserProfile`, `UserTaskSession` and other user-related models
  - `Dashboard/views.py` — dashboard view and `get_user_from_query` helper
  - `Dashboard/templates/Dashboard/base.html` — main layout and status bar
  - `Appraise/management/commands/tail_middleware_log.py` — management command to tail middleware log

Development and testing notes
-----------------------------
- Use the Docker setup for quick local testing. Ensure the host `./data` directory exists and is writable so SQLite persists.
- For unit tests: There are various `tests.py` files in apps. You can run Django tests inside the container with:

```bash
docker-compose exec web python manage.py test
```

- To debug a specific `crowdee_user_id` flow, reproduce a request with `?user_id=123&param_p=...&task_id=...` and then run:

```bash
python manage.py tail_middleware_log --follow --filter 123
# or inside container
docker-compose exec web python manage.py tail_middleware_log --follow --filter 123
```

Closing
-------
This architecture is optimized for local development and testing. If you need I can:
- Replace the dev server with gunicorn and add a production-ready docker-compose stack with Postgres.
- Add a small dismiss button to the UI that clears the `hide_ui` session key.
- Add more structured JSON logging and log forwarding (Fluentd/Logstash) for production observability.

If you want any of these changes implemented now, tell me which and I will make the edits and run tests.

