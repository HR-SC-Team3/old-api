---
name: code-review
description: "Repository rules for reviewing pull requests in this repo. Use this whenever reviewing or commenting on a pull request or diff in this codebase."
---

<!-- @format -->

This repository exists to **document the current behavior of the code via tests**. It is not
a place to fix bugs, refactor, or improve the application under test. Review every pull
request against that purpose, and flag violations of the following rules.

## 1. Never change application behavior

The code under test (everything outside `tests/`, `scripts/`, and test tooling) must never be
edited in a way that changes its behavior. Tests exist to capture and pin down what the code
currently does - including quirks and bugs - not to make the code correct.

- Reject any diff that changes logic, fixes a bug, or alters an endpoint's response in the
  application code, even if the change looks like an obvious improvement.
- Formatting-only or comment-only changes to application code that provably do not alter
  behavior are the only acceptable touches to that code.
- If a test fails against current behavior, the fix is to correct the test's expectation to
  match reality, not to change the application so the test passes.

## 2. Use the permission helper, don't edit `data/user.json`

Tests that need a user with specific permissions must go through the permission helper
(`scripts/permission_users.py`, exposed to integration tests via the `user_headers` fixture in
`tests/integration/conftest.py`), which synthesizes users on demand for a given
resource/method/allowed combination.

- Reject any diff that manually adds, edits, or hardcodes entries in `data/user.json` (or
  duplicates its contents elsewhere) to obtain test permissions.
- Look for tests using `user_headers(resource=..., method=..., allowed=...)` rather than
  crafting API keys or user records by hand.

## 3. No data files may ever be edited

Files under `data/` (e.g. `data/user.json`, `data/item.json`, `data/order.json`, etc.) are
fixture/seed data for the application and must never be edited by a pull request, for any
reason - not to add test data, not to fix a typo, not to support a new test case.

- Reject any diff that touches files under `data/`.
- If a test needs data that doesn't exist yet, it should create it at runtime (e.g. via the
  API, or via helpers like `scripts/permission_users.py`) rather than editing the seed files.

## 4. Test function names must be unique within a file

Python silently keeps only the last definition when two functions in the same module share a
name - pytest never warns about this. The earlier test simply never runs, and any coverage
claimed for it (in the PR description or elsewhere) is false without any error to signal it.

- Check the whole file for name collisions, not just neighboring tests. A rename made to fix
  one collision can silently introduce a new one elsewhere in the same file - re-check after
  every rename touching a test name.
- `grep "^def test_" file.py | sort | uniq -d` should print nothing; treat any output as a
  bug in the diff, not a style nit.

## 5. Don't accept a `skip` marker that claims "no user has that permission"

`scripts/permission_users.py`'s `make_user_for_permutation`, wired into the `user_headers`
fixture (rule 2), synthesizes a user for any `(resource, method, allowed)` combination that
doesn't already have a hand-authored match. A test marked
`@pytest.mark.skip(reason="no user has DELETE permission for X")` is citing a limitation that
doesn't exist - `user_headers(resource=..., method=..., allowed=...)` already produces that
user on demand, and the fixture's own docstring documents this fallback.

- Flag any `skip` whose stated reason is "no test user has this permission" and ask for it to
  be replaced with a real assertion (or an `xfail` if the endpoint itself misbehaves).

## 6. Flag dead code left in test files

- Unused imports and unused module-level variables (e.g. a `*_MODEL_SOURCE` constant read
  from disk but never asserted against) should be removed, not left as copy-paste leftovers.
- Commented-out test functions should be finished or deleted, not left commented out.

## Additional things worth flagging

- **Shared-file collisions across concurrent PRs.** If a PR adds a class/model to a shared
  file (e.g. a new `class X` in `tests/integration/schemas.py`) and another currently open PR
  adds the same class, note it as a merge-coordination risk for whichever PR merges second,
  even though it isn't a violation of rules 1-6 in isolation.
