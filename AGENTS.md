<!-- @format -->

# Agent instructions

These rules apply to any coding agent (AI or human-assisted) working in this repository -
whether writing code, reviewing a pull request, or editing a diff.

## Purpose of this repository

The goal of this repository is to **document the current behavior of the code via tests**.
It is not a place to fix bugs, refactor, or improve the application under test. Judge every
change against that purpose, and refuse or flag violations of the following rules.

## Rules

### 1. Never change application behavior

The code under test (everything outside `tests/`, `scripts/`, and test tooling) must never be
edited in a way that changes its behavior. Tests exist to capture and pin down what the code
currently does - including quirks and bugs - not to make the code correct.

- Do not alter logic, fix a bug, or change an endpoint's response in the application code,
  even if the change looks like an obvious improvement.
- Formatting-only or comment-only changes to application code that provably do not alter
  behavior are the only acceptable touches to that code.
- If a test fails against current behavior, fix the test's expectation to match reality -
  never change the application so the test passes.

### 2. Use the permission helper, don't edit `data/user.json`

Tests that need a user with specific permissions must go through the permission helper
(`scripts/permission_users.py`, exposed to integration tests via the `user_headers` fixture in
`tests/integration/conftest.py`), which synthesizes users on demand for a given
resource/method/allowed combination.

- Never manually add, edit, or hardcode entries in `data/user.json` (or duplicate its
  contents elsewhere) to obtain test permissions.
- Use `user_headers(resource=..., method=..., allowed=...)` rather than crafting API keys or
  user records by hand.

### 3. No data files may ever be edited

Files under `data/` (e.g. `data/user.json`, `data/item.json`, `data/order.json`, etc.) are
fixture/seed data for the application and must never be edited, for any reason - not to add
test data, not to fix a typo, not to support a new test case.

- Never touch files under `data/`.
- If a test needs data that doesn't exist yet, create it at runtime (e.g. via the API, or via
  helpers like `scripts/permission_users.py`) rather than editing the seed files.

### 4. Test function names must be unique within a file

Python silently keeps only the last definition when two functions in the same module share a
name - pytest never warns about this. The earlier test simply never runs again, and its
coverage claim (in the PR description or elsewhere) becomes false with no error to signal it.

- When adding or renaming a test, check the whole file for name collisions, not just
  neighboring tests - fixing one collision by renaming can silently create a new one
  elsewhere in the same file.
- A quick sanity check before pushing: `grep "^def test_" file.py | sort | uniq -d` should be
  empty.

### 5. Don't skip a test because "no user has that permission" - generate one

`scripts/permission_users.py`'s `make_user_for_permutation`, wired into the `user_headers`
fixture (see rule 2), synthesizes a user for any `(resource, method, allowed)` combination
that doesn't already have a hand-authored match. A test marked
`@pytest.mark.skip(reason="no user has DELETE permission for X")` is treating a
non-limitation as a blocker - `user_headers(resource=..., method=..., allowed=...)` already
produces that user on demand. Prefer running the test (or `xfail`ing it if the endpoint
itself misbehaves) over skipping it for a permission reason.

### 6. Remove dead code before merging

Test files documenting current behavior should still be maintainable:

- Remove unused imports and unused module-level variables (e.g. a `*_MODEL_SOURCE` constant
  that's read from disk but never asserted against).
- Remove commented-out test functions rather than leaving them in the file - finish them or
  delete them.

### 7. Pydantic response models belong in `schemas.py`

`tests/integration/schemas.py` is the single shared location for the Pydantic models used to
validate API responses (e.g. `Transfer`, `Client`, `Item`, `ItemType`).

- Do not define a new `BaseModel` subclass inline inside a `test_*.py` file - add it to
  `schemas.py` and `from schemas import Whatever` instead.
- Before adding a class, check `schemas.py` doesn't already define one for that resource
  (including one added by another currently-open PR - see the merge-coordination note below).

## Where else these rules live

- [`CONTRIBUTING.md`](CONTRIBUTING.md) - human contributor guide.
- [`.github/skills/code-review/SKILL.md`](.github/skills/code-review/SKILL.md) - GitHub
  Copilot code review agent skill.

Keep all four in sync if these rules ever change.
