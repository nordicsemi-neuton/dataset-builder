"""databuilder-014 (B7): centering announces the discard, then quantifies it (domain P-18).

Red on parent 7c48e79 (no centering_rows_discarded finding), green after. Imports nothing new from
data_builder.center -- only center_per_class, already public -- so `git checkout 7c48e79 --
src/data_builder/center.py` yields clean assertion failures, not an ImportError that would hide the
incumbent test_center.py tests. Asserts on finding codes, Finding.data, Finding.message,
Finding.rule_ref (all stable on the Finding dataclass).
"""
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

import numpy as np

import _helpers as H
from data_builder import cli
from data_builder.center import center_per_class

NOISE, AMP = 0.01, 6.0


def gest(label, n, peaks, seed):
    """The spec's pinned generator: draw order z, then acc_x, acc_y (test_pipeline.py:67-75)."""
    rng = np.random.RandomState(seed)
    z = NOISE * rng.randn(n)
    for p in peaks:
        z[p - 1:p + 2] += AMP
    df = H.pd.DataFrame({"acc_x": NOISE * rng.randn(n), "acc_y": NOISE * rng.randn(n), "acc_z": z})
    df["class"] = label
    return df


class _Missing:
    """Stand-in when the finding is absent, so `.message`/`.data` access fails as an assertion
    (not an AttributeError) on the parent commit -- keeps the red→green red assertion-clean (P0.2)."""
    def __getattr__(self, name):
        raise AssertionError("centering_rows_discarded finding is absent")


def _delta(findings):
    for f in findings:
        if f.code == "centering_rows_discarded":
            return f
    return _Missing()


def _by_label(finding):
    return {e["label"]: e for e in finding.data["per_class"]}


