<!-- @format -->

# Contributing

Thanks for your interest in contributing! This document explains the conventions this
repository expects, and why they exist, so your pull request passes CI and review on
the first try.

## Table of contents

- [Before you start](#before-you-start)
- [Repository purpose & rules](#repository-purpose--rules)
- [Branch naming](#branch-naming)
- [Commit messages](#commit-messages)
- [Pull requests](#pull-requests)
- [Automated checks (CI)](#automated-checks-ci)
- [Tests](#tests)
- [Code review & merging](#code-review--merging)

## Before you start

1. Fork or branch from `main`.
2. Install test dependencies:

    ```bash
    pip install -r requirements-test.txt
    ```

3. Make your changes, add or update tests, and run the test suite locally before
   opening a pull request (see [Tests](#tests)).

## Repository purpose & rules

The goal of this repository is to **document the current behavior of the code via
tests**. It is not a place to fix bugs, refactor, or improve the application under
test. Keep this in mind for every PR:

1. **Never change application behavior.** Code outside `tests/`, `scripts/`, and test
   tooling must never be edited in a way that changes what it does - that includes
   fixing bugs and other "obvious improvements". Tests exist to pin down current
   behavior, quirks and bugs included. If a test fails against current behavior, fix
   the test's expectation, not the application. Formatting/comment-only changes that
   provably don't alter behavior are the only acceptable touches to application code.
2. **Use the permission helper, don't edit `data/user.json`.** Tests that need a user
   with specific permissions must go through `scripts/permission_users.py` (exposed to
   integration tests via the `user_headers` fixture in `tests/integration/conftest.py`),
   which synthesizes users on demand for a given resource/method/allowed combination.
   Never hand-edit or duplicate `data/user.json` to obtain test permissions.
3. **No data files may ever be edited.** Files under `data/` (e.g. `data/user.json`,
   `data/item.json`, `data/order.json`, etc.) are fixture/seed data and must never be
   edited by a pull request, for any reason. If a test needs data that doesn't exist
   yet, create it at runtime (via the API or helpers like `permission_users.py`)
   instead of editing the seed files.

These rules are also encoded in [`AGENTS.md`](AGENTS.md) (general coding-agent
instructions), for GitHub Copilot code review in
[`.github/skills/code-review/SKILL.md`](.github/skills/code-review/SKILL.md), and as a
Claude Code project skill in
[`.claude/skills/code-review/SKILL.md`](.claude/skills/code-review/SKILL.md).

## Branch naming

Branches must follow the `<type>/<short-description>` pattern, enforced automatically
by CI:

```
feat/add-login-page
fix/null-pointer-auth
docs/update-readme
```

- Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `tests`,
  `build`, `ci`, `chore`, `revert`, `dev`.
- The description may only contain lowercase letters, numbers, dots, underscores, and
  hyphens (`a-z0-9._-`).

## Commit messages

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<optional scope>): <short description>
```

Examples:

```
feat: add login page
fix(auth): null pointer on expired token
docs: update README installation instructions
```

| Type             | Use for                                                     |
| ---------------- | ----------------------------------------------------------- |
| `feat`           | A new feature                                               |
| `fix`            | A bug fix                                                   |
| `docs`           | Documentation-only changes                                  |
| `style`          | Formatting only, no functional change (e.g. whitespace)     |
| `refactor`       | Code restructuring without changing behavior                |
| `perf`           | A performance improvement                                   |
| `test` / `tests` | Adding or updating tests                                    |
| `build`          | Changes to the build system or dependencies                 |
| `ci`             | Changes to CI/CD configuration (e.g. workflows themselves)  |
| `chore`          | Maintenance tasks with no impact on `src` or tests          |
| `revert`         | Reverting a previous commit                                 |
| `dev`            | Development-related changes that don't fit another category |

- Keep the description concise and written in the imperative mood ("add", not
  "added"/"adds").
- Do not end the subject line with a period.

## Pull requests

- **The PR title must also follow Conventional Commits** - it is validated
  automatically and the same rules as commit messages apply.
- The title must not end with a period.
- `WIP` PR titles are allowed, but signal the PR isn't ready to merge yet.
- Keep pull requests focused: one logical change per PR.
- Describe _why_ the change is needed, not just what changed.

## Automated checks (CI)

Every push and pull request triggers the following GitHub Actions workflows. All of
them must pass before a PR can be merged.

| Workflow                   | Trigger                                          | What it checks                                                                        |
| -------------------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------- |
| `pr-conventions.yml`       | PR opened / edited / synchronized                | PR title follows Conventional Commits, and branch name follows `<type>/<description>` |
| `pr-require-approvals.yml` | Review submitted / PR events                     | At least 2 approving reviews before merge                                             |
| `scan-secrets.yml`         | Push to `main` / every PR                        | TruffleHog scans for verified/leaked secrets (API keys, tokens, passwords)            |
| `tests.yml`                | Push to `main` / every PR                        | Installs dependencies and runs the full `pytest` suite                                |
| `test-parity.yml`          | Changes to test files or the parity check script | Every resource has the same categories of tests (no missing coverage)                 |

If a check fails, fix the underlying issue and push again - do not bypass checks.

If TruffleHog flags a secret, removing it from the current diff is not enough: rotate
(invalidate) the credential, since it may already be reachable from git history.

## Tests

Run the full test suite locally before opening a PR:

```bash
python -m pytest
```

If you add a new resource, make sure its test file covers the same test categories as
existing resources - see `scripts/check_test_parity.py`.

## Code review & merging

- A pull request needs **at least 2 approving reviews** before it can be merged.
  Only the latest review per reviewer counts; dismissed reviews do not.
- Address review feedback with additional commits rather than force-pushing, unless
  asked to clean up history before merge.
- Once approved and all checks are green, the PR can be merged.

---

**Quick checklist before opening a PR:**

- [ ] No application behavior was changed (tests-only, or provably behavior-preserving)
- [ ] No files under `data/` were edited
- [ ] Test users were created via `permission_users.py` / `user_headers`, not by hand
- [ ] Branch name follows `<type>/<description>`
- [ ] Commits (and PR title) follow Conventional Commits
- [ ] Tests added/updated and passing locally
- [ ] No secrets committed
- [ ] PR description explains the _why_
