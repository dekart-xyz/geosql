import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from geosql import cli


@contextlib.contextmanager
def temp_home():
    with tempfile.TemporaryDirectory() as directory:
        home = Path(directory)
        with mock.patch("geosql.cli.Path.home", return_value=home):
            yield home


class CliInstallTest(unittest.TestCase):
    def test_install_copilot_skill_copies_skill_and_references(self):
        with temp_home() as home:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli.install_copilot_skill(), 0)

            skill_dir = home / ".copilot" / "skills" / "geosql"
            self.assertTrue((skill_dir / "SKILL.md").exists())
            self.assertTrue((skill_dir / "references" / "map-styling.md").exists())

    def test_handle_install_target_accepts_copilot(self):
        with mock.patch("geosql.cli.install_copilot_skill", return_value=0) as install:
            self.assertEqual(cli.handle_install_target("copilot"), 0)

        install.assert_called_once_with()

    def test_handle_install_target_all_installs_all_targets(self):
        with mock.patch("geosql.cli.install_claude_skill", return_value=0) as claude:
            with mock.patch("geosql.cli.install_codex_skill", return_value=0) as codex:
                with mock.patch("geosql.cli.install_copilot_skill", return_value=0) as copilot:
                    self.assertEqual(cli.handle_install_target("all"), 0)

        claude.assert_called_once_with()
        codex.assert_called_once_with()
        copilot.assert_called_once_with()

    def test_detect_installed_agents_includes_copilot_home(self):
        with temp_home() as home:
            (home / ".copilot").mkdir()
            with mock.patch("geosql.cli.shutil.which", return_value=None):
                self.assertEqual(cli.detect_installed_agents(), ["copilot"])

    def test_manual_install_hint_lists_copilot_paths(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(cli.manual_install_hint(), 1)

        text = output.getvalue()
        self.assertIn("~/.copilot/skills/geosql/SKILL.md", text)
        self.assertIn("~/.copilot/skills/geosql/references/", text)

    def test_non_interactive_single_copilot_detection_installs_copilot(self):
        env = {"DO_NOT_TRACK": "1", "HOME": os.environ.get("HOME", "")}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch("geosql.cli.print_banner"):
                with mock.patch("geosql.cli.detect_installed_agents", return_value=["copilot"]):
                    with mock.patch("geosql.cli.is_interactive_terminal", return_value=False):
                        with mock.patch("geosql.cli.install_copilot_skill", return_value=0) as install:
                            output = io.StringIO()
                            with contextlib.redirect_stdout(output):
                                self.assertEqual(cli.run_interactive_install(), 0)

        install.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
