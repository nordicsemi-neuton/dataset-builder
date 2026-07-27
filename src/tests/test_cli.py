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

    def test_validate_sp_off_tabular_runs_without_window(self):
        # A tabular profile (SP off, no gesture classes) validates with no --window and no candidates.
        raw = dict(H.BASE_PROFILE, sampling_rate_hz=100, signal_processing=False, window=None,
                   class_encoding={"map": {"a": 0, "b": 1, "c": 2}, "continuous_classes": [],
                                   "gesture_classes": []})
        p = os.path.join(self.d, "tab.json")
        with open(p, "w") as fh:
            json.dump(raw, fh)
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(["validate", self.csv, "--profile", p, "--json"])
        self.assertEqual(code, 0)  # window checks skipped; sp_off_unverified is ADVISORY
        self.assertIn("sp_off_unverified", [f["code"] for f in json.loads(buf.getvalue())["findings"]])

    def test_validate_malformed_candidate_errors_loudly(self):
        # A non-int window candidate must not be silently skipped (it would hide the window checks).
        raw = dict(H.BASE_PROFILE, sampling_rate_hz=100,
                   window={"candidates": [None], "shift": 20, "frequency_domain_features": False})
        p = os.path.join(self.d, "badcand.json")
        with open(p, "w") as fh:
            json.dump(raw, fh)
        with self.assertRaises(SystemExit) as cm:
            cli.main(["validate", self.csv, "--profile", p])
        self.assertEqual(cm.exception.code, 4)


if __name__ == "__main__":
    unittest.main()
