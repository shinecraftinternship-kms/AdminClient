import logging
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import connection

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Deletes ALL data from the database (preserves DB schema). Recreates admin superuser."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep-admin", action="store_true", default=False,
            help="Keep the admin superuser account",
        )
        parser.add_argument(
            "--no-input", action="store_true", default=False,
            help="Skip confirmation prompt",
        )

    def handle(self, *args, **options):
        keep_admin = options["keep_admin"]
        no_input = options["no_input"]

        if not no_input:
            confirm = input(
                "WARNING: This will DELETE ALL DATA from the database.\n"
                "Type 'YES' to confirm: "
            )
            if confirm != "YES":
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        self.stdout.write("Clearing all data from database...")

        # Get all table names (excluding Django internals)
        with connection.cursor() as cursor:
            if connection.vendor == "sqlite":
                cursor.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'django_%' AND name NOT LIKE 'sqlite_%'"
                )
            else:
                cursor.execute(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename NOT LIKE 'django_%'"
                )
            tables = [row[0] for row in cursor.fetchall()]

        # Temporarily disable foreign key checks (SQLite)
        if connection.vendor == "sqlite":
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA foreign_keys = OFF")

        # Delete from every table
        with connection.cursor() as cursor:
            for table in tables:
                try:
                    cursor.execute(f'DELETE FROM "{table}"')
                    count = cursor.rowcount
                    self.stdout.write(f"  Cleared table '{table}': {count} row(s)")
                except Exception as e:
                    self.stdout.write(f"  Skipped '{table}': {e}")

        # Re-enable foreign key checks (SQLite)
        if connection.vendor == "sqlite":
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA foreign_keys = ON")

        # Reset sequences (PostgreSQL)
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                for table in tables:
                    try:
                        cursor.execute(
                            f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), 1, false)"
                        )
                    except Exception:
                        pass

        # Recreate admin superuser
        admin_password = "admin123"
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", admin_password)
            self.stdout.write(self.style.SUCCESS("Created admin superuser (admin / admin123)"))
        else:
            self.stdout.write("Admin superuser already exists.")

        self.stdout.write(self.style.SUCCESS("\nAll data cleared successfully."))
        self.stdout.write("Admin login: admin / admin123")
