Appraise — INSTRUCTIONS

This document explains how to set up and run the Appraise evaluation system locally using Docker (recommended) and how to troubleshoot the common issues. It assumes you have Docker and docker-compose installed.

Quick summary (copy/paste)

1) Prepare host folders and DB file

```bash
cd /home/berko/github/Appraise-Crowdee
mkdir -p data static
# optional: create empty sqlite file (container can create it too)
touch data/db.sqlite3
# ensure writable by container (convenient way)
chmod 666 data/db.sqlite3 || true
```

2) Build and run with docker-compose

```bash
docker-compose up -d --build
```

3) Follow logs

```bash
docker-compose logs -f web
```

4) Visit the app

Open in your browser:

http://127.0.0.1:8000/

----

Detailed steps

Prerequisites
- Docker (20.x+) and docker-compose
- A POSIX shell (bash) for the commands below

Prepare the project and persistent data directory
- The provided `docker-compose.yml` mounts the host `./data` directory into the container at `/data`. The Django settings prefer `/data/db.sqlite3` if `/data` exists. To make the SQLite database persistent, create the `data/` folder on the host and either create an empty `db.sqlite3` file or let Django create it on first migration.

Commands:

```bash
cd /path/to/Appraise-Crowdee
mkdir -p data static
# create DB file if you want to pre-create it
touch data/db.sqlite3
chmod 666 data/db.sqlite3 || true
```

Build and run

```bash
docker-compose up -d --build
```

What the container does on startup
- The Dockerfile runs `python manage.py migrate --noinput` and then starts the Django development server on 0.0.0.0:8000. This will create DB tables in `/data/db.sqlite3` (the mounted file). Static files are optionally mounted at `/app/static`.

Access the app
- Web UI: http://127.0.0.1:8000/

Special query-parameter authentication flow (used for crowd workers / testing)
- The app supports a simple query-param SSO-like flow for evaluation/testing. If an incoming request has `?user_id=<id>`, the app will:
  - lookup `UserProfile` with `crowdee_user_id=<id>`
  - if found, use the related `User` and log them in
  - if not found, create a `User` with username `user_<id>` (append `_1`, `_2` if collision) and create a `UserProfile` with `crowdee_user_id` set
  - add the user to a default group named `default`
  - persist `crowdee_user_id`, `param_p` and `task_id` (if present) in the Django session under `request.session` and set a `hide_ui` flag so the UI can hide the top navbar and footer

To open the dashboard with hidden UI and status bar, use a URL like:

http://127.0.0.1:8000/dashboard/?user_id=55&param_p=33&task_id=10

Or visit landing page first to set session and then dashboard:

http://127.0.0.1:8000/?user_id=55&param_p=33&task_id=10
http://127.0.0.1:8000/dashboard/

Logs
- Two log files are written under the project root by default:
  - `appraise.log` — general application log
  - `middleware.log` — middleware-specific events (authentication-by-query, session writes, failures)

Tail middleware log (management command)
- The project contains a management command `tail_middleware_log` to view the middleware log from within the Django environment. Example:

```bash
# show existing lines
python manage.py tail_middleware_log

# follow new lines and filter by substring
python manage.py tail_middleware_log --follow --filter crowdee_user_id
```

If running inside Docker:

```bash
docker-compose exec web python manage.py tail_middleware_log --follow --filter crowdee_user_id
# or
docker-compose exec web sh -c "tail -f /app/middleware.log"
```

Troubleshooting
- DB permission errors when mounting `data/db.sqlite3`
  - Ensure `data/db.sqlite3` is writable by the container. Quick fix: `chmod 666 data/db.sqlite3` on the host.
- Missing static files or incorrect static root
  - The Dockerfile runs `collectstatic --noinput` during build (best-effort). For dev you can mount `./static` to `/app/static` to persist collected files.
- Middleware errors creating or logging-in users
  - Tail `middleware.log` (see above) and inspect entries for the `crowdee_user_id` you used. The middleware logs user lookups, creations, login events and session persistence as INFO and logs exceptions with tracebacks.

Security note
- The query-parameter login flow is intentionally simple for testing and crowd-runner integration. It bypasses normal authentication and creates users with no passwords. Do NOT enable this flow in a production deployment exposed to the public internet. Use a proper SSO/OAuth2 integration for production.

Extending/Customization
- To disable the query-param flow entirely, you can remove `Appraise.middleware.CrowdeeAuthMiddleware` from `MIDDLEWARE` in `Appraise/settings.py`.
- To make the hide-UI flag temporary (only for the single request), update the middleware and helper to avoid writing `hide_ui` to the session and instead pass flags as query params or via a short-lived signed token.

Contact / Next steps
- If you want I can: make the status bar dismissible; add more structured JSON logs; add a simple admin UI to look up `crowdee_user_id` mappings; or implement a proper 3rd-party API call hook on job submit.

----

Appendix: Useful commands

```bash
# Run the app (docker-compose)
docker-compose up -d --build

# Show logs for the web service
docker-compose logs -f web

# Execute a management command inside the running service
docker-compose exec web python manage.py migrate

# Tail middleware log from host
python manage.py tail_middleware_log --follow
```

