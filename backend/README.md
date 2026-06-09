# Backend

## Start

```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

## Database

- PostgreSQL only
- Configure via `DATABASE_URL` or `POSTGRES_HOST` / `POSTGRES_PORT` / `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD`
- Backup command:

```bash
python backend/backup_db.py
```

Backups are exported as `.sql` files into `backend/backups/`.