class TestCenterRowDelta(unittest.TestCase):
    # --- criterion 1: partial loss is announced and quantified ---
    def test_partial_loss_reports_row_delta(self):
        df = H.concat(H.block(0, 15000),
                      gest(1, 15000, [150 * k for k in range(1, 101)], 11),
                      gest(2, 15000, [37 * k for k in range(1, 401)], 12))
        out, findings = center_per_class(df, H.prof(), window=20)
        f = _delta(findings)
        self.assertIsNotNone(f, "no centering_rows_discarded finding")
        self.assertEqual(f.data["rows_in"], len(df))
        self.assertEqual(f.data["rows_out"], len(out))
        self.assertEqual(sum(e["rows_in"] for e in f.data["per_class"]), len(df))
        self.assertEqual(sum(e["rows_out"] for e in f.data["per_class"]), len(out))
        self.assertEqual(f.severity, "info")

    # --- criterion 2: all three kinds + both blocking branches, one frame ---
    def test_ledger_covers_all_kinds_and_branches(self):
        prof = H.prof(class_encoding={"map": {"idle": 0, "left": 1, "right": 2, "hold": 3},
                                      "continuous_classes": [0, 3], "gesture_classes": [1, 2]})
        df = H.concat(
            H.block(0, 40),                         # continuous, trims
            gest(1, 240, [40, 90, 140, 190], 2),    # gesture, keeps
            gest(2, 15, [7], 2),                    # gesture, keeps nothing
            H.block(3, 15),                         # continuous, too short
            H.block(5, 50),                         # not in any list -> unpartitioned
        )
        _, findings = center_per_class(df, prof, window=20)
        by = _by_label(_delta(findings))
        self.assertEqual(by[0]["kind"], "continuous")
        self.assertEqual(by[3]["kind"], "continuous")
        self.assertEqual(by[3]["rows_out"], 0)
        self.assertIsNone(by[0]["events_detected"])
        self.assertEqual(by[5]["kind"], "unpartitioned")
        self.assertEqual(by[5]["rows_out"], by[5]["rows_in"])
        self.assertEqual(by[1]["kind"], "gesture")
        self.assertIsNotNone(by[1]["events_detected"])
        self.assertTrue(any(x.code == "class_too_short_to_trim" for x in findings))
        self.assertTrue(any(x.code == "no_centered_windows" for x in findings))
        msg = _delta(findings).message
        self.assertIn("too short to fill one window", msg)
        self.assertIn("trimmed to whole windows", msg)
        self.assertIn("left untouched", msg)

    # --- criterion 3: winning-axis event count ---
    def test_events_detected_from_winning_axis(self):
        df = gest(1, 15000, [150 * k for k in range(1, 101)], 11)
        _, findings = center_per_class(df, H.prof(), window=20)
        e = _by_label(_delta(findings))[1]
        self.assertEqual(e["events_detected"], 99)
        # window 64: an event is detected then dropped -> detected(3) > windows kept(2)
        df64 = gest(1, 640, [30, 200, 400], 3)
        _, findings64 = center_per_class(df64, H.prof(), window=64)
        e64 = _by_label(_delta(findings64))[1]
        self.assertEqual(e64["events_detected"], 3)
        self.assertEqual(e64["rows_out"], 2 * 64)
        self.assertGreater(e64["events_detected"], e64["rows_out"] // 64)

    # --- criterion 4: no sensor column present -> 0, never -1/None in the message ---
    def test_no_sensor_column_present(self):
        df = gest(1, 240, [40, 90, 140, 190], 2)
        prof = H.prof(sensor_columns=["nope_x"])
        _, findings = center_per_class(df, prof, window=20)
        e = _by_label(_delta(findings))[1]
        self.assertEqual(e["events_detected"], 0)
        self.assertEqual(e["rows_out"], 0)
        self.assertNotIn("-1", _delta(findings).message)
        self.assertNotIn("None", _delta(findings).message)

    # --- criterion 5: wording branches ---
    def test_wording_leads_and_plurals(self):
        # lead 1 (gesture present, rows_out > 0)
        g = H.concat(H.block(0, 200), gest(1, 240, [34 * k for k in range(1, 7)], 2))
        self.assertIn("keeps one window per detected gesture",
                      _delta(center_per_class(g, H.prof(), 20)[1]).message)
        # lead 2 (no gesture in the frame): neutral, true for trimmed-continuous and untouched alike
        m2 = _delta(center_per_class(H.block(0, 53), H.prof(), 20)[1]).message
        self.assertIn("Centering kept 40 of 53 rows", m2)
        self.assertNotIn("trimmed each class", m2)  # would be false on an unpartitioned-only frame
        # lead 3 (total loss)
        tl = H.concat(H.block(0, 15), gest(1, 15, [7], 2))
        self.assertIn("produced no rows at all",
                      _delta(center_per_class(tl, H.prof(), 20)[1]).message)
        # singular gesture-event form and never "won't center"
        one = gest(1, 300, [150], 2)
        m = _delta(center_per_class(one, H.prof(), 20)[1]).message
        self.assertIn("1 gesture event found", m)
        self.assertNotIn("1 gesture events", m)
        for frame in (g, tl, one):
            self.assertNotIn("won't center", _delta(center_per_class(frame, H.prof(), 20)[1]).message)

    def test_truncation_marker_over_eight_classes(self):
        prof = H.prof(class_encoding={"map": {f"c{i}": i for i in range(10)},
                                      "continuous_classes": [0],
                                      "gesture_classes": list(range(1, 10))})
        frames = [H.block(0, 200)] + [gest(i, 240, [34 * k for k in range(1, 7)], i) for i in range(1, 10)]
        _, findings = center_per_class(H.concat(*frames), prof, window=20)
        m = _delta(findings).message
        self.assertIn("and 2 more classes", m)   # 10 classes, 8 shown -> 2 hidden, correctly pluralised
        self.assertNotIn("classs", m)
        self.assertEqual(len(_delta(findings).data["per_class"]), 10)  # data never truncated

    # --- criterion 6: total loss takes the early return, still reports ---
    def test_total_loss_reports_hundred_percent(self):
        df = H.concat(H.block(0, 15), gest(1, 15, [7], 2))
        out, findings = center_per_class(df, H.prof(), window=20)
        self.assertEqual(len(out), 0)
        f = _delta(findings)
        self.assertEqual(f.data["discarded_percent"], 100.0)
        self.assertIn("produced no rows at all", f.message)

    # --- criterion 7: clause order (discard desc, ties by label asc); data in label order ---
    def test_message_order_vs_data_order(self):
        # class 2 loses more than class 1 -> class 2 first in the message; data stays label-ordered
        df = H.concat(H.block(0, 200),
                      gest(1, 240, [40, 90, 140, 190], 2),        # ~66%
                      gest(2, 240, [30 * k for k in range(1, 9)], 2))  # denser -> different %
        f = _delta(center_per_class(df, H.prof(), 20)[1])
        self.assertEqual([e["label"] for e in f.data["per_class"]], [0, 1, 2])  # label order in data
        # message orders by discard desc: the higher-% class name appears before the lower-% one
        by = _by_label(f)
        hi, lo = sorted([1, 2], key=lambda c: -by[c]["discarded_percent"])
        self.assertLess(f.message.index(f"class {hi}:"), f.message.index(f"class {lo}:"))

    # --- criterion 8: rule_ref present and resolves (checked structurally + by test_rule_refs) ---
    def test_rule_ref_non_empty(self):
        df = H.concat(H.block(0, 200), gest(1, 240, [34 * k for k in range(1, 7)], 2))
        f = _delta(center_per_class(df, H.prof(), 20)[1])
        self.assertTrue(f.rule_ref)
        self.assertIn("#", f.rule_ref)

    # --- criterion 9: verdict-neutral (INFO does not raise the verdict) ---
    def test_info_is_verdict_neutral(self):
        from data_builder.findings import make_report
        df = H.concat(H.block(0, 15000),
                      gest(1, 15000, [150 * k for k in range(1, 101)], 11),
                      gest(2, 15000, [37 * k for k in range(1, 401)], 12))
        _, findings = center_per_class(df, H.prof(), window=20)
        # only the row-delta finding present here -> PASS
        self.assertEqual(make_report([_delta(findings)]).verdict, "PASS")

    # --- criterion 11: empty frame is silent ---
    def test_empty_frame_silent(self):
        df = H.pd.DataFrame({c: [] for c in ("acc_x", "acc_y", "acc_z", "class")})
        out, findings = center_per_class(df, H.prof(), window=20)
        self.assertEqual(len(out), 0)
        self.assertFalse(any(f.code == "centering_rows_discarded" for f in findings))


class TestCenterRowDeltaJson(unittest.TestCase):
    # --- criterion 10: prep --json exit 0, parses, finding present with its ledger ---
    def test_prep_json_carries_ledger(self):
        d = tempfile.mkdtemp()
        raw = dict(H.BASE_PROFILE)
        raw["sampling_rate_hz"] = 100
        pp = os.path.join(d, "p.json")
        with open(pp, "w") as fh:
            json.dump(raw, fh)
        csv = os.path.join(d, "in.csv")
        H.concat(H.block(0, 200), gest(1, 240, [34 * k for k in range(1, 7)], 2),
                 gest(2, 240, [34 * k for k in range(1, 7)], 3)).to_csv(csv, index=False)
        out = os.path.join(d, "out.csv")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(["prep", csv, "--profile", pp, "--out", out, "--window", "20", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        f = next((x for x in payload["findings"] if x["code"] == "centering_rows_discarded"), None)
        self.assertIsNotNone(f)
        self.assertIn("per_class", f["data"])
        self.assertEqual(len(f["data"]["per_class"]), 3)


if __name__ == "__main__":
    unittest.main()
