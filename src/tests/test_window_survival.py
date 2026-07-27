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

    def test_min_run_ok_non_int_label_does_not_crash(self):
        # databuilder-018 (B1a): object labels like "0.0" are int-coercible via validate._label_ints
        # but crash a bare int(); min_run_ok must format them without raising (guard at both sites).
        df = H.concat(H.block("0.0", 15), H.block("1.0", 60), H.block("2.0", 60))
        df["class"] = df["class"].astype(object)
        findings = min_run_ok(df, "class", None, window=20)   # must NOT raise (parent: int("0.0"))
        flagged = [f for f in findings if f.code == "class_run_below_window"]
        self.assertTrue(flagged)
        self.assertEqual(flagged[0].data["label"], 0)             # "0.0" -> canonical int 0
        self.assertTrue(flagged[0].message.startswith("Class 0's"))


# databuilder-020 (B8): window_yield_findings — per-class window census + imbalance.
class TestWindowYieldFindingsB8(unittest.TestCase):
    def test_window_yield_findings_unit(self):
        import json
        from data_builder.window_survival import window_yield_findings  # RED on parent: does not exist
        # balanced -> yield INFO, no imbalance
        fb = window_yield_findings(H.concat(H.block(0, 60), H.block(1, 60), H.block(2, 60)), "class", None, 20)
        codes = [f.code for f in fb]
        self.assertIn("window_class_yield", codes)
        self.assertNotIn("window_class_imbalance", codes)
        # row-balanced (120/120/120) but window-imbalanced ({0:6,1:2,2:5}) -> ADVISORY, ratio >= 3
        order = [H.block(0, 120)]
        for _ in range(6):
            order += [H.block(1, 20), H.block(2, 4)]
        order += [H.block(2, 96)]
        fi = window_yield_findings(H.concat(*order), "class", None, 20)
        adv = [f for f in fi if f.code == "window_class_imbalance"]
        self.assertEqual(len(adv), 1)
        self.assertGreaterEqual(adv[0].data["ratio"], 3)
        # a class whose runs are < window contributes 0 to pure_windows (and is min_run_ok's job)
        z = H.concat(H.block(0, 60), H.block(1, 12), H.block(0, 60), H.block(1, 12), H.block(2, 60))
        y = [f for f in window_yield_findings(z, "class", None, 20) if f.code == "window_class_yield"][0]
        self.assertEqual(y.data["pure_windows"][1], 0)
        json.dumps(y.data)                                    # JSON-safe: np.int64 keys -> int


if __name__ == "__main__":
    unittest.main()
