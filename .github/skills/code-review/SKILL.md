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
