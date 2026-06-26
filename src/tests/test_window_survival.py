import unittest

import _helpers as H
from data_builder.window_survival import run_lengths, simulate_survival, min_run_ok


def _df():
    # class 0: one run of 40; class 1: two runs of 12 (max_run 12)
    return H.concat(H.block(0, 40), H.block(1, 12), H.block(0, 5), H.block(1, 12))


class TestWindowSurvival(unittest.TestCase):
    def test_run_lengths(self):
        agg = run_lengths(_df(), "class", None)
        self.assertEqual(agg[0]["max_run"], 40)
        self.assertEqual(agg[1]["max_run"], 12)

    def test_min_run_below_window_flagged(self):
        findings = min_run_ok(_df(), "class", None, window=20)
        codes = [f.code for f in findings]
        self.assertIn("class_run_below_window", codes)
        self.assertTrue(all("Processed Data view" in f.message for f in findings))
        # class 0 (max_run 40) should NOT be flagged
        self.assertTrue(all(f.data["label"] == 1 for f in findings))

    def test_simulate_counts(self):
        df = H.concat(H.block(0, 100))
        total, pure, mixed, counts = simulate_survival(df, "class", None, window=20, shift=20)
        self.assertEqual(total, 5)
        self.assertEqual(pure, 5)
        self.assertEqual(mixed, 0)


if __name__ == "__main__":
    unittest.main()
