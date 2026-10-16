import os
import stat
import tempfile
import time
import unittest
from pathlib import Path

from repro_doctor.agents import AgentResponse
from repro_doctor.models import Artifact, CommandResult
from repro_doctor.pipeline import process_repository
from repro_doctor.verifier import DockerSubprocessRunner, classify_failure


def _result(*command: str, returncode: int = 0, output: str = "") -> CommandResult:
    return CommandResult(
        command=command,
        returncode=returncode,
        stdout=output,
    )


class FakeDocker:
    def __init__(self, cycles):
        self.cycles = cycles
        self.build_calls = 0
        self.test_calls = 0
        self.current = None

    def build(self, root, image_tag, timeout):
        self.current = self.cycles[min(self.build_calls, len(self.cycles) - 1)]
        self.build_calls += 1
        return self.current[0]

    def test(self, image_tag, timeout):
        self.test_calls += 1
        return self.current[1]


class FakeRepairRunner:
    def __init__(self, *, path="Makefile"):
        self.path = path
        self.calls = []

    def run(self, request, progress=None):
        self.calls.append(request)
        content = (
            ".PHONY: test\n\n"
            "test:\n\tpython -m unittest discover\n"
            if self.path == "Makefile"
            else "FROM python:3.12-slim\nWORKDIR /app\nCOPY . .\n"
        )
        return AgentResponse(
            role=request.role,
            artifacts=(Artifact(self.path, content, "repair fake verification failure"),),
        )


def _source(root: Path) -> Path:
    source = root / "source"
    source.mkdir()
    (source / "app.py").write_text("print('ok')\n", encoding="utf-8")
    return source


class VerificationLoopTests(unittest.TestCase):
    def test_failure_classification_uses_stage_and_captured_output(self):
        self.assertEqual(
            classify_failure(
                "build",
                _result(
                    "docker",
                    "build",
                    returncode=1,
                    output="Dockerfile parse error",
                ),
            ),
            "build",
        )
        self.assertEqual(
            classify_failure(
                "build",
                _result("docker", "build", returncode=1, output="npm ERR! ERESOLVE dependency"),
            ),
            "dependency",
        )
        self.assertEqual(
            classify_failure("test", _result("docker", "run", returncode=1, output="FAILED")),
            "test",
        )
        self.assertEqual(
            classify_failure(
                "test",
                CommandResult(("docker", "run"), None, timed_out=True),
            ),
            "timeout",
        )

    def test_first_verification_passes_without_repair(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = _source(root)
            docker = FakeDocker(
                [
                    (
                        _result("docker", "build"),
                        _result("docker", "run", "--rm", "image", "make", "test"),
                    )
                ]
            )
            repair = FakeRepairRunner()

            result = process_repository(
                str(source),
                root / "output",
                mode="local",
                verify=True,
                docker_runner=docker,
                repair_runner=repair,
            )

            self.assertTrue(result.verification is not None)
            self.assertTrue(result.verification.passed)
            self.assertEqual(result.verification.retry_count, 0)
            self.assertEqual(repair.calls, [])
            self.assertIn("Result: passed", result.report_path.read_text(encoding="utf-8"))

    def test_test_failure_routes_one_repair_and_then_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = _source(root)
            docker = FakeDocker(
                [
                    (
                        _result("docker", "build"),
                        _result("docker", "run", returncode=1, output="FAILED test command"),
                    ),
                    (
                        _result("docker", "build"),
                        _result("docker", "run"),
                    ),
                ]
            )
            repair = FakeRepairRunner()

            result = process_repository(
                str(source),
                root / "output",
                mode="local",
                verify=True,
                docker_runner=docker,
                repair_runner=repair,
            )

            self.assertTrue(result.verification.passed)
            self.assertEqual(result.verification.retry_count, 1)
            self.assertEqual(len(repair.calls), 1)
            self.assertEqual(repair.calls[0].role, "test-script-writer")
            self.assertIn("FAILED test command", repair.calls[0].prompt)
            report = result.report_path.read_text(encoding="utf-8")
            self.assertIn("Retry count: 1", report)
            self.assertIn("test-script-writer", report)

    def test_dependency_build_failure_routes_to_dockerfile_and_exhausts_at_five(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = _source(root)
            failed_build = _result(
                "docker",
                "build",
                returncode=1,
                output="RUN python -m pip install -r requirements.txt\nfailed",
            )
            docker = FakeDocker([(failed_build, _result("docker", "run"))])
            repair = FakeRepairRunner(path="Dockerfile")

            result = process_repository(
                str(source),
                root / "output",
                mode="local",
                verify=True,
                docker_runner=docker,
                repair_runner=repair,
            )

            self.assertFalse(result.verification.passed)
            self.assertEqual(result.verification.retry_count, 5)
            self.assertEqual(docker.build_calls, 6)
            self.assertEqual(docker.test_calls, 0)
            self.assertEqual(len(repair.calls), 5)
            self.assertTrue(all(call.role == "dockerfile-writer" for call in repair.calls))
            self.assertTrue(result.patch_path.exists())
            self.assertTrue(result.report_path.exists())
            self.assertIn("Dockerfile", result.changed_files)
            report = result.report_path.read_text(encoding="utf-8")
            self.assertIn("Failure classification: `dependency`", report)
            self.assertIn("RUN python -m pip install", report)
            self.assertEqual(report.count("Attempt "), 5)


class DockerProcessCleanupTests(unittest.TestCase):
    def test_timeout_terminates_and_reaps_the_docker_process_group(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pid_file = root / "child.pid"
            script = root / "fake-docker"
            script.write_text(
                f"#!{os.sys.executable}\n"
                "import subprocess\n"
                "import sys\n"
                "import time\n"
                f"child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
                f"open({str(pid_file)!r}, 'w').write(str(child.pid))\n"
                "time.sleep(30)\n",
                encoding="utf-8",
            )
            script.chmod(script.stat().st_mode | stat.S_IXUSR)
            runner = DockerSubprocessRunner(binary=str(script))

            started = time.monotonic()
            result = runner.build(root, "test-image", 0.1)
            self.assertLess(time.monotonic() - started, 2.0)
            self.assertTrue(result.timed_out)
            self.assertTrue(pid_file.exists())
            child_pid = int(pid_file.read_text(encoding="utf-8"))
            for _ in range(100):
                if not Path(f"/proc/{child_pid}").exists():
                    break
                time.sleep(0.01)
            self.assertFalse(Path(f"/proc/{child_pid}").exists())
