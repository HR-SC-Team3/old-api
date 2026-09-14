#!/usr/bin/env python3
"""
Create a parent "story" issue plus one sub-issue per API endpoint (from
API_Endpoint_Test_Report.xlsx), add each to a GitHub Projects (v2) board in
the "Todo" column, label them "Sprint 1", and assign the right person.

REQUIRES gh CLI v2.94.0 or later (for --parent support on `gh issue create`).
Check with: gh --version

SETUP (one time):
    gh auth login
    gh auth refresh -s project      # Projects v2 scope

EDIT THE VALUES BELOW, then run:
    pip install openpyxl
    python3 create_github_issues.py
"""

import json
import subprocess
import sys
import tempfile
import os

# ---------------------------------------------------------------------------
# 1. EDIT THESE
# ---------------------------------------------------------------------------
REPO = "HR-SC-Team3/old-api"
PROJECT_OWNER = "HR-SC-Team3"        # org from the project URL
PROJECT_NUMBER = "1"                 # from .../projects/1/views/2
STATUS_COLUMN_NAME = "Todo"          # must match the column name exactly
SPRINT_LABEL = "Sprint 1"
STORY_TITLE = "As a developer I want to know what each endpoint does"
# ---------------------------------------------------------------------------

XLSX_PATH = "API_Endpoint_Test_Report.xlsx"

ASSIGNEES = {
    "Samrina": "SamSam0208",
    "Daniel": "daniel3573",
    "Dimitri": "Foxxite",
    "Yorick": "Y0-r1ck",
}

# Full checklist, matching the type-specific sections of the validation
# checklist document — one set of items per endpoint type.
CHECKS = {
    "Collection GET": [
        "Returns 200 OK with a valid response on a normal request",
        "Response body matches the documented schema (field names, types, nesting)",
        "Pagination works as documented (page, limit/page_size, or cursor params)",
        "Filtering/query params behave as documented (test at least 2 filters)",
        "Sorting params (if documented) return correctly ordered results",
        "Empty result set returns 200 with an empty array, not an error",
        "Invalid query param (e.g. page=-1, unknown filter key) returns a sensible 400 or is ignored gracefully — not a 500",
        "Response time is reasonable (flag anything unusually slow)",
    ],
    "Single-Resource GET": [
        "Valid ID returns 200 with the correct resource",
        "Non-existent ID returns 404 (not 200 with empty body, not 500)",
        "Malformed ID (e.g. string where int expected) returns 400, not 500",
        "Response includes all documented fields, correctly typed",
        "Nested/related objects (if any) are complete and consistent with their own endpoint's data",
    ],
    "POST (Create)": [
        "Valid payload returns 201 Created with the created resource (including generated id)",
        "Response Location header or body correctly points to the new resource",
        "Missing required field(s) returns 400/422 with a clear error message",
        "Invalid field type/value (e.g. string for a number, invalid enum) is rejected, not silently coerced",
        "Duplicate/unique-constraint violations are handled (e.g. duplicate SKU) with a proper 409/400, not a 500",
        "Extra/unexpected fields in payload are ignored or rejected consistently (check documented behavior)",
        "Created resource is immediately retrievable via GET",
        "Foreign key references (e.g. warehouse_id on a location) are validated — invalid reference is rejected",
    ],
    "PUT (Update)": [
        "Valid full payload updates the resource and returns 200",
        "Non-existent ID returns 404",
        "Partial payload behavior matches documentation (full replace vs. partial merge — confirm which one this API does)",
        "Invalid field values are rejected the same way as on POST",
        "Updating a field with a foreign key validates the reference exists",
        "Update is actually persisted (re-GET confirms the change)",
        "Concurrent/conflicting updates don't silently corrupt data (if testable)",
    ],
    "DELETE": [
        "Valid ID deletes and returns 200/204",
        "Non-existent ID returns 404",
        "Resource is actually gone afterward (GET returns 404)",
        "Deleting a resource referenced elsewhere is handled deliberately — either blocked with a clear error, or cascades as documented. Flag if it just breaks the referencing resource silently.",
        "Repeated DELETE on the same ID returns 404, not a 500",
    ],
    "Nested Relationship GET": [
        "Returns only items belonging to the correct parent",
        "Non-existent parent ID returns 404",
        "Empty relationship returns 200 with empty array",
        "Pagination/filtering (if supported) behaves the same as regular collection GETs",
    ],
    "Nested PUT-Action": [
        "Valid payload performs the expected action and returns the correct status",
        "Business rules are enforced (e.g. commit on a transfer actually moves stock and updates inventory counts correctly)",
        "Action is idempotent or clearly documented if not (what happens if called twice?)",
        "Invalid state transitions are rejected (e.g. committing an already-committed transfer, shipping an order with no items)",
        "Referenced sub-resources (items, orders) must exist and belong to the correct parent — cross-parent references should be rejected",
        "Side effects on related resources are verified (e.g. does committing a transfer update inventories and items/{id}/inventory correctly?)",
    ],
}

CROSS_CUTTING = [
    "Auth: request without credentials is rejected (401); request with insufficient permissions is rejected (403), if roles apply",
    "Content-Type: correct Content-Type is required/enforced on request and response",
    "Error format: error responses follow a consistent schema across the whole API (not different shapes per endpoint)",
    "Consistency with spec: response actually matches what's declared in the OpenAPI file (status codes, required fields, examples)",
    "No sensitive data leakage: internal IDs, stack traces, or debug info aren't exposed in error responses",
]


def run(cmd):
    print("  $", " ".join(cmd))
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def run_json(cmd):
    return json.loads(run(cmd).stdout)


