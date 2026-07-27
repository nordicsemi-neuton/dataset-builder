"""databuilder-011 (sprint B2b) — the label-keyspace crash in relabel_contiguous.

A classification label column that mixes class NAMES and class INDICES used to raise KeyError inside
relabel_contiguous (exit 1, no finding). It is now a total int64 encoding blocked by a FIX_REQUIRED
finding: `label_keyspace_mixed` (no unknowns) or `label_not_in_map` (a genuinely-unknown label too).

Red on parent 3dadb7e (KeyError): TestMixedKeyspaceCrash.* and TestMixedViaPrep.*. The byte-identity
tests are GREEN on the parent by design — they guard that shapes which work today are unchanged (P0.2:
byte-identity for unchanged label shapes). Demonstrate red→green with:
    git checkout 3dadb7e -- src/data_builder/relabel.py
    python3 -m unittest discover -s src/tests
    git checkout HEAD -- src/data_builder/relabel.py
"""
import os
import tempfile
import unittest

import numpy as np
import pandas as pd

import _helpers as H
from data_builder.profile import DatasetProfile
from data_builder.relabel import relabel_contiguous
from data_builder import pipeline

CMAP = {"idle": 0, "left": 1, "right": 2}


def _map_profile():
    """A classification profile whose class map is CMAP (BASE_PROFILE already carries it)."""
    raw = dict(H.BASE_PROFILE)
    raw["sampling_rate_hz"] = 100
    return DatasetProfile.from_dict(raw)


class TestMixedKeyspaceCrash(unittest.TestCase):
    """The core defect: a mixed name/index column no longer crashes; it blocks with an int64 frame."""

    def test_mixed_name_and_index_blocks_not_crashes(self):
        """Red on parent: KeyError '1'. After: label_keyspace_mixed, int64 [0,1,2]."""
        out, dictionary, findings = relabel_contiguous(
            pd.DataFrame({"class": ["idle", "1", "right"]}), "class", CMAP)
        self.assertEqual(out["class"].tolist(), [0, 1, 2])
        codes = {f.code for f in findings}
        self.assertIn("label_keyspace_mixed", codes)
        self.assertNotIn("label_not_in_map", codes)

    def test_mixed_frame_dtype_is_int64(self):
        """rev-3 guard, measured directly on the returned frame (not via 'no ValueError' / CSV re-read):
        an object column would re-crash center.py's int(cls)/sorted(unique) downstream."""
        out, _, _ = relabel_contiguous(
            pd.DataFrame({"class": ["idle", "1", "right"]}), "class", CMAP)
        self.assertEqual(out["class"].dtype, np.int64)

    def test_mixed_dictionary_keeps_real_class_names(self):
        """Guards the idx_to_name landmine: a bare index-string must not overwrite a real class name."""
        _, dictionary, _ = relabel_contiguous(
            pd.DataFrame({"class": ["idle", "1", "right"]}), "class", CMAP)
        self.assertEqual(dictionary, {"idle": 0, "left": 1, "right": 2})
        self.assertIn("right", dictionary)          # the real name at index 2, not the token "2"
        self.assertNotIn("1", dictionary)           # the bare index-string is never a dictionary key
        self.assertNotIn("2", dictionary)

    def test_mixed_with_absent_class_still_reports_absence(self):
        """[idle,1] -> classes 0,1 present, index 2 absent: keyspace-mixed AND mapped_class_absent."""
        out, _, findings = relabel_contiguous(
            pd.DataFrame({"class": ["idle", "1"]}), "class", CMAP)
        self.assertEqual(out["class"].tolist(), [0, 1])
        codes = {f.code for f in findings}
        self.assertIn("label_keyspace_mixed", codes)
        self.assertIn("mapped_class_absent", codes)
        absent = next(f.data["absent"] for f in findings if f.code == "mapped_class_absent")
        self.assertEqual(absent, [2])

    def test_mixed_plus_unknown_reports_the_unknown_not_the_mix(self):
        """[idle,1,jump]: an unknown label is the more actionable defect -> label_not_in_map wins."""
        out, dictionary, findings = relabel_contiguous(
            pd.DataFrame({"class": ["idle", "1", "jump"]}), "class", CMAP)
        self.assertEqual(out["class"].tolist(), [0, 1, 3])
        self.assertEqual(out["class"].dtype, np.int64)
        codes = {f.code for f in findings}
        self.assertIn("label_not_in_map", codes)
        self.assertNotIn("label_keyspace_mixed", codes)

    def test_label_keyspace_mixed_severity_and_rule_ref(self):
        """FIX_REQUIRED (exit 2, never WILL_LOSE_DATA), anchored to an existing heading."""
        _, _, findings = relabel_contiguous(
            pd.DataFrame({"class": ["idle", "1"]}), "class", CMAP)
        f = next(f for f in findings if f.code == "label_keyspace_mixed")
        self.assertEqual(f.severity, "fix-required")
        self.assertEqual(f.group, "HARD-REJECT")
        self.assertTrue(f.rule_ref.endswith("#classification-target-rules"))


