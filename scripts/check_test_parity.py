#!/usr/bin/env python3
"""
Check that every tests/integration/test_<resource>.py file covers the same
set of test "shapes" (a test's function name with the resource's own name
normalized out, e.g. `test_get_supplier_by_id_returns_404` and
`test_get_warehouse_by_id_returns_404` both normalize to
`test_get_RESOURCE_by_id_returns_404`).

This does not hardcode a fixed checklist. Instead it enforces *consistency*
across resource test files: whatever categories of test one resource's file
covers, every other resource's file is expected to cover too. The intent is
to catch a new resource test file (e.g. test_orders.py) that quietly skips a
whole category of checks (auth, schema, pagination, error format, ...) that
every other resource's tests already established as the baseline.

With fewer than two resource test files there is nothing to compare against,
so the check trivially passes.
"""

import ast
import re
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parents[1] / "tests" / "integration"

# Files that aren't a per-resource endpoint test file (test_<resource>.py),
# so they have nothing to be consistent with and are excluded from the
# shape comparison below.
NON_RESOURCE_TEST_FILES = {"test_helpers.py", "test_permission_users.py"}


def resource_name_variants(stem):
    """All singular/plural spellings of a test file's resource name to strip.

    e.g. "test_suppliers" -> {"suppliers", "supplier"}
         "test_inventories" -> {"inventories", "inventory"}
    """
    resource = stem[len("test_") :]
    variants = {resource}
    if resource.endswith("ies"):
        variants.add(resource[:-3] + "y")
    elif resource.endswith("s"):
        variants.add(resource[:-1])
    return sorted(variants, key=len, reverse=True)


def normalize(name, variants):
    normalized = name
    for variant in variants:
        normalized = re.sub(
            rf"(?<![a-z0-9]){re.escape(variant)}(?![a-z0-9])",
            "RESOURCE",
            normalized,
            flags=re.IGNORECASE,
        )
    return normalized


def extract_test_names(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
            "test_"
        ):
            names.add(node.name)
    return names


def main():
    test_files = sorted(
        p for p in TESTS_DIR.glob("test_*.py") if p.name not in NON_RESOURCE_TEST_FILES
    )

    if len(test_files) < 2:
        print(
            f"Only {len(test_files)} resource test file(s) found in "
            f"{TESTS_DIR.relative_to(TESTS_DIR.parents[2])}; nothing to compare yet."
        )
        return 0

    shapes_by_file = {}
    for path in test_files:
        variants = resource_name_variants(path.stem)
        names = extract_test_names(path)
        shapes_by_file[path.name] = {normalize(name, variants) for name in names}

    all_shapes = set()
    for shapes in shapes_by_file.values():
        all_shapes |= shapes

    ok = True
    for filename, shapes in sorted(shapes_by_file.items()):
        missing = sorted(all_shapes - shapes)
        if missing:
            ok = False
            print(f"::error::{filename} is missing {len(missing)} test type(s):")
            for shape in missing:
                # Show which other file(s) actually have this shape, for context.
                present_in = sorted(
                    f for f, s in shapes_by_file.items() if shape in s and f != filename
                )
                print(f"  - {shape}  (present in: {', '.join(present_in)})")

    if ok:
        print(
            f"All {len(test_files)} resource test files cover the same "
            f"{len(all_shapes)} test types."
        )

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
