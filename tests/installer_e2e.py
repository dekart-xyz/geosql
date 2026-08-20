import csv
import io
import os
import select
import subprocess
import tempfile
import time
import unittest
import venv
import zipfile
from pathlib import Path

if os.name != "nt":
    import pty
else:
    pty = None


ROOT = Path(__file__).resolve().parents[1]


def build_fake_dekart_wheel(wheelhouse):
    """Build a local Dekart wheel so the E2E never reaches a package index."""
    wheel_path = wheelhouse / "dekart-0.0.0-py3-none-any.whl"
    files = {
        "dekart/__init__.py": "",
        "dekart/cli.py": """\
import json
import os
import sys
from pathlib import Path


def main():
    state = Path(os.environ["DEKART_E2E_STATE"])
    if sys.argv[1:] == ["init"]:
        state.write_text("ready", encoding="utf-8")
        return 0
    if sys.argv[1:] == ["tools", "--json"] and state.exists():
        print(json.dumps({"tools": []}))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
""",
        "dekart-0.0.0.dist-info/METADATA": """\
Metadata-Version: 2.1
Name: dekart
Version: 0.0.0
""",
        "dekart-0.0.0.dist-info/WHEEL": """\
Wheel-Version: 1.0
Generator: geosql-installer-e2e
Root-Is-Purelib: true
Tag: py3-none-any
""",
        "dekart-0.0.0.dist-info/entry_points.txt": """\
[console_scripts]
dekart = dekart.cli:main
""",
    }
    record = io.StringIO()
    writer = csv.writer(record, lineterminator="\n")
    for name in files:
        writer.writerow([name, "", ""])
    writer.writerow(["dekart-0.0.0.dist-info/RECORD", "", ""])
    files["dekart-0.0.0.dist-info/RECORD"] = record.getvalue()

    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return wheel_path


def run_in_pty(command, env, input_bytes=b"\r", timeout=30):
    """Run a command in a real terminal and return its code and transcript."""
    master_fd, slave_fd = pty.openpty()
    process = subprocess.Popen(
        command,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        env=env,
        close_fds=True,
    )
    os.close(slave_fd)
    output = bytearray()
    input_sent = False
    deadline = time.monotonic() + timeout
    try:
        while process.poll() is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                process.kill()
                raise AssertionError(f"installer timed out; output:\n{output.decode(errors='replace')}")
            ready, _, _ = select.select([master_fd], [], [], min(0.1, remaining))
            if ready:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError:
                    break
                if not chunk:
                    time.sleep(0.01)
                    continue
                output.extend(chunk)
                if not input_sent and (b"Use " in output or b"Select [" in output):
                    os.write(master_fd, input_bytes)
                    input_sent = True
        while True:
            ready, _, _ = select.select([master_fd], [], [], 0)
            if not ready:
                break
            try:
                chunk = os.read(master_fd, 4096)
            except OSError:
                break
            if not chunk:
                break
            output.extend(chunk)
    finally:
        os.close(master_fd)
        if process.poll() is None:
            process.kill()
        process.wait()
    return process.returncode, output.decode(errors="replace")


class InstallerE2ETest(unittest.TestCase):
    def test_vibe_install_bootstraps_dekart_when_environment_has_no_pip(self):
        self.assertEqual(os.environ.get("GEOSQL_INSTALLER_E2E_CONTAINER"), "1")
        self.assertTrue(Path("/.dockerenv").is_file(), "installer E2E must run inside Docker")
        with tempfile.TemporaryDirectory() as directory:
            temp_root = Path(directory)
            environment = temp_root / "venv"
            venv.EnvBuilder(with_pip=False).create(environment)
            scripts = environment / ("Scripts" if os.name == "nt" else "bin")
            python = scripts / ("python.exe" if os.name == "nt" else "python")

            wheelhouse = temp_root / "wheelhouse"
            wheelhouse.mkdir()
            build_fake_dekart_wheel(wheelhouse)

            home = temp_root / "home"
            vibe_home = home / ".vibe"
            vibe_home.mkdir(parents=True)
            state = temp_root / "dekart-ready"
            env = os.environ.copy()
            env.update(
                {
                    "DEKART_E2E_STATE": str(state),
                    "DO_NOT_TRACK": "1",
                    "HOME": str(home),
                    "NO_COLOR": "1",
                    "PATH": os.pathsep.join([str(scripts), "/usr/bin", "/bin"]),
                    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                    "PIP_FIND_LINKS": str(wheelhouse),
                    "PIP_NO_INDEX": "1",
                    "PYTHONPATH": str(ROOT),
                    "TERM": "xterm-256color",
                    "VIBE_HOME": str(vibe_home),
                }
            )

            code, output = run_in_pty([str(python), "-m", "geosql.cli", "install", "vibe"], env)

            self.assertEqual(code, 0, output)
            self.assertLess(output.index("-m ensurepip --upgrade"), output.index("Select [1-2]"), output)
            self.assertTrue((vibe_home / "skills" / "geosql" / "SKILL.md").is_file(), output)
            self.assertTrue((scripts / "dekart").is_file(), output)
            self.assertTrue(state.is_file(), output)
            ready = subprocess.run(
                [str(scripts / "dekart"), "tools", "--json"],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(ready.returncode, 0, ready.stderr)


if __name__ == "__main__":
    unittest.main()
