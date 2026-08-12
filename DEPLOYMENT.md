# BrainyBotz CRM — Production Hardening

## Before deployment

1. Set `DJANGO_DEBUG=False`.
2. Generate a strong `DJANGO_SECRET_KEY`.
3. Set `DJANGO_ALLOWED_HOSTS` to the production hostname(s).
4. Set `DJANGO_CSRF_TRUSTED_ORIGINS` to the HTTPS origin(s).
5. Configure SMTP credentials instead of the console email backend.
6. Configure Razorpay production credentials only when payments are ready for production.
7. Configure Google OAuth only if Google login is required.
8. Run:
   - `python3 manage.py check --deploy`
   - `python3 manage.py collectstatic --noinput`
9. Run database migrations on the deployment environment.
10. Configure regular database backups.

## Local safety checks

```bash
python3 manage.py check
python3 manage.py check --deploy
python3 manage.py backup_db
```

The backup command creates timestamped SQLite copies under `backups/`.

## Production server

The included `gunicorn` dependency supports a WSGI deployment. A typical command is:

```bash
gunicorn config.wsgi:application
```

Use the platform's HTTPS/SSL termination and set the environment variables above.

## Important

- Never commit `.env`, real OAuth secrets, Razorpay secrets, or production database backups.
- SQLite is appropriate for development/small deployments. For a multi-user production CRM, PostgreSQL is recommended.
- Keep `media/` on persistent storage or object storage in production.
