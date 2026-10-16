import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from repro_doctor.pipeline import process_repository


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(path for path in root.rglob("*") if path.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class PipelineTests(unittest.TestCase):
    def test_patch_applies_and_source_stays_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "fixture"
            source.mkdir()
            (source / "pyproject.toml").write_text(
                "[project]\nname = 'patch-fixture'\n\n", encoding="utf-8"
            )
            (source / "tests").mkdir()
            (source / "tests" / "test_ok.py").write_text(
                "import unittest\n\nclass TestOK(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            output = root / "output"
            before_digest = _tree_digest(source)

            result = process_repository(str(source), output)

            self.assertEqual(before_digest, _tree_digest(source))
            self.assertTrue(result.patch_path.exists())
            self.assertTrue(result.report_path.exists())
            self.assertIn("Dockerfile", result.changed_files)
            report = result.report_path.read_text(encoding="utf-8")
            self.assertIn("Stack: Python", report)
            self.assertIn("Retry count: 0", report)
            self.assertIn("Result: not run", report)

            applied = root / "applied"
            shutil.copytree(source, applied)
            checked = subprocess.run(
                ["git", "apply", "--check", str(result.patch_path)],
                cwd=applied,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(checked.returncode, 0, checked.stderr)
            applied_result = subprocess.run(
                ["git", "apply", str(result.patch_path)],
                cwd=applied,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(applied_result.returncode, 0, applied_result.stderr)
            self.assertTrue((applied / "Makefile").exists())
            self.assertTrue((applied / "README.repro-doctor.md").exists())
