import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

import _helpers as H
from data_builder import cli


def _passing_df():
    return H.concat(H.block(0, 60), H.block(1, 60, peak_at=30), H.block(2, 60, peak_at=30))


class TestCli(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        raw = dict(H.BASE_PROFILE)
        raw["sampling_rate_hz"] = 100
        self.profile_path = os.path.join(self.d, "profile.json")
        with open(self.profile_path, "w") as fh:
            json.dump(raw, fh)
        self.csv = os.path.join(self.d, "data.csv")
        _passing_df().to_csv(self.csv, index=False)

    def test_validate_pass_exit_0_and_json(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(["validate", self.csv, "--profile", self.profile_path,
                             "--window", "20", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["verdict"], "PASS")
        self.assertIn("findings", payload)

    def test_validate_out_of_range_window_exit_2(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(["validate", self.csv, "--profile", self.profile_path, "--window", "5"])
        self.assertEqual(code, 2)  # FIX_REQUIRED


if __name__ == "__main__":
    unittest.main()