class TestByteIdentityUnchangedShapes(unittest.TestCase):
    """Every label shape that works today is unchanged (values, dtype, dictionary, finding codes).

    Green on parent by design — regression guards, not red→green. The full SHA-256 matrix lives in
    dev/databuilder-011_relabel_matrix.py; these pin the load-bearing shapes in the suite.
    """

    def _run(self, labels):
        return relabel_contiguous(pd.DataFrame({"class": labels}), "class", CMAP)

    def test_pure_names_unchanged(self):
        out, d, findings = self._run(["idle", "left", "right", "idle"])
        self.assertEqual(out["class"].tolist(), [0, 1, 2, 0])
        self.assertEqual(out["class"].dtype, np.int64)
        self.assertEqual(d, {"idle": 0, "left": 1, "right": 2})
        self.assertEqual([f.code for f in findings], [])

    def test_pure_indices_unchanged(self):
        out, d, findings = self._run(["0", "1", "2", "0"])
        self.assertEqual(out["class"].tolist(), [0, 1, 2, 0])
        self.assertEqual(d, {"idle": 0, "left": 1, "right": 2})
        self.assertEqual([f.code for f in findings], [])

    def test_genuine_unknown_unchanged(self):
        out, d, findings = self._run(["idle", "left", "jump"])
        self.assertEqual(out["class"].tolist(), [0, 1, 3])
        self.assertEqual(out["class"].dtype, np.int64)
        self.assertEqual(d, {"idle": 0, "left": 1, "jump": 3})
        self.assertEqual([f.code for f in findings], ["label_not_in_map", "mapped_class_absent"])

    def test_names_class_absent_unchanged(self):
        out, d, findings = self._run(["idle", "left"])
        self.assertEqual(out["class"].tolist(), [0, 1])
        self.assertEqual([f.code for f in findings], ["mapped_class_absent"])

    def test_branch2_collision_ship_is_unchanged_not_newly_blocked(self):
        """K1 (pre-existing branch-2 silent mis-encode), OUT OF SCOPE here: the fix must NOT block it,
        or B2b would be doing the non-monotone tightening it deliberately split to the sprint Log."""
        out, d, findings = relabel_contiguous(
            pd.DataFrame({"c": ["1", "0"]}), "c", {"1": 0, "walk": 1})
        self.assertEqual(out["c"].tolist(), [1, 0])          # ships the by-index reading, as today
        self.assertEqual([f.code for f in findings], [])     # still no finding (PASS) — unchanged


class TestMixedViaPrep(unittest.TestCase):
    """The default gesture-prep path: center_per_class runs on the mixed frame BEFORE the block, so an
    object column would re-crash centering on this ordinary (non --write-anyway) run — the real rev-3
    guard. Red on parent (KeyError inside relabel at pipeline.py:176, exit 1)."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.out = os.path.join(self.d, "out.csv")

    def _mixed_frame(self):
        # 3 gesture-ish blocks, labelled by a MIX of names and one index: idle / "1" (=left) / right.
        b0 = H.block("idle", 60, peak_at=30)
        b1 = H.block("1", 60, peak_at=30)          # the index for class "left"
        b2 = H.block("right", 60, peak_at=30)
        return H.concat(b0, b1, b2)

    def test_prep_blocks_without_crashing_on_default_path(self):
        """Red on parent: exit 1 KeyError. After: FIX_REQUIRED, written False, no exception escapes."""
        src = os.path.join(self.d, "in.csv")
        self._mixed_frame().to_csv(src, index=False)
        res = pipeline.prep([src], _map_profile(), self.out, window=20)   # no write_anyway
        self.assertEqual(res["report"].verdict, "FIX_REQUIRED")
        self.assertFalse(res["written"])
        self.assertIn("label_keyspace_mixed", {f.code for f in res["report"].findings})
        self.assertFalse(os.path.exists(self.out))

    def test_prep_write_anyway_writes_int64_target(self):
        """Forced override: centering runs, an int64 target reaches disk, no exception."""
        src = os.path.join(self.d, "in.csv")
        self._mixed_frame().to_csv(src, index=False)
        res = pipeline.prep([src], _map_profile(), self.out, window=20, write_anyway=True)
        self.assertTrue(res["written"])
        written = pd.read_csv(self.out)
        self.assertTrue(set(written["class"].unique()) <= {0, 1, 2})


if __name__ == "__main__":
    unittest.main()
