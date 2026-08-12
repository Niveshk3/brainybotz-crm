from pathlib import Path
from datetime import datetime
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a timestamped backup of the local SQLite database."

    def handle(self, *args, **options):
        db_path = Path(settings.DATABASES["default"]["NAME"])

        if db_path.suffix != ".sqlite3":
            raise CommandError("backup_db is intended for the SQLite development database.")

        if not db_path.exists():
            raise CommandError(f"Database not found: {db_path}")

        backup_dir = settings.BASE_DIR / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = backup_dir / f"db_{timestamp}.sqlite3"

        shutil.copy2(db_path, destination)

        self.stdout.write(
            self.style.SUCCESS(f"Database backup created: {destination}")
        )
