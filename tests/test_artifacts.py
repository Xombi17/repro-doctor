import tempfile
import unittest
from pathlib import Path

from repro_doctor.artifacts import generate_artifacts, materialize
from repro_doctor.detect import detect_python


class ArtifactTests(unittest.TestCase):
    def test_generates_python_reproducibility_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "pyproject.toml").write_text(
                "[project]\nname = 'artifact-fixture'\n\n",
                encoding="utf-8",
            )
            (root / "tests").mkdir()
            (root / "tests" / "test_one.py").write_text(
                "import unittest\n", encoding="utf-8"
            )
            profile = detect_python(root)

            artifacts = generate_artifacts(root, profile)
            by_name = {artifact.path: artifact.content for artifact in artifacts}

            self.assertIn("Dockerfile", by_name)
            self.assertIn("FROM python:3.12-slim", by_name["Dockerfile"])
            self.assertIn("python -m unittest discover -s tests", by_name["Makefile"])
            self.assertEqual(by_name[".python-version"], "3.12\n")
            self.assertIn("dependency lock proposal", by_name["requirements.repro-doctor.txt"])
            self.assertIn("make test", by_name["README.repro-doctor.md"])

            materialize(root, artifacts)
            self.assertTrue((root / "Dockerfile").exists())
            self.assertTrue((root / "Makefile").exists())

    def test_preserves_existing_lockfile_dockerfile_and_test_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "app.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "requirements.txt").write_text("requests==2.32.3\n", encoding="utf-8")
            (root / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
            (root / "Makefile").write_text("test:\n\tpython -m unittest\n", encoding="utf-8")
            profile = detect_python(root)

            artifacts = generate_artifacts(root, profile)
            names = {artifact.path for artifact in artifacts}

            self.assertNotIn("Dockerfile", names)
            self.assertNotIn("Makefile", names)
            self.assertNotIn("requirements.repro-doctor.txt", names)
