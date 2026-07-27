import os
import stat
import tempfile
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlparse

from geosql import cli
from geosql.installation_id import CI_INSTALLATION_ID, get_installation_id


class InstallationIDTest(unittest.TestCase):
    def test_concurrent_first_runs_share_one_persisted_uuid(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": directory}, clear=True):
                with ThreadPoolExecutor(max_workers=8) as executor:
                    installation_ids = list(executor.map(lambda _: get_installation_id(), range(16)))

            self.assertEqual(len(set(installation_ids)), 1)
            self.assertEqual(uuid.UUID(installation_ids[0]).version, 4)
            self.assertEqual(
                Path(directory, "dekart", "installation_id").read_text(encoding="utf-8").strip(),
                installation_ids[0],
            )
            if os.name != "nt":
                mode = stat.S_IMODE(Path(directory, "dekart", "installation_id").stat().st_mode)
                self.assertEqual(mode, 0o600)

    def test_malformed_file_is_replaced_without_breaking_callers(self):
        with tempfile.TemporaryDirectory() as directory:
            installation_path = Path(directory, "dekart", "installation_id")
            installation_path.parent.mkdir(parents=True)
            installation_path.write_text("not-a-uuid", encoding="utf-8")

            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": directory}, clear=True):
                installation_id = get_installation_id()

            self.assertEqual(uuid.UUID(installation_id).version, 4)
            self.assertEqual(installation_path.read_text(encoding="utf-8").strip(), installation_id)

    def test_existing_valid_uuid_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            installation_id = str(uuid.uuid4())
            installation_path = Path(directory, "dekart", "installation_id")
            installation_path.parent.mkdir(parents=True)
            installation_path.write_text(installation_id, encoding="utf-8")

            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": directory}, clear=True):
                self.assertEqual(get_installation_id(), installation_id)

            self.assertEqual(installation_path.read_text(encoding="utf-8"), installation_id)

    def test_ci_uses_reserved_uuid_without_creating_file(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"CI": "1", "XDG_CONFIG_HOME": directory}, clear=True):
                self.assertEqual(get_installation_id(), CI_INSTALLATION_ID)

            self.assertFalse(Path(directory, "dekart", "installation_id").exists())

    def test_opt_out_skips_identity_creation_and_version_ping(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {"DO_NOT_TRACK": "1", "XDG_CONFIG_HOME": directory}
            with mock.patch.dict(os.environ, env, clear=True):
                with mock.patch("geosql.cli.request.urlopen") as urlopen:
                    cli.send_version_ping()

            urlopen.assert_not_called()
            self.assertFalse(Path(directory, "dekart", "installation_id").exists())

    def test_version_ping_sends_installation_id(self):
        installation_id = str(uuid.uuid4())
        with mock.patch("geosql.cli.get_installation_id", return_value=installation_id):
            with mock.patch("geosql.cli.request.urlopen") as urlopen:
                cli.send_version_ping()

        request = urlopen.call_args.args[0]
        self.assertEqual(parse_qs(urlparse(request.full_url).query)["installation_id"], [installation_id])

    def test_identity_failure_keeps_legacy_version_ping(self):
        with mock.patch("geosql.cli.get_installation_id", side_effect=OSError("read-only config")):
            with mock.patch("geosql.cli.request.urlopen") as urlopen:
                cli.send_version_ping()

        request = urlopen.call_args.args[0]
        self.assertNotIn("installation_id", parse_qs(urlparse(request.full_url).query))


if __name__ == "__main__":
    unittest.main()
