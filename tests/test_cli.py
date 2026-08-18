import contextlib
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from geosql import cli


@contextlib.contextmanager
def temp_home():
    with tempfile.TemporaryDirectory() as directory:
        home = Path(directory)
        with mock.patch("geosql.cli.Path.home", return_value=home), mock.patch.dict(os.environ, {"VIBE_HOME": ""}):
            yield home


class CliInstallTest(unittest.TestCase):
    def test_parser_accepts_vibe_target(self):
        args = cli.build_parser().parse_args(["install", "vibe"])

        self.assertEqual(args.command, "install")
        self.assertEqual(args.target, "vibe")

    def test_install_copilot_skill_copies_skill_and_references(self):
        with temp_home() as home:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli.install_copilot_skill(), 0)

            skill_dir = home / ".copilot" / "skills" / "geosql"
            self.assertTrue((skill_dir / "SKILL.md").exists())
            self.assertTrue((skill_dir / "references" / "map-styling.md").exists())
            self.assertTrue((skill_dir / "references" / "bigquery.md").exists())
            self.assertTrue((skill_dir / "references" / "snowflake.md").exists())
            self.assertTrue((skill_dir / "references" / "postgres.md").exists())
            self.assertTrue((skill_dir / "references" / "wherobots.md").exists())

    def test_install_opencode_skill_copies_skill_and_references(self):
        with temp_home() as home:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli.install_opencode_skill(), 0)

            skill_dir = home / ".config" / "opencode" / "skills" / "geosql"
            self.assertTrue((skill_dir / "SKILL.md").exists())
            self.assertTrue((skill_dir / "references" / "map-styling.md").exists())
            self.assertTrue((skill_dir / "references" / "bigquery.md").exists())
            self.assertTrue((skill_dir / "references" / "snowflake.md").exists())
            self.assertTrue((skill_dir / "references" / "postgres.md").exists())
            self.assertTrue((skill_dir / "references" / "wherobots.md").exists())

    def test_install_vibe_skill_copies_skill_and_references(self):
        with temp_home() as home:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli.install_vibe_skill(), 0)

            skill_dir = home / ".vibe" / "skills" / "geosql"
            self.assertTrue((skill_dir / "SKILL.md").exists())
            self.assertTrue((skill_dir / "references" / "map-styling.md").exists())
            self.assertTrue((skill_dir / "references" / "bigquery.md").exists())
            self.assertTrue((skill_dir / "references" / "snowflake.md").exists())
            self.assertTrue((skill_dir / "references" / "postgres.md").exists())
            self.assertTrue((skill_dir / "references" / "wherobots.md").exists())

    def test_install_vibe_skill_uses_configured_vibe_home(self):
        with tempfile.TemporaryDirectory() as directory:
            vibe_home = Path(directory) / "custom-vibe"
            with mock.patch.dict(os.environ, {"VIBE_HOME": str(vibe_home)}):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(cli.install_vibe_skill(), 0)

            self.assertTrue((vibe_home / "skills" / "geosql" / "SKILL.md").exists())

    def test_handle_install_target_accepts_copilot(self):
        with mock.patch("geosql.cli.install_copilot_skill", return_value=0) as install:
            with mock.patch("geosql.cli.offer_dekart_setup", return_value=0) as dekart:
                self.assertEqual(cli.handle_install_target("copilot"), 0)

        install.assert_called_once_with()
        dekart.assert_called_once_with("GitHub Copilot")

    def test_handle_install_target_accepts_opencode(self):
        with mock.patch("geosql.cli.install_opencode_skill", return_value=0) as install:
            with mock.patch("geosql.cli.offer_dekart_setup", return_value=0) as dekart:
                self.assertEqual(cli.handle_install_target("opencode"), 0)

        install.assert_called_once_with()
        dekart.assert_called_once_with("OpenCode")

    def test_handle_install_target_accepts_vibe(self):
        with mock.patch("geosql.cli.install_vibe_skill", return_value=0) as install:
            with mock.patch("geosql.cli.offer_dekart_setup", return_value=0) as dekart:
                self.assertEqual(cli.handle_install_target("vibe"), 0)

        install.assert_called_once_with()
        dekart.assert_called_once_with("Mistral Vibe")

    def test_handle_install_target_all_installs_all_targets(self):
        with mock.patch("geosql.cli.install_claude_skill", return_value=0) as claude:
            with mock.patch("geosql.cli.install_codex_skill", return_value=0) as codex:
                with mock.patch("geosql.cli.install_copilot_skill", return_value=0) as copilot:
                    with mock.patch("geosql.cli.install_opencode_skill", return_value=0) as opencode:
                        with mock.patch("geosql.cli.install_vibe_skill", return_value=0) as vibe:
                            with mock.patch("geosql.cli.offer_dekart_setup", return_value=0) as dekart:
                                self.assertEqual(cli.handle_install_target("all"), 0)

        claude.assert_called_once_with()
        codex.assert_called_once_with()
        copilot.assert_called_once_with()
        opencode.assert_called_once_with()
        vibe.assert_called_once_with()
        dekart.assert_called_once_with("your selected agents")

    def test_failed_skill_install_does_not_offer_dekart(self):
        with mock.patch("geosql.cli.install_codex_skill", return_value=1):
            with mock.patch("geosql.cli.offer_dekart_setup") as dekart:
                self.assertEqual(cli.handle_install_target("codex"), 1)

        dekart.assert_not_called()

    def test_detect_installed_agents_includes_copilot_home(self):
        with temp_home() as home:
            (home / ".copilot").mkdir()
            with mock.patch("geosql.cli.shutil.which", return_value=None):
                self.assertEqual(cli.detect_installed_agents(), ["copilot"])

    def test_detect_installed_agents_includes_opencode_home(self):
        with temp_home() as home:
            (home / ".config" / "opencode").mkdir(parents=True)
            with mock.patch("geosql.cli.shutil.which", return_value=None):
                self.assertEqual(cli.detect_installed_agents(), ["opencode"])

    def test_detect_installed_agents_includes_vibe_binary(self):
        with temp_home():
            with mock.patch("geosql.cli.shutil.which", side_effect=lambda name: "/bin/vibe" if name == "vibe" else None):
                self.assertEqual(cli.detect_installed_agents(), ["vibe"])

    def test_detect_installed_agents_includes_vibe_home(self):
        with temp_home() as home:
            (home / ".vibe").mkdir()
            with mock.patch("geosql.cli.shutil.which", return_value=None):
                self.assertEqual(cli.detect_installed_agents(), ["vibe"])

    def test_detect_installed_agents_includes_configured_vibe_home(self):
        with tempfile.TemporaryDirectory() as directory:
            isolated_home = Path(directory)
            vibe_home = isolated_home / "custom-vibe"
            vibe_home.mkdir()
            with mock.patch.dict(os.environ, {"VIBE_HOME": str(vibe_home)}):
                with mock.patch("geosql.cli.Path.home", return_value=isolated_home):
                    with mock.patch("geosql.cli.shutil.which", return_value=None):
                        self.assertEqual(cli.detect_installed_agents(), ["vibe"])

    def test_manual_install_hint_lists_copilot_paths(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(cli.manual_install_hint(), 1)

        text = output.getvalue()
        self.assertIn("~/.copilot/skills/geosql/SKILL.md", text)
        self.assertIn("~/.copilot/skills/geosql/references/", text)
        self.assertIn("~/.config/opencode/skills/geosql/SKILL.md", text)
        self.assertIn("~/.config/opencode/skills/geosql/references/", text)
        self.assertIn("~/.vibe/skills/geosql/SKILL.md", text)
        self.assertIn("~/.vibe/skills/geosql/references/", text)

    def test_manual_install_hint_uses_configured_vibe_home(self):
        with tempfile.TemporaryDirectory() as directory:
            vibe_home = Path(directory) / "not-created"
            output = io.StringIO()
            with mock.patch.dict(os.environ, {"VIBE_HOME": str(vibe_home)}):
                with contextlib.redirect_stdout(output):
                    self.assertEqual(cli.manual_install_hint(), 1)

            self.assertIn(str(vibe_home / "skills" / "geosql" / "SKILL.md"), output.getvalue())

    def test_non_interactive_single_copilot_detection_installs_copilot(self):
        env = {"DO_NOT_TRACK": "1", "HOME": os.environ.get("HOME", "")}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch("geosql.cli.print_banner"):
                with mock.patch("geosql.cli.detect_installed_agents", return_value=["copilot"]):
                    with mock.patch("geosql.cli.is_interactive_terminal", return_value=False):
                        with mock.patch("geosql.cli.install_copilot_skill", return_value=0) as install:
                            with mock.patch("geosql.cli.offer_dekart_setup", return_value=0):
                                output = io.StringIO()
                                with contextlib.redirect_stdout(output):
                                    self.assertEqual(cli.run_interactive_install(), 0)

        install.assert_called_once_with()

    def test_non_interactive_single_vibe_detection_installs_vibe(self):
        env = {"DO_NOT_TRACK": "1", "HOME": os.environ.get("HOME", "")}
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch("geosql.cli.print_banner"):
                with mock.patch("geosql.cli.detect_installed_agents", return_value=["vibe"]):
                    with mock.patch("geosql.cli.is_interactive_terminal", return_value=False):
                        with mock.patch("geosql.cli.install_vibe_skill", return_value=0) as install:
                            with mock.patch("geosql.cli.offer_dekart_setup", return_value=0):
                                output = io.StringIO()
                                with contextlib.redirect_stdout(output):
                                    self.assertEqual(cli.run_interactive_install(), 0)

        install.assert_called_once_with()

    def test_skill_is_user_invocable(self):
        skill_text = cli.ROOT_SKILL_FILE.read_text(encoding="utf-8")

        self.assertIn("user-invocable: true", skill_text)

    def test_skill_documents_snapshot_viewport_params(self):
        skill_text = cli.ROOT_SKILL_FILE.read_text(encoding="utf-8")

        self.assertIn("dekart snapshot --report-id <report_id> --out /tmp/<report_id>-snapshot.png --zoom", skill_text)
        self.assertIn("--lat", skill_text)
        self.assertIn("--lon", skill_text)


class DekartSetupTest(unittest.TestCase):
    def test_ready_cli_does_not_prompt_or_change_setup(self):
        output = io.StringIO()
        with mock.patch("geosql.cli.find_dekart_cli", return_value="/bin/dekart"):
            with mock.patch("geosql.cli.is_dekart_ready", return_value=True):
                with mock.patch("geosql.cli.select_optional_dekart_action") as select_action:
                    with mock.patch("geosql.cli.run_dekart_command") as run_command:
                        with contextlib.redirect_stdout(output):
                            self.assertEqual(cli.offer_dekart_setup(), 0)

        select_action.assert_not_called()
        run_command.assert_not_called()
        self.assertIn("GeoSQL and Dekart are ready.", output.getvalue())

    def test_missing_cli_yes_installs_with_current_python_then_initializes(self):
        with mock.patch("geosql.cli.find_dekart_cli", side_effect=[None, "/bin/dekart"]):
            with mock.patch("geosql.cli.is_interactive_terminal", return_value=True):
                with mock.patch("geosql.cli.is_dekart_ready", return_value=True):
                    with mock.patch("geosql.cli.select_optional_dekart_action", return_value=True):
                        with mock.patch("geosql.cli.run_dekart_command", side_effect=[0, 0]) as run_command:
                            self.assertEqual(cli.offer_dekart_setup(), 0)

        self.assertEqual(
            run_command.call_args_list,
            [
                mock.call([cli.sys.executable, "-m", "pip", "install", "dekart"]),
                mock.call(["/bin/dekart", "init"]),
            ],
        )

    def test_missing_cli_no_keeps_geosql_installed_and_prints_later_commands(self):
        output = io.StringIO()
        with mock.patch("geosql.cli.find_dekart_cli", return_value=None):
            with mock.patch("geosql.cli.is_interactive_terminal", return_value=True):
                with mock.patch("geosql.cli.select_optional_dekart_action", return_value=False):
                    with mock.patch("geosql.cli.run_dekart_command") as run_command:
                        with contextlib.redirect_stdout(output):
                            self.assertEqual(cli.offer_dekart_setup(), 0)

        run_command.assert_not_called()
        text = output.getvalue()
        self.assertIn("GeoSQL is installed. Dekart setup was skipped.", text)
        self.assertIn("-m pip install dekart", text)
        self.assertIn("dekart init", text)

    def test_installed_not_ready_yes_skips_pip_and_initializes(self):
        with mock.patch("geosql.cli.find_dekart_cli", return_value="/bin/dekart"):
            with mock.patch("geosql.cli.is_dekart_ready", side_effect=[False, True]):
                with mock.patch("geosql.cli.is_interactive_terminal", return_value=True):
                    with mock.patch("geosql.cli.select_optional_dekart_action", return_value=True):
                        with mock.patch("geosql.cli.run_dekart_command", return_value=0) as run_command:
                            self.assertEqual(cli.offer_dekart_setup(), 0)

        run_command.assert_called_once_with(["/bin/dekart", "init"])

    def test_non_interactive_missing_cli_never_installs_or_initializes(self):
        output = io.StringIO()
        with mock.patch("geosql.cli.find_dekart_cli", return_value=None):
            with mock.patch("geosql.cli.is_interactive_terminal", return_value=False):
                with mock.patch("geosql.cli.run_dekart_command") as run_command:
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(cli.offer_dekart_setup(), 0)

        run_command.assert_not_called()
        self.assertIn("Non-interactive terminal detected", output.getvalue())

    def test_non_interactive_installed_cli_uses_short_readiness_timeout(self):
        with mock.patch("geosql.cli.find_dekart_cli", return_value="/bin/dekart"):
            with mock.patch("geosql.cli.is_interactive_terminal", return_value=False):
                with mock.patch("geosql.cli.is_dekart_ready", return_value=False) as ready:
                    with mock.patch("geosql.cli.run_dekart_command") as run_command:
                        self.assertEqual(cli.offer_dekart_setup(), 0)

        ready.assert_called_once_with("/bin/dekart", timeout=2)
        run_command.assert_not_called()

    def test_escape_cancels_optional_offer(self):
        with mock.patch("geosql.cli.is_interactive_terminal", return_value=True):
            with mock.patch("geosql.cli.select_menu_option", return_value="cancel"):
                self.assertFalse(cli.select_optional_dekart_action("title", ["Yes", "Not now"]))

    def test_optional_menu_defaults_to_recommended_setup(self):
        with mock.patch("geosql.cli.is_interactive_terminal", return_value=True):
            with mock.patch("geosql.cli.select_menu_option", return_value=0) as select_menu:
                self.assertTrue(cli.select_optional_dekart_action("title", ["Yes", "Not now"]))

        select_menu.assert_called_once_with("title", ["Yes", "Not now"], default_index=0)

    def test_numbered_fallback_blank_defaults_to_recommended_setup(self):
        with mock.patch("geosql.cli.is_interactive_terminal", return_value=True):
            with mock.patch("geosql.cli.select_menu_option", return_value=None):
                with mock.patch("builtins.input", return_value=""):
                    self.assertTrue(cli.select_optional_dekart_action("title", ["Yes", "Not now"]))

    def test_numbered_fallback_escape_cancels(self):
        with mock.patch("geosql.cli.is_interactive_terminal", return_value=True):
            with mock.patch("geosql.cli.select_menu_option", return_value=None):
                with mock.patch("builtins.input", return_value="\x1b"):
                    self.assertFalse(cli.select_optional_dekart_action("title", ["Yes", "Not now"]))

    def test_numbered_fallback_invalid_input_does_not_authorize_install(self):
        output = io.StringIO()
        with mock.patch("geosql.cli.is_interactive_terminal", return_value=True):
            with mock.patch("geosql.cli.select_menu_option", return_value=None):
                with mock.patch("builtins.input", side_effect=["yes", "2"]):
                    with contextlib.redirect_stdout(output):
                        self.assertFalse(cli.select_optional_dekart_action("title", ["Yes", "Not now"]))

        self.assertIn("Enter a number from 1 to 2", output.getvalue())

    def test_missing_cli_offer_uses_benefit_led_copy(self):
        with mock.patch("geosql.cli.find_dekart_cli", return_value=None):
            with mock.patch("geosql.cli.find_environment_dekart_cli", return_value=None):
                with mock.patch("geosql.cli.is_interactive_terminal", return_value=True):
                    with mock.patch("geosql.cli.select_optional_dekart_action", return_value=False) as select_action:
                        self.assertEqual(cli.offer_dekart_setup("Codex"), 0)

        select_action.assert_called_once_with(
            "GeoSQL needs the Dekart CLI to render maps and connect\nyour warehouse.",
            ["Install Dekart CLI (recommended, 4x correctness on GIS tasks)", "Install later"],
        )

    def test_ctrl_c_cancels_optional_offer(self):
        with mock.patch("geosql.cli.is_interactive_terminal", return_value=True):
            with mock.patch("geosql.cli.select_menu_option", side_effect=KeyboardInterrupt):
                self.assertFalse(cli.select_optional_dekart_action("title", ["Yes", "Not now"]))

    def test_pip_failure_returns_nonzero_and_does_not_run_init(self):
        error = io.StringIO()
        with mock.patch("geosql.cli.find_dekart_cli", return_value=None):
            with mock.patch("geosql.cli.is_interactive_terminal", return_value=True):
                with mock.patch("geosql.cli.select_optional_dekart_action", return_value=True):
                    with mock.patch("geosql.cli.run_dekart_command", return_value=7) as run_command:
                        with contextlib.redirect_stderr(error):
                            self.assertEqual(cli.offer_dekart_setup(), 7)

        run_command.assert_called_once_with([cli.sys.executable, "-m", "pip", "install", "dekart"])
        self.assertIn("installation failed", error.getvalue())

    def test_pip_cancellation_keeps_successful_geosql_install(self):
        output = io.StringIO()
        with mock.patch("geosql.cli.find_dekart_cli", return_value=None):
            with mock.patch("geosql.cli.find_environment_dekart_cli", return_value=None):
                with mock.patch("geosql.cli.is_interactive_terminal", return_value=True):
                    with mock.patch("geosql.cli.select_optional_dekart_action", return_value=True):
                        with mock.patch("geosql.cli.run_dekart_command", return_value=130):
                            with contextlib.redirect_stdout(output):
                                self.assertEqual(cli.offer_dekart_setup(), 0)

        self.assertIn("installation was cancelled", output.getvalue())
        self.assertIn("pip install dekart", output.getvalue())

    def test_init_failure_returns_nonzero_and_prints_recovery(self):
        output = io.StringIO()
        error = io.StringIO()
        with mock.patch("geosql.cli.find_dekart_cli", return_value="/bin/dekart"):
            with mock.patch("geosql.cli.is_dekart_ready", return_value=False):
                with mock.patch("geosql.cli.is_interactive_terminal", return_value=True):
                    with mock.patch("geosql.cli.select_optional_dekart_action", return_value=True):
                        with mock.patch("geosql.cli.run_dekart_command", return_value=9):
                            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
                                self.assertEqual(cli.offer_dekart_setup(), 9)

        self.assertIn("Dekart setup did not finish", error.getvalue())
        self.assertIn("dekart init", output.getvalue())

    def test_init_cancellation_keeps_successful_geosql_install(self):
        output = io.StringIO()
        with mock.patch("geosql.cli.find_dekart_cli", return_value="/bin/dekart"):
            with mock.patch("geosql.cli.is_dekart_ready", return_value=False):
                with mock.patch("geosql.cli.is_interactive_terminal", return_value=True):
                    with mock.patch("geosql.cli.select_optional_dekart_action", return_value=True):
                        with mock.patch("geosql.cli.run_dekart_command", return_value=130):
                            with contextlib.redirect_stdout(output):
                                self.assertEqual(cli.offer_dekart_setup(), 0)

        self.assertIn("Dekart setup was cancelled", output.getvalue())
        self.assertIn("dekart init", output.getvalue())

    def test_readiness_check_uses_tools_json(self):
        completed = mock.Mock(returncode=0)
        with mock.patch("geosql.cli.subprocess.run", return_value=completed) as run:
            self.assertTrue(cli.is_dekart_ready("/bin/dekart"))

        run.assert_called_once_with(
            ["/bin/dekart", "tools", "--json"],
            stdout=cli.subprocess.DEVNULL,
            stderr=cli.subprocess.DEVNULL,
            check=False,
            timeout=10,
        )

    def test_find_environment_dekart_cli_checks_current_python_scripts_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / ("dekart.exe" if os.name == "nt" else "dekart")
            executable.touch()
            with mock.patch("geosql.cli.sysconfig.get_path", return_value=directory):
                self.assertEqual(cli.find_environment_dekart_cli(), str(executable))

    @unittest.skipIf(os.name == "nt", "POSIX symlink behavior")
    def test_expose_dekart_cli_creates_self_cleaning_launcher(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "private" / "dekart"
            target.parent.mkdir()
            target.touch()
            target.chmod(0o755)
            geosql_path = Path(directory) / "bin" / "geosql"
            geosql_path.parent.mkdir()
            geosql_path.touch()
            exposed = geosql_path.parent / "dekart"
            with mock.patch("geosql.cli.shutil.which", side_effect=[str(geosql_path), str(exposed)]):
                self.assertEqual(cli.expose_dekart_cli(str(target)), str(exposed))

            self.assertTrue(exposed.is_file())
            self.assertIn(cli.DEKART_LAUNCHER_MARKER, exposed.read_text(encoding="utf-8"))
            target.unlink()
            result = subprocess.run([str(exposed)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            self.assertEqual(result.returncode, 127)
            self.assertFalse(exposed.exists())

    def test_hidden_environment_cli_is_exposed_without_reinstalling(self):
        with mock.patch("geosql.cli.find_dekart_cli", return_value=None):
            with mock.patch("geosql.cli.find_environment_dekart_cli", return_value="/private/bin/dekart"):
                with mock.patch("geosql.cli.is_interactive_terminal", return_value=True):
                    with mock.patch("geosql.cli.select_optional_dekart_action", return_value=True):
                        with mock.patch("geosql.cli.expose_dekart_cli", return_value="/user/bin/dekart"):
                            with mock.patch("geosql.cli.is_dekart_ready", return_value=True):
                                with mock.patch("geosql.cli.run_dekart_command", return_value=0) as run_command:
                                    self.assertEqual(cli.offer_dekart_setup(), 0)

        run_command.assert_called_once_with(["/user/bin/dekart", "init"])

    def test_stale_launcher_is_refreshed_from_current_environment(self):
        with mock.patch("geosql.cli.find_dekart_cli", side_effect=["/user/bin/dekart", None]):
            with mock.patch("geosql.cli.find_environment_dekart_cli", return_value="/current/bin/dekart"):
                with mock.patch("geosql.cli.is_interactive_terminal", return_value=True):
                    with mock.patch("geosql.cli.is_dekart_ready", side_effect=[False, True]):
                        with mock.patch("geosql.cli.select_optional_dekart_action", return_value=True):
                            with mock.patch("geosql.cli.expose_dekart_cli", return_value="/user/bin/dekart") as expose:
                                with mock.patch("geosql.cli.run_dekart_command", return_value=0) as run_command:
                                    self.assertEqual(cli.offer_dekart_setup(), 0)

        expose.assert_called_once_with("/current/bin/dekart")
        run_command.assert_called_once_with(["/user/bin/dekart", "init"])

    def test_successful_init_must_pass_readiness_check(self):
        output = io.StringIO()
        error = io.StringIO()
        with mock.patch("geosql.cli.find_dekart_cli", return_value="/bin/dekart"):
            with mock.patch("geosql.cli.is_dekart_ready", side_effect=[False, False]):
                with mock.patch("geosql.cli.is_interactive_terminal", return_value=True):
                    with mock.patch("geosql.cli.select_optional_dekart_action", return_value=True):
                        with mock.patch("geosql.cli.run_dekart_command", return_value=0):
                            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
                                self.assertEqual(cli.offer_dekart_setup(), 1)

        self.assertIn("not ready yet", error.getvalue())
        self.assertIn("dekart tools --json", output.getvalue())


if __name__ == "__main__":
    unittest.main()
