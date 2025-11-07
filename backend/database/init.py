"""Utility script to setup the PostgreSQL database with alembic and optionally seed it and upload files to S3."""
# fmt: on
import os  # noq: I001
import sys  # noq: I001

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "app")))
# fmt: off

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC

import psycopg2
from api.dependencies.s3 import S3Manager
from core.config import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extensions import connection as PgConnection


def get_alembic_version_from_dump(dump_path: str) -> str | None:
    """Extract alembic version from a SQL dump file, if present."""
    with open(dump_path, encoding="utf-8") as f:
        for line in f:
            if "alembic_version VALUES" in line:
                match = re.search(r"VALUES ?\(?'?([a-fA-F0-9]+)'?\)?", line)
                if match:
                    return match.group(1)
    return None

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="Seed PostgreSQL database and upload S3 files.")
    parser.add_argument("--sql-dump", type=str, default=None, help="SQL dump file name in current directory")
    parser.add_argument("--s3-upload-dir", type=str, default=None, help="Directory to upload to S3. If not given, S3 upload is skipped.")
    parser.add_argument("--no-backup", action="store_true", help="Disable automatic backup before dropping the database.")
    return parser.parse_args()


def backup_database(backup_dir: str, alembic_version: str | None) -> None:
    """Backup the current database to a file in backup_dir with name backup_{date}.sql."""
    from datetime import datetime
    backup_name = f"{alembic_version}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.bak"
    backup_path = os.path.join(backup_dir, backup_name)
    cmd = [
        "pg_dump",
        f"-h{POSTGRES_HOST}",
        f"-p{POSTGRES_PORT}",
        f"-U{POSTGRES_USER}",
        "--data-only",
        "--inserts",
        POSTGRES_DB,
        "-f", backup_path
    ]
    env = os.environ.copy()
    env["PGPASSWORD"] = POSTGRES_PASSWORD
    print(f"Backing up only data to {backup_path} ...")
    subprocess.run(cmd, check=True, env=env)  # noqa: S603

def drop_and_recreate_database(db: str = POSTGRES_DB) -> None:
    """Drop and recreate the target database."""
    conn = get_connection(db_name="postgres")
    try:
        with conn.cursor() as cursor:
            # Terminate all connections to the db
            cursor.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid();", (db,))
            cursor.execute(f"DROP DATABASE IF EXISTS \"{db}\"")
            cursor.execute(f"CREATE DATABASE \"{db}\"")
    finally:
        conn.close()
        
def get_connection(db_name: str | None = None) -> PgConnection:
    """Create a new PostgreSQL connection. If db_name is None, use DATABASE_URL."""
    conn: PgConnection = psycopg2.connect(
            dbname=db_name or POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
        )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn
    
def reset_sequences(conn: PgConnection) -> None:
    """Reset all sequences for tables with serial columns, robust to empty tables or missing sequences."""
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT table_name, column_name, column_default
            FROM information_schema.columns
            WHERE column_default LIKE 'nextval%%'
              AND table_schema = 'public'
        """)
        sequence_info = cursor.fetchall()
        for table_name, column_name, column_default in sequence_info:
            try:
                sequence_name = column_default.split("'")[1]
            except IndexError:
                continue

            try:
                cursor.execute(f'SELECT COALESCE(MAX("{column_name}"), 0) FROM "{table_name}"')  # noqa: S608
                max_value = cursor.fetchone()[0]
            except psycopg2.errors.UndefinedTable:
                conn.rollback()
                continue

            # Finally, set the sequence if it exists
            try:
                cursor.execute("SELECT setval(%s, %s, %s)", (sequence_name, max_value + 1, False))
            except psycopg2.errors.UndefinedTable:
                conn.rollback()
                continue

def run_alembic_commands(upgrade_to_version: str = "head") -> None:
    """Run alembic stamp base and upgrade to a specific version or head using subprocess to replicate CLI behavior."""
    # Find the full path to alembic
    alembic_path = shutil.which("alembic")
    if not alembic_path:
        raise RuntimeError("Alembic executable not found in PATH")

    # Run alembic stamp base
    print("Stamping base revision...")
    subprocess.run(  # noqa: S603
        [alembic_path, "stamp", "base"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print("✅ Base revision stamped.")

    # Run alembic upgrade
    print(f"Upgrading to {upgrade_to_version}...")
    subprocess.run(  # noqa: S603
        [alembic_path, "upgrade", upgrade_to_version],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print(f"✅ Upgraded to {upgrade_to_version}.")

def apply_sql_dump(conn: PgConnection, sql_dump_path: str) -> None:
    """Apply the SQL dump file to the database, skipping alembic_version inserts."""
    sql_lines: list[str] = []
    with open(sql_dump_path, encoding="utf-8") as sql_file:
        for line in sql_file:
            if line.strip().startswith("\\"):
                continue
            if "alembic_version VALUES" in line:  # ! Already handled by the previous alembic commands
                continue
            if "SET transaction_timeout" in line:  # ! Not supported in some Postgres versions
                continue
            sql_lines.append(line)
    sql_content: str = "".join(sql_lines)
    with conn.cursor() as cursor:
        cursor.execute(sql_content)

def upload_s3_files(upload_dir: str) -> None:
    """Upload files from upload_dir to S3 using their filename as key."""
    s3_manager: S3Manager = S3Manager()
    if not os.path.isdir(upload_dir):
        return
    for file_name in os.listdir(upload_dir):
        file_path: str = os.path.join(upload_dir, file_name)
        if os.path.isfile(file_path):
            with open(file_path, "rb") as file_data:
                s3_manager.upload(file_name, file_data, content_type="application/octet-stream")

def main() -> None:
    """Initialize and optionally seed the database and upload S3 files."""
    args: argparse.Namespace = parse_args()
    backup_dir = os.getcwd()  # Default backup directory
    alembic_version: str | None = None

    if args.sql_dump:
        alembic_version = get_alembic_version_from_dump(args.sql_dump)
        print(f"✅ Alembic version from dump: {alembic_version}")

    if not args.no_backup:
        try:
            print("Backing up the current database ...")
            backup_database(backup_dir, alembic_version or "head")
            print("✅ Backup completed.")
        except Exception as e:
            print(f"Error during backup: {e}")
            sys.exit(1)

    print("Dropping and recreating the database ...")
    drop_and_recreate_database(POSTGRES_DB)
    conn: PgConnection = get_connection()
    try:
        print(f"Applying Alembic migrations up to version: {alembic_version or 'head'} ...")
        run_alembic_commands(upgrade_to_version=alembic_version or "head")
        conn.commit()
        print("✅ Alembic migrations applied.")
        if args.sql_dump:
            print(f"Applying SQL dump {args.sql_dump} ...")
            apply_sql_dump(conn, args.sql_dump)
            conn.commit()
            print("✅ SQL dump applied.")
            print("Resetting sequences ...")
            reset_sequences(conn)
            print("✅ Sequences reset.")
        if args.s3_upload_dir:
            print(f"Uploading files from {args.s3_upload_dir} to S3 ...")
            upload_s3_files(args.s3_upload_dir)
            print("✅ S3 upload completed.")
            
        print("🎉 Database setup completed successfully.")
    except Exception as e:
        print("❌ Encountered an error during setup!")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    main()