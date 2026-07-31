from pathlib import Path
import tempfile
from unittest import TestCase

from runtime import get_data_dir


class PersistentDatabaseTests(TestCase):
    def test_legacy_database_is_copied_to_persistent_data_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            legacy_dir = tmpdir_path / "legacy-data"
            legacy_dir.mkdir()
            legacy_db = legacy_dir / "scanner.db"
            legacy_db.write_bytes(b"persist-me")

            data_dir = tmpdir_path / "persistent-data"
            data_dir.mkdir()

            resolved = get_data_dir(
                data_dir_override=str(data_dir),
                legacy_data_dir=str(legacy_dir),
            )

            self.assertEqual(Path(resolved), data_dir)
            self.assertTrue((data_dir / "scanner.db").exists())
            self.assertEqual((data_dir / "scanner.db").read_bytes(), b"persist-me")
