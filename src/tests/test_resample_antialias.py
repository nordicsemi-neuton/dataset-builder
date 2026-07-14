"""databuilder-008 — safe anti-aliased downsampling.

Covers the downsample path added over the pre-existing upsample/no-op behaviour: no aliasing, no edge-step
artifact (padtype='line'), short-run refusal, scipy-absent refusal, the no-op pass-through, provenance,
and the gap guard. scipy-dependent tests are skipped when scipy is absent so a scipy-less `unittest
discover` stays green (the engine still runs validate + upsample without scipy).
"""
import json
import sys
import unittest

import numpy as np

import _helpers as H
from data_builder.findings import Severity, make_report
from data_builder.resample import resample_to_rate

try:
    import scipy  # noqa: F401
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

SENSORS = ["acc_x", "acc_y", "acc_z"]


def _run(sig, fs, t0=0.0, label=0):
    n = len(sig)
    df = H.pd.DataFrame({"acc_x": sig, "acc_y": np.zeros(n), "acc_z": np.full(n, 9.78)})
    df["t"] = t0 + np.arange(n) / fs
    df["class"] = label
    return df


def _band_power(y, fs, f_lo, f_hi):
    spec = np.abs(np.fft.rfft(y - np.mean(y))) ** 2
    freqs = np.fft.rfftfreq(len(y), 1.0 / fs)
    return float(spec[(freqs >= f_lo) & (freqs <= f_hi)].sum())


