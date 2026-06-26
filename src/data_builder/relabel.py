"""relabel — encode the label column to contiguous ints from 0, returning the dictionary.

Handles string class names and already-numeric labels, with or without a desired map. Reconciles the
desired map against the actual labels (domain P-03): a label in the data not covered by the map (or
vice-versa) is a finding, not a silent guess.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .findings import Finding, Group, Severity

DATASET_REQ = "wiki/architecture/platform-dataset-requirements.md"


def _as_token(v) -> str:
    s = str(v).strip().strip('"')
    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
    except ValueError:
        pass
    return s


def relabel_contiguous(df: pd.DataFrame, label_col: str, desired_map: dict | None = None):
    """Return (df, dictionary, findings). dictionary maps original-token -> contiguous int from 0."""
    findings: list[Finding] = []
    df = df.copy()
    tokens = [_as_token(v) for v in df[label_col].to_numpy()]
    present = sorted(set(tokens))

    if desired_map:
        # desired_map: name -> index. Accept data labelled by the name OR by the index.
        name_to_idx = {str(k): int(v) for k, v in desired_map.items()}
        idx_to_name = {v: k for k, v in name_to_idx.items()}
        by_name = set(name_to_idx)
        by_idx = {str(i) for i in name_to_idx.values()}

        if set(present) <= by_name:
            mapping = name_to_idx
        elif set(present) <= by_idx:
            mapping = {str(i): i for i in name_to_idx.values()}
        else:
            unknown = sorted(set(present) - by_name - by_idx)
            findings.append(Finding(
                Group.HARD_REJECT, Severity.FIX_REQUIRED, "label_not_in_map",
                f"The data contains label(s) {unknown} not in the provided class encoding. Reconcile the "
                f"class map with the actual labels before encoding.",
                f"{DATASET_REQ}#classification-target-rules", {"unknown": unknown}))
            # best effort: extend the map so we still produce a frame, but the finding blocks the write
            mapping = dict(name_to_idx)
            nxt = max(name_to_idx.values(), default=-1) + 1
            for u in unknown:
                mapping[u] = nxt
                nxt += 1
            idx_to_name = {v: k for k, v in mapping.items()}

        df[label_col] = np.array([mapping[t] for t in tokens], dtype=np.int64)
        used = sorted(set(df[label_col].tolist()))
        dictionary = {idx_to_name.get(i, str(i)): i for i in used}
        missing = sorted(set(name_to_idx.values()) - set(used))
        if missing:
            findings.append(Finding(
                Group.BAD_MODEL, Severity.INFO, "mapped_class_absent",
                f"Class index(es) {missing} from the encoding are not present in the data.",
                f"{DATASET_REQ}#classification-target-rules", {"absent": missing}))
        return df, dictionary, findings

    # No desired map: build a contiguous encoding.
    numeric = []
    all_numeric = True
    for t in present:
        try:
            numeric.append(int(t))
        except ValueError:
            all_numeric = False
            break

    if all_numeric:
        ordered = sorted(int(t) for t in present)
        if ordered == list(range(len(ordered))):
            dictionary = {str(i): i for i in ordered}
            df[label_col] = np.array([int(t) for t in tokens], dtype=np.int64)
            return df, dictionary, findings
        remap = {str(old): new for new, old in enumerate(ordered)}
        findings.append(Finding(
            Group.HARD_REJECT, Severity.FIX_REQUIRED, "noncontiguous_labels",
            f"Labels {ordered} are not contiguous from 0; they were re-encoded to 0..{len(ordered)-1}. "
            f"Save the new dictionary and keep it for inference.",
            f"{DATASET_REQ}#classification-target-rules", {"original": ordered}))
        df[label_col] = np.array([remap[t] for t in tokens], dtype=np.int64)
        return df, {k: v for k, v in remap.items()}, findings

    # String labels -> assign sorted order.
    remap = {name: i for i, name in enumerate(present)}
    df[label_col] = np.array([remap[t] for t in tokens], dtype=np.int64)
    findings.append(Finding(
        Group.BAD_MODEL, Severity.INFO, "string_labels_encoded",
        f"Text labels were encoded to integers 0..{len(present)-1}. Saved dictionary: {remap}.",
        f"{DATASET_REQ}#classification-target-rules", {"dictionary": remap}))
    return df, remap, findings