def load_endpoints():
    import openpyxl

    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    ov = wb["Overview"]
    endpoints = []
    for row in ov.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        endpoints.append(
            {"num": row[0], "person": row[1], "method": row[2], "path": row[3], "type": row[4]}
        )
    return endpoints


def build_body(ep):
    type_checks = CHECKS.get(ep["type"], [])

    lines = [
        f"**Endpoint:** `{ep['method']} {ep['path']}`",
        f"**Type:** {ep['type']}",
        "",
        "### Checklist",
        "",
    ]
    for item in type_checks:
        lines.append(f"- [ ] {item}")

    lines += [
        "",
        "### Cross-cutting checks",
        "",
    ]
    for item in CROSS_CUTTING:
        lines.append(f"- [ ] {item}")

    lines += [
        "",
        "### Notes for API redesign",
        "",
        "The goal isn't just pass/fail — we're documenting how this endpoint actually "
        "behaves so we can design a better version. When you test, record:",
        "",
        "- **Actual behavior observed** (even if it technically passes, note anything surprising)",
        "- **Inconsistencies vs. other endpoints** (different error shapes, status codes, naming, etc.)",
        "- **Redesign suggestions** (what should this endpoint look like instead?)",
        "",
        "### How to report findings",
        "",
        "For any failed item, comment on this issue with:",
        "1. Which checklist item failed",
        "2. Actual vs. expected behavior",
        "3. Severity (blocker / major / minor / cosmetic)",
        "",
        f"_Sub-issue of: {STORY_TITLE}_",
    ]
    return "\n".join(lines)


def ensure_label():
    try:
        run(["gh", "label", "create", SPRINT_LABEL, "--repo", REPO, "--color", "0E8A16", "--force"])
    except subprocess.CalledProcessError as e:
        print(f"  ! Could not create label '{SPRINT_LABEL}': {e.stderr.strip()}")


def get_project_and_status_ids():
    """Look up the project's node id, the Status field id, and the Todo option id."""
    project = run_json(
        ["gh", "project", "view", PROJECT_NUMBER, "--owner", PROJECT_OWNER, "--format", "json"]
    )
    project_id = project["id"]

    fields = run_json(
        ["gh", "project", "field-list", PROJECT_NUMBER, "--owner", PROJECT_OWNER, "--format", "json"]
    )["fields"]

    status_field = next((f for f in fields if f["name"].lower() == "status"), None)
    if not status_field:
        sys.exit("Could not find a 'Status' field on this project board.")

    todo_option = next(
        (o for o in status_field.get("options", []) if o["name"].lower() == STATUS_COLUMN_NAME.lower()),
        None,
    )
    if not todo_option:
        sys.exit(
            f"Could not find a '{STATUS_COLUMN_NAME}' column in the Status field. "
            f"Available: {[o['name'] for o in status_field.get('options', [])]}"
        )

    return project_id, status_field["id"], todo_option["id"]


def add_to_project_and_set_status(issue_url, project_id, status_field_id, todo_option_id):
    item = run_json(
        [
            "gh", "project", "item-add", PROJECT_NUMBER,
            "--owner", PROJECT_OWNER, "--url", issue_url, "--format", "json",
        ]
    )
    item_id = item["id"]
    run(
        [
            "gh", "project", "item-edit",
            "--project-id", project_id,
            "--id", item_id,
            "--field-id", status_field_id,
            "--single-select-option-id", todo_option_id,
        ]
    )


def create_issue(title, body, labels=None, assignee=None, parent=None):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(body)
        body_file = f.name
    try:
        cmd = ["gh", "issue", "create", "--repo", REPO, "--title", title, "--body-file", body_file]
        if labels:
            cmd += ["--label", ",".join(labels)]
        if assignee:
            cmd += ["--assignee", assignee]
        if parent:
            cmd += ["--parent", str(parent)]
        result = run(cmd)
        return result.stdout.strip().splitlines()[-1]  # issue URL
    finally:
        os.unlink(body_file)


def main():
    endpoints = load_endpoints()
    print(f"Loaded {len(endpoints)} endpoints.\n")

    ensure_label()
    project_id, status_field_id, todo_option_id = get_project_and_status_ids()

    print(f"\nCreating parent story issue: {STORY_TITLE}")
    story_body = (
        "Parent tracking issue for endpoint testing across the API.\n\n"
        "Each sub-issue below covers one endpoint's test checklist."
    )
    story_url = create_issue(STORY_TITLE, story_body, labels=[SPRINT_LABEL])
    story_number = story_url.rstrip("/").split("/")[-1]
    print(f"  -> {story_url}")
    add_to_project_and_set_status(story_url, project_id, status_field_id, todo_option_id)

    created = []
    for ep in endpoints:
        title = f"Test endpoint {ep['method']} {ep['path']}"
        body = build_body(ep)
        assignee = ASSIGNEES.get(ep["person"])
        if not assignee:
            print(f"  ! No GitHub username mapped for '{ep['person']}' — issue will be unassigned")

        print(f"Creating issue #{ep['num']}: {title}")
        try:
            issue_url = create_issue(
                title, body, labels=[SPRINT_LABEL], assignee=assignee, parent=story_number
            )
            print(f"  -> {issue_url}")
            add_to_project_and_set_status(issue_url, project_id, status_field_id, todo_option_id)
            created.append({"num": ep["num"], "url": issue_url})
        except subprocess.CalledProcessError as e:
            print(f"  ! FAILED: {e.stderr.strip()}", file=sys.stderr)

    print(f"\nDone. Created {len(created)}/{len(endpoints)} endpoint issues under {story_url}")
    with open("created_issues.json", "w") as f:
        json.dump({"story": story_url, "issues": created}, f, indent=2)
    print("Saved mapping to created_issues.json")


if __name__ == "__main__":
    main()
