"""validate<->prep divergence is governed by pipeline._PREP_REPAIRS, not left to a false "they match".

validate inspects the raw file; prep transforms it and validates the prepared frame, so the two
surfaces legitimately report different finding codes. This test runs both over a fixture matrix and
asserts every code that appears on one surface but not the other is DOCUMENTED in _PREP_REPAIRS — so a
new, undocumented divergence fails the suite and forces someone to classify it (sprint acceptance;
the previous blanket "prep == validate" criterion was false for at least eight code pairs).
"""
import csv
import os
import tempfile
import unittest

import _helpers as H  # noqa: F401  (puts src on path)

from data_builder.profile import DatasetProfile
from data_builder import validate as V, pipeline as P

SENS = ["acc_x", "acc_y", "acc_z"]


def _prof(**over):
    base = dict(dataset_name="m", label_column="class", sensor_columns=SENS, session_column=None,
                time_column="t", separator="comma", sampling_rate_hz=100,
                task_type="multiclass_classification", target_technology="neuton",
                class_encoding={"map": {"a": 0, "b": 1, "c": 2}, "continuous_classes": [],
                                "gesture_classes": []},
                window={"candidates": [20], "shift": 20, "frequency_domain_features": False},
                holdout_path=None, notes="")
    base.update(over)
    return DatasetProfile.from_dict(base)


def _rows(n=60, nonnum=False, run=None):
    r, k = [], 0
    if run is None:
        for c in range(3):
            for i in range(n):
                v = [(i * 7 + c * 13 + a) % 100 for a in range(3)]
                if nonnum and c == 0 and i == 0:
                    v[0] = "oops"
                r.append(v + [round(k * 0.01, 4), c]); k += 1
    else:  # short interleaved runs (each class run < window)
        for i in range(n * 3):
            r.append([(i * 7 + a) % 100 for a in range(3)] + [round(i * 0.01, 4), (i // run) % 3])
    return r


def _write(path, rows, crlf=False):
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(SENS + ["t", "class"]); w.writerows(rows)
    if crlf:
        with open(path, "rb") as fh:
            data = fh.read()
        with open(path, "wb") as fh:
            fh.write(data.replace(b"\n", b"\r\n"))


def _validate_codes(path, pr):
    sp = None if pr.signal_processing is None else pr.signal_processing
    rep = V.run_checks(path, pr, 20, pr.frequency_domain, sp_on=sp)
    return {f.code for f in rep.findings}


def _prep_codes(path, pr, **kw):
    with tempfile.TemporaryDirectory() as d:
        res = P.prep([path], pr, os.path.join(d, "o.csv"), 20, write_anyway=True, **kw)
        return {f.code for f in res["report"].findings}


class TestPrepValidateParity(unittest.TestCase):
    def _scenarios(self, d):
        gest = _prof(class_encoding={"map": {"a": 0, "b": 1, "c": 2}, "continuous_classes": [0],
                                     "gesture_classes": [1, 2]})
        out = []
        p = os.path.join(d, "gest.csv"); _write(p, _rows()); out.append(("gesture", gest, p, {}))
        p = os.path.join(d, "tab.csv"); _write(p, _rows())
        out.append(("tabular_spoff", _prof(signal_processing=False), p, {}))
        p = os.path.join(d, "nn.csv"); _write(p, _rows(nonnum=True)); out.append(("nonnumeric", _prof(), p, {}))
        p = os.path.join(d, "crlf.csv"); _write(p, _rows(), crlf=True); out.append(("crlf", _prof(), p, {}))
        p = os.path.join(d, "reg.csv"); _write(p, _rows())
        out.append(("regression", _prof(task_type="regression", class_encoding=None), p, {}))
        p = os.path.join(d, "rs.csv"); _write(p, _rows()); out.append(("resample", _prof(), p, {"target_rate": 50.0}))
        p = os.path.join(d, "short.csv"); _write(p, _rows(run=5)); out.append(("shortruns", _prof(), p, {}))
        return out

    def test_every_divergence_is_documented(self):
        with tempfile.TemporaryDirectory() as d:
            undocumented = {}
            for name, pr, path, kw in self._scenarios(d):
                v = _validate_codes(path, pr)
                p = _prep_codes(path, pr, **kw)
                diverge = (v ^ p) - P._PREP_REPAIRS_FLAT   # symmetric difference minus the allowlist
                if diverge:
                    undocumented[name] = sorted(diverge)
            self.assertEqual(undocumented, {},
                             "undocumented validate<->prep divergence (classify in pipeline._PREP_REPAIRS): "
                             + repr(undocumented))

    def test_skip_intake_is_the_intake_subset(self):
        # _SKIP_INTAKE must stay a subset of the documented allowlist (single source of truth).
        self.assertTrue(P._SKIP_INTAKE <= P._PREP_REPAIRS_FLAT)
        self.assertEqual(P._SKIP_INTAKE, P._PREP_REPAIRS["intake_repaired_on_write"])


if __name__ == "__main__":
    unittest.main()