class TestAntialiasDownsample(unittest.TestCase):
    @unittest.skipUnless(_HAS_SCIPY, "scipy required for the anti-alias filter")
    def test_downsample_suppresses_alias_vs_interp(self):
        # 70 Hz tone at 200 Hz -> down to 100 Hz (Nyquist 50). Unfiltered it aliases to 30 Hz.
        fs, target, ftone, n = 200, 100, 70.0, 2000
        t = np.arange(n) / fs
        y = np.sin(2 * np.pi * ftone * t)
        out, _ = resample_to_rate(_run(y, fs), "t", target, SENSORS, "class", None, "s")
        filt = _band_power(out["acc_x"].to_numpy(), target, 25, 35)
        # baseline: the OLD behaviour (plain linear interp onto the coarse grid) — aliases.
        n_new = int(np.floor(t[-1] * target)) + 1
        interp = _band_power(np.interp(np.arange(n_new) / target, t, y), target, 25, 35)
        atten_db = 10 * np.log10(interp / max(filt, 1e-12))
        self.assertGreaterEqual(atten_db, 20.0, f"alias only attenuated {atten_db:.1f} dB")

    @unittest.skipUnless(_HAS_SCIPY, "scipy required for the anti-alias filter")
    def test_no_edge_step_from_dc_offset(self):
        # acc_x carries a large DC offset; padtype='line' must not pull the run edges toward 0.
        fs, n = 200, 1600
        t = np.arange(n) / fs
        y = 9.78 + 0.05 * np.sin(2 * np.pi * 10 * t)
        out, _ = resample_to_rate(_run(y, fs), "t", 100, SENSORS, "class", None, "s")
        yo = out["acc_x"].to_numpy()
        self.assertLess(abs(yo[0] - 9.78), 0.5)
        self.assertLess(abs(yo[-1] - 9.78), 0.5)

    def test_short_run_downsample_refused(self):
        # 100 samples @200 Hz -> 25 Hz (factor 8): far below the filter's minimum -> FIX_REQUIRED, left raw.
        out, findings = resample_to_rate(_run(np.zeros(100), 200), "t", 25, SENSORS, "class", None, "s")
        f = [f for f in findings if f.code == "downsample_run_too_short"]
        self.assertTrue(f, "expected a downsample_run_too_short finding")
        self.assertEqual(f[0].severity, Severity.FIX_REQUIRED)
        self.assertEqual(len(out), 100)  # run left at its original rate (finding blocks the write)

    def test_scipy_absent_refuses_downsample_but_upsample_still_works(self):
        saved = {k: sys.modules.get(k) for k in ("scipy", "scipy.signal")}
        sys.modules["scipy"] = None          # make `from scipy import signal` raise ImportError
        sys.modules["scipy.signal"] = None
        try:
            _, down = resample_to_rate(_run(np.zeros(2000), 200), "t", 100, SENSORS, "class", None, "s")
            self.assertTrue(any(f.code == "scipy_required_for_downsample" for f in down))
            self.assertTrue(any(f.severity == Severity.FIX_REQUIRED
                                for f in down if f.code == "scipy_required_for_downsample"))
            # upsample never touches scipy:
            _, up = resample_to_rate(_run(np.zeros(500), 50), "t", 100, SENSORS, "class", None, "s")
            self.assertFalse(any(f.code == "scipy_required_for_downsample" for f in up))
        finally:
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v

    def test_noop_when_target_equals_source(self):
        _, findings = resample_to_rate(_run(np.zeros(500), 100), "t", 100, SENSORS, "class", None, "s")
        prov = [f for f in findings if f.code == "resample_provenance"]
        self.assertTrue(prov)
        self.assertEqual(prov[0].data["direction"], "up_or_noop")
        self.assertEqual(prov[0].data["method"], "linear-interp")
        json.dumps(make_report(findings).to_dict())  # must not raise (np.int64 etc. would)

    @unittest.skipUnless(_HAS_SCIPY, "scipy required for the anti-alias filter")
    def test_downsample_provenance_is_json_safe(self):
        _, findings = resample_to_rate(_run(np.zeros(2000), 200), "t", 100, SENSORS, "class", None, "s")
        prov = [f for f in findings if f.code == "resample_provenance"]
        self.assertTrue(prov)
        self.assertEqual(prov[0].data["direction"], "down")
        self.assertEqual(prov[0].data["down"], 2)
        json.dumps(make_report(findings).to_dict())

    def test_extreme_downsample_factor_refused_not_crash(self):
        # 1000 Hz -> 1 Hz: ratio rounds up/down to up=0 under limit_denominator; must refuse, not crash.
        out, findings = resample_to_rate(_run(np.zeros(2000), 1000), "t", 1, SENSORS, "class", None, "s")
        self.assertTrue(any(f.code == "downsample_run_too_short" for f in findings))
        self.assertEqual(len(out), 2000)  # left at original rate, no exception

    def test_multi_recording_session_rate_not_doubled(self):
        # Two 200 Hz recordings concatenated in one session with reset clocks. Measuring the rate by a
        # SORTED median would interleave them and read ~400 Hz -> a spurious downsample. It must read ~200.
        r0 = _run(np.zeros(600), 200, t0=0.0, label=0)
        r1 = _run(np.zeros(600), 200, t0=0.0, label=1)  # clock resets to 0 for the 2nd recording
        df = H.concat(r0, r1)
        _, findings = resample_to_rate(df, "t", 200, SENSORS, "class", None, "s")
        prov = [f for f in findings if f.code == "resample_provenance"]
        self.assertTrue(prov)
        self.assertEqual(prov[0].data["direction"], "up_or_noop")  # ~200 == target -> no (spurious) downsample
        self.assertAlmostEqual(prov[0].data["measured_src_hz"], 200.0, delta=5.0)

    def test_large_gap_on_downsample_is_blocking(self):
        n, fs = 2000, 200
        t = np.arange(n) / fs
        t[n // 2:] += 1.0  # a 1 s dropout, still monotonic
        df = H.pd.DataFrame({"acc_x": np.zeros(n), "acc_y": np.zeros(n), "acc_z": np.full(n, 9.78),
                             "t": t, "class": 0})
        _, findings = resample_to_rate(df, "t", 100, SENSORS, "class", None, "s")
        gap = [f for f in findings if f.code == "large_gap_in_resampled_run"]
        self.assertTrue(gap)
        self.assertEqual(gap[0].severity, Severity.FIX_REQUIRED)


if __name__ == "__main__":
    unittest.main()
