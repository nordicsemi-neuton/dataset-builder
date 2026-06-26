"""Every rule_ref anchor emitted by the package must resolve to a heading in the referenced wiki file.

This guards against anchor drift (the impl gate found 24 broken anchors). It statically scans the
source for `{CONST}#anchor` and "wiki/...#anchor" literals and checks each against the GitHub-style
heading slugs of the target file.
"""
import glob
import os
import re
import unittest

import _helpers as H  # noqa: F401  (puts src on path / anchors repo root)

REPO = os.path.dirname(H.SRC)  # H.SRC is .../<repo>/src -> repo root is its parent


def gh_slug(heading: str) -> str:
    s = re.sub(r"[^\w\s-]", "", heading.strip().lower())
    return s.replace(" ", "-")


def headings_of(path: str) -> set:
    out = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"^#{1,6}\s+(.*)", line.rstrip())
            if m:
                out.add(gh_slug(m.group(1)))
    return out


def collect_refs():
    const_re = re.compile(r'^([A-Z_]+)\s*=\s*"(wiki/[^"]+\.md)"', re.M)
    refs = []
    for f in glob.glob(os.path.join(REPO, "src/data_builder/*.py")):
        with open(f, encoding="utf-8") as fh:
            src = fh.read()
        consts = dict(const_re.findall(src))
        for cname, anchor in re.findall(r"\{([A-Z_]+)\}#([A-Za-z0-9_-]+)", src):
            if cname in consts:
                refs.append((os.path.basename(f), consts[cname], anchor))
        for path, anchor in re.findall(r'"(wiki/[^"#]+\.md)#([A-Za-z0-9_-]+)"', src):
            refs.append((os.path.basename(f), path, anchor))
    return refs


class TestRuleRefs(unittest.TestCase):
    def test_all_anchors_resolve(self):
        refs = collect_refs()
        self.assertGreater(len(refs), 20, "expected to find many rule_ref anchors")
        cache = {}
        broken = []
        for src_file, wiki_path, anchor in refs:
            full = os.path.join(REPO, wiki_path)
            if wiki_path not in cache:
                cache[wiki_path] = headings_of(full) if os.path.exists(full) else None
            hs = cache[wiki_path]
            if hs is None or anchor not in hs:
                broken.append(f"{src_file}: {wiki_path}#{anchor}")
        self.assertEqual(broken, [], "broken rule_ref anchors:\n" + "\n".join(broken))


if __name__ == "__main__":
    unittest.main()
