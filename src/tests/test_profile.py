"""DatasetProfile loader: the signal_processing field, and schema<->loader parity.

Parity guards the trap that this task's own change lives inside: the schema declares
`additionalProperties: false` while the loader silently ignores unknown keys, so a field added to one
side and not the other is undetectable and there was no test. The loader key set is derived from
`profile.from_dict`'s source by AST (not a hardcoded list, which would only test itself), so:
  - deleting a property from the schema  -> a loader key with no property -> FAIL
  - adding a `raw.get("x")` to the loader -> a loader key with no property -> FAIL
Both directions are live; that is `databuilder-012` acceptance 9.
"""
import ast
import json
import os
import unittest

import _helpers as H  # noqa: F401  (puts src on path)

from data_builder.profile import DatasetProfile, ProfileError

REPO = os.path.dirname(H.SRC)
SCHEMA = os.path.join(REPO, "data/skill-presets/dataset-profile.schema.json")
DEMO = os.path.join(REPO, "data/skill-presets/nordic-gesture-demo.json")
PROFILE_PY = os.path.join(H.SRC, "data_builder/profile.py")

# Keys the schema carries that from_dict does not (yet) read. A NEW schema-only key must fail the
# parity test, so this exception list is explicit and closed.
KNOWN_SCHEMA_ONLY = {"$comment", "accel_full_scale_g", "gyro_full_scale_dps"}


def _loader_keys():
    """Every key from_dict reads off `raw`, extracted by AST from the live source.

    Catches all four idioms so a future author cannot slip a key past parity: raw["k"], raw.get("k"),
    raw.pop("k"), and "k" in raw.
    """
    with open(PROFILE_PY, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "from_dict")
    keys = set()

    def _is_raw(node):
        return isinstance(node, ast.Name) and node.id == "raw"

    for node in ast.walk(fn):
        # raw["k"]
        if isinstance(node, ast.Subscript) and _is_raw(node.value) \
                and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            keys.add(node.slice.value)
        # raw.get("k") / raw.pop("k")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr in ("get", "pop") and _is_raw(node.func.value) \
                and node.args and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            keys.add(node.args[0].value)
        # "k" in raw
        if isinstance(node, ast.Compare) and _is_raw(node.comparators[0]) \
                and any(isinstance(op, ast.In) for op in node.ops) \
                and isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
            keys.add(node.left.value)
    return keys


class TestSchemaLoaderParity(unittest.TestCase):
    def setUp(self):
        with open(SCHEMA, encoding="utf-8") as fh:
            self.schema_props = set(json.load(fh)["properties"])
        self.loader_keys = _loader_keys()

    def test_every_loader_key_is_a_schema_property(self):
        missing = self.loader_keys - self.schema_props
        self.assertEqual(missing, set(),
                         f"loader reads keys the schema does not declare: {sorted(missing)}")

    def test_schema_only_keys_are_the_known_set(self):
        schema_only = self.schema_props - self.loader_keys
        self.assertEqual(schema_only, KNOWN_SCHEMA_ONLY,
                         f"schema-only keys changed: {sorted(schema_only)} (update KNOWN_SCHEMA_ONLY "
                         "only for a deliberate, documented addition)")

    def test_extractor_catches_all_read_idioms(self):
        # Guards the guard: the AST walker must see the real loader keys, so a future author using a
        # different idiom cannot pass parity invisibly.
        for k in ("dataset_name", "signal_processing", "target_technology", "window"):
            self.assertIn(k, self.loader_keys)

    def test_worked_example_loads_and_keys_are_schema_properties(self):
        with open(DEMO, encoding="utf-8") as fh:
            raw = json.load(fh)
        DatasetProfile.from_dict(raw)  # must not raise
        for k in raw:
            self.assertIn(k, self.schema_props, f"demo key {k!r} is not a schema property")


class TestSignalProcessingField(unittest.TestCase):
    def _load(self, value=H, **over):
        raw = {**H.BASE_PROFILE, **over}
        if value is not H:
            raw["signal_processing"] = value
        return DatasetProfile.from_dict(raw)

    def test_true_false_absent(self):
        self.assertIs(self._load(value=True).signal_processing, True)
        self.assertIs(self._load(value=False).signal_processing, False)
        self.assertIsNone(self._load().signal_processing)          # absent
        self.assertIsNone(self._load(value=None).signal_processing)  # explicit null

    def test_non_bool_rejected(self):
        for bad in (1, 0, "true", "false", "yes", 1.0):
            with self.assertRaises(ProfileError):
                self._load(value=bad)


if __name__ == "__main__":
    unittest.main()
