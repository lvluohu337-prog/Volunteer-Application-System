from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.database import get_database_url, get_postgres_conninfo, init_db


def main() -> None:
    init_db()

    backup_dir = Path(__file__).resolve().parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_path = backup_dir / f"gaokao_planning_{timestamp}.sql"
    pg_dump_bin = os.environ.get("PG_DUMP_PATH", "pg_dump")
    conninfo = get_postgres_conninfo()
    database_url = get_database_url()

    if database_url:
        command = [pg_dump_bin, database_url, "--file", str(target_path), "--clean", "--if-exists"]
        env = None
    else:
        if not conninfo:
            raise RuntimeError("PostgreSQL connection info is required for backup.")
        segments = dict(item.split("=", 1) for item in conninfo.split() if "=" in item)
        command = [
            pg_dump_bin,
            "--host",
            segments.get("host", "127.0.0.1"),
            "--port",
            segments.get("port", "5432"),
            "--username",
            segments["user"],
            "--dbname",
            segments["dbname"],
            "--file",
            str(target_path),
            "--clean",
            "--if-exists",
        ]
        env = os.environ.copy()
        if segments.get("password"):
            env["PGPASSWORD"] = segments["password"]

    subprocess.run(command, check=True, env=env)
    print(f"PostgreSQL backup created: {target_path}")


if __name__ == "__main__":
    main()
