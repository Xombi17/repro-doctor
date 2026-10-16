import tempfile
import unittest
from pathlib import Path

from repro_doctor.detect import detect_python
from repro_doctor.errors import UnsupportedRepositoryError


class DetectionTests(unittest.TestCase):
    def test_detects_pyproject_runtime_lockfile_and_pytest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "pyproject.toml").write_text(
                """[project]
name = "fixture-app"
requires-python = ">=3.11"
dependencies = ["requests>=2"]

[tool.pytest.ini_options]
testpaths = ["tests"]
""",
                encoding="utf-8",
            )
            (root / ".python-version").write_text("3.11.9\n", encoding="utf-8")
            (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("def test_ok(): pass\n", encoding="utf-8")

            profile = detect_python(root)

            self.assertEqual(profile.stack, "python")
            self.assertEqual(profile.package_name, "fixture-app")
            self.assertEqual(profile.runtime, "3.11.9")
            self.assertEqual(profile.lockfile, "uv.lock")
            self.assertEqual(profile.test_command, "python -m pytest")
            self.assertEqual(profile.confidence, "high")

    def test_uses_unittest_fallback_for_test_layout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "app.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text(
                "import unittest\n\nclass AppTests(unittest.TestCase):\n    pass\n",
                encoding="utf-8",
            )

            profile = detect_python(root)

            self.assertEqual(profile.test_command, "python -m unittest discover -s tests")
            self.assertEqual(profile.runtime, "3.12")
            self.assertIsNone(profile.lockfile)

    def test_rejects_node_and_ambiguous_repositories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "package.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaises(UnsupportedRepositoryError) as error:
                detect_python(root)
            self.assertIn("Phase 2", str(error.exception))

            (root / "app.py").write_text("print('python')\n", encoding="utf-8")
            with self.assertRaises(UnsupportedRepositoryError) as error:
                detect_python(root)
            self.assertIn("ambiguous", str(error.exception))

    def test_rejects_repository_without_python_signals(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "notes.txt").write_text("not a project\n", encoding="utf-8")
            with self.assertRaises(UnsupportedRepositoryError):
                detect_python(root)
