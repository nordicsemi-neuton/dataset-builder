import unittest

import _helpers as H
from data_builder.relabel import relabel_contiguous


class TestRelabel(unittest.TestCase):
    def test_numeric_contiguous_unchanged(self):
        df = H.pd.DataFrame({"class": ["0", "1", "2", "0"]})
        out, dictionary, findings = relabel_contiguous(df, "class")
        self.assertEqual(sorted(out["class"].unique().tolist()), [0, 1, 2])
        self.assertFalse([f for f in findings if f.severity in ("hard-reject", "fix-required")])

    def test_numeric_gap_remapped(self):
        df = H.pd.DataFrame({"class": ["0", "1", "3"]})
        out, dictionary, findings = relabel_contiguous(df, "class")
        self.assertEqual(sorted(out["class"].unique().tolist()), [0, 1, 2])
        self.assertTrue(any(f.code == "noncontiguous_labels" for f in findings))

    def test_string_labels_with_map(self):
        df = H.pd.DataFrame({"class": ["idle", "left", "right", "idle"]})
        mp = {"idle": 0, "left": 1, "right": 2}
        out, dictionary, findings = relabel_contiguous(df, "class", mp)
        self.assertEqual(out["class"].tolist(), [0, 1, 2, 0])
        self.assertEqual(dictionary["idle"], 0)

    def test_label_not_in_map_flagged(self):
        df = H.pd.DataFrame({"class": ["idle", "left", "unknown_gesture"]})
        mp = {"idle": 0, "left": 1}
        _, _, findings = relabel_contiguous(df, "class", mp)
        self.assertTrue(any(f.code == "label_not_in_map" for f in findings))


if __name__ == "__main__":
    unittest.main()
