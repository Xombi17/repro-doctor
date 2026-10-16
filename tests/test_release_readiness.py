import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from repro_doctor.cli import build_parser


PROJECT_ROOT = Path(__file__).resolve().parents[1]
_NESTED_COPY_ENV = "REPRO_DOCTOR_CLEAN_COPY_CHILD"
_GENERATED_NAMES = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    ".coverage",
    "repro-doctor-output",
    "build",
    "dist",
}
_SECRET_MARKERS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "BEGIN PRIVATE KEY",
    "OMNIRUSH_API_KEY",
    "ghp_",
    "sk-",
)


def _ignore_generated(_directory: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name in _GENERATED_NAMES
        or name.endswith((".pyc", ".pyo", ".egg-info"))
    }


def _meaningful_files(root: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file() or any(part in _GENERATED_NAMES for part in relative.parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        files[relative.as_posix()] = path.read_bytes()
    return files


def _run(command: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@unittest.skipIf(
    os.environ.get(_NESTED_COPY_ENV) == "1",
    "the clean-copy subprocess already runs the complete suite",
)
class CleanCopyValidationTests(unittest.TestCase):
    def test_clean_copy_behaves_like_a_fresh_clone(self):
        before = _meaningful_files(PROJECT_ROOT)
        with tempfile.TemporaryDirectory(prefix="repro-doctor-release-") as temporary:
            copy = Path(temporary) / "checkout"
            shutil.copytree(
                PROJECT_ROOT,
                copy,
                symlinks=True,
                ignore=_ignore_generated,
            )

            self.assertFalse((copy / ".git").exists())
            self.assertFalse(any(path.name == "__pycache__" for path in copy.rglob("*")))
            self.assertFalse((copy / "repro-doctor-output").exists())

            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env[_NESTED_COPY_ENV] = "1"

            tests = _run(["make", "test"], copy, env)
            self.assertEqual(
                tests.returncode,
                0,
                f"clean-copy make test failed:\n{tests.stdout}\n{tests.stderr}",
            )
            self.assertIn("OK", tests.stdout + tests.stderr)

            help_result = _run([sys.executable, "-m", "repro_doctor", "--help"], copy, env)
            self.assertEqual(
                help_result.returncode,
                0,
                f"clean-copy CLI help failed:\n{help_result.stdout}\n{help_result.stderr}",
            )
            self.assertIn("usage: repro-doctor", help_result.stdout)
            self.assertFalse((copy / "repro-doctor-output").exists())
            self.assertFalse(
                any(
                    path.name in {"__pycache__", ".pytest_cache"}
                    or path.suffix in {".pyc", ".pyo"}
                    for path in copy.rglob("*")
                )
            )

        self.assertEqual(before, _meaningful_files(PROJECT_ROOT))


class ReleaseReadinessTests(unittest.TestCase):
    def test_required_release_files_and_pins_are_present(self):
        required = (
            "README.md",
            "CONTRIBUTING.md",
            "SUPPORTED-REPOSITORIES.md",
            "RELEASE-CHECKLIST.md",
            "Dockerfile",
            "Makefile",
            "LICENSE",
            ".python-version",
            "requirements-dev.lock",
        )
        for name in required:
            with self.subTest(name=name):
                self.assertTrue((PROJECT_ROOT / name).is_file())

        self.assertEqual(
            (PROJECT_ROOT / ".python-version").read_text(encoding="utf-8").strip(),
            "3.12",
        )
        lock_lines = [
            line.strip()
            for line in (PROJECT_ROOT / "requirements-dev.lock")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertTrue(lock_lines)
        self.assertTrue(
            all(re.fullmatch(r"[A-Za-z0-9_.-]+==[^\s]+", line) for line in lock_lines)
        )

    def test_readme_documents_the_actual_cli_contract(self):
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        help_text = build_parser().format_help()
        required_sections = (
            "## Requirements",
            "## Setup",
            "## Run",
            "## Supported stacks",
            "## Verification",
            "## Repair limit",
            "## Test",
            "## Docker",
            "## Deploy",
            "## Limitations",
        )
        for section in required_sections:
            with self.subTest(section=section):
                self.assertIn(section, readme)

        for option in (
            "--output-dir",
            "--mode {agent,local}",
            "--agent-timeout AGENT_TIMEOUT",
            "--docker-timeout DOCKER_TIMEOUT",
            "--skip-verification",
            "--version",
        ):
            with self.subTest(option=option):
                self.assertIn(option, help_text)
                self.assertIn(option.split()[0], readme)

        for command in (
            "python -m repro_doctor --help",
            "make test",
            "docker build -t repro-doctor .",
            "docker run --rm repro-doctor",
        ):
            with self.subTest(command=command):
                self.assertIn(command, readme)
        self.assertIn("five repair attempts", readme)
        self.assertNotIn("--verify", readme)

    def test_report_examples_match_the_report_schema_and_are_redacted(self):
        examples = (
            PROJECT_ROOT / "examples" / "reports" / "python-report.md",
            PROJECT_ROOT / "examples" / "reports" / "node-report.md",
        )
        required_fragments = (
            "# repro-doctor report",
            "## Detected stack",
            "## Changed files",
            "## Verification",
            "- Result:",
            "- Retry count:",
            "### Repair attempts",
        )
        for example in examples:
            with self.subTest(example=example.name):
                text = example.read_text(encoding="utf-8")
                for fragment in required_fragments:
                    self.assertIn(fragment, text)
                for marker in _SECRET_MARKERS:
                    self.assertNotIn(marker, text)
