#!/usr/bin/env python3
"""
feature_mask_decoder.py — decode FEATURES_EXTRACTION_MASK from a Nordic Edge AI Lab
model archive into a per-axis feature usage table.

Usage:
    python3 feature_mask_decoder.py <path_to_nrf_edgeai_user_model.c>

Reads the FEATURES_EXTRACTION_MASK[] array (6 uint64_t values, one per input axis)
and prints which time-domain features are enabled for each axis. Use this to
quickly answer questions like:
- Is `LR_SLOPE` / `LR_INTERCEPT` enabled? (the only signed-asymmetry features)
- How many features per axis? Total features?
- Which features are missing across ALL axes?

The bit ordering follows nrf_edgeai_dsp_pipeline_types.h's
nrf_edgeai_feature_timedomain_t enum.
"""
import re
import sys
from pathlib import Path

# Windows consoles/pipes default to cp1252, which cannot encode every character in
# this tool's output; degrade to '?' instead of crashing (no-op on UTF-8 terminals).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(errors="replace")
        except (ValueError, OSError):
            pass


# Bit position -> feature name (matches NRF_EDGEAI_FEATURE_TIMEDOMAIN enum order)
TIME_FEATURES = [
    "MIN", "MAX", "RANGE", "MEAN", "MAD", "SKEW", "KUR", "STD", "RMS",
    "MCR", "ZCR", "TCR", "P2P_LF", "P2P_HF", "ABSMEAN", "AMDF",
    "PSCR", "NSCR", "PSOZ", "PSOM", "PSOS", "CREST", "RMDS", "AUTOCORR",
    "HJ_MOBILITY", "HJ_COMPLEXITY", "LR_SLOPE", "LR_INTERCEPT",
]

AXIS_NAMES_DEFAULT = ["axis_0", "axis_1", "axis_2", "axis_3", "axis_4", "axis_5"]


def parse_mask_array(c_source: str) -> list[int]:
    """Extract the FEATURES_EXTRACTION_MASK[] hex values from C source text."""
    m = re.search(
        r"static\s+const\s+uint64_t\s+FEATURES_EXTRACTION_MASK\[\]\s*=\s*\{([^}]+)\}",
        c_source,
    )
    if not m:
        sys.exit("ERROR: FEATURES_EXTRACTION_MASK array not found")
    body = m.group(1)
    hexes = re.findall(r"0x[0-9a-fA-F]+", body)
    return [int(h, 16) for h in hexes]


def decode_one_axis(mask: int) -> dict:
    """Return {feature_name: bool} for time-domain features (low 32 bits after >> 32)."""
    # The runtime stores time-domain mask in the upper 32 bits of the 64-bit field
    lo = (mask >> 32) & 0xFFFFFFFF
    return {f: bool((lo >> i) & 1) for i, f in enumerate(TIME_FEATURES)}


def main():
    if len(sys.argv) < 2:
        sys.exit(f"Usage: {sys.argv[0]} <path_to_nrf_edgeai_user_model.c>")
    path = Path(sys.argv[1])
    src = path.read_text()
    masks = parse_mask_array(src)

    # Try to find INPUT_UNIQ_FEATURES_NUM for axis-name length
    n_match = re.search(r"INPUT_UNIQ_FEATURES_NUM\s+(\d+)", src)
    n_axes = int(n_match.group(1)) if n_match else len(masks)
    axis_names = AXIS_NAMES_DEFAULT[:n_axes]

    decoded = [decode_one_axis(m) for m in masks[:n_axes]]

    print(f"FEATURES_EXTRACTION_MASK ({len(masks)} axes):")
    for i, m in enumerate(masks[:n_axes]):
        print(f"  axis_{i}: 0x{m:016x}")
    print()

    # Pretty table
    header = f"  {'feature':>15}  " + "  ".join(f"{a:>7}" for a in axis_names)
    print(header)
    for i, fname in enumerate(TIME_FEATURES):
        cells = [(decoded[a][fname]) for a in range(n_axes)]
        marks = "  ".join(f"{('YES' if c else '   '):>7}" for c in cells)
        flag = "  <-- direction-encoding" if fname in {"LR_SLOPE", "LR_INTERCEPT"} else ""
        print(f"  {fname:>15}  {marks}{flag}")

    # Summary
    print()
    per_axis = [sum(d.values()) for d in decoded]
    print(f"Features per axis: {per_axis}")
    print(f"Total features: {sum(per_axis)}")
    missing_everywhere = [
        f for f in TIME_FEATURES if not any(d[f] for d in decoded)
    ]
    print(f"Features missing on EVERY axis: {missing_everywhere}")
    if "LR_SLOPE" in missing_everywhere or "LR_INTERCEPT" in missing_everywhere:
        print()
        print("WARNING: LR_SLOPE / LR_INTERCEPT not enabled on any axis.")
        print("These are the only features encoding signed asymmetry within a window —")
        print("required for direction-of-motion discrimination (left/right, up/down).")


if __name__ == "__main__":
    main()
