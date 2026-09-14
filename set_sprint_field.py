#!/usr/bin/env python3
"""
Set the Sprint (iteration) field to "Sprint 1" on issues that were already
created and added to the project board — no new issues are created.

Reads created_issues.json (produced by create_github_issues.py) to get the
list of issue URLs, including the parent story.

EDIT THE VALUES BELOW to match your board, then run:
    python3 set_sprint_field.py
"""

import json
import subprocess
import sys

# ---------------------------------------------------------------------------
PROJECT_OWNER = "HR-SC-Team3"
PROJECT_NUMBER = "1"
SPRINT_FIELD_NAME = "Sprint"
SPRINT_ITERATION_NAME = "Sprint 1"
CREATED_ISSUES_FILE = "created_issues.json"
# ---------------------------------------------------------------------------


def run(cmd):
    print("  $", " ".join(cmd))
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def run_json(cmd):
    return json.loads(run(cmd).stdout)


def get_field_and_iteration_id(project_id):
    """gh project field-list does not return iteration IDs for Iteration-type
    fields (a known gh CLI limitation: cli/cli#10301, #11068), so query the
    GraphQL API directly instead."""
    query = """
    query($projectId: ID!, $fieldName: String!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          field(name: $fieldName) {
            ... on ProjectV2IterationField {
              id
              name
              configuration {
                iterations { id title startDate duration }
                completedIterations { id title startDate duration }
              }
            }
          }
        }
      }
    }
    """
    result = run_json(
        [
            "gh", "api", "graphql",
            "-f", f"query={query}",
            "-f", f"projectId={project_id}",
            "-f", f"fieldName={SPRINT_FIELD_NAME}",
        ]
    )
    field = result.get("data", {}).get("node", {}).get("field")
    if not field:
        sys.exit(f"No '{SPRINT_FIELD_NAME}' iteration field found on this project.")

    config = field.get("configuration", {})
    all_iterations = config.get("iterations", []) + config.get("completedIterations", [])
    iteration = next(
        (it for it in all_iterations if it.get("title", "").lower() == SPRINT_ITERATION_NAME.lower()),
        None,
    )
    if not iteration:
        sys.exit(
            f"No iteration called '{SPRINT_ITERATION_NAME}' found. "
            f"Available: {[it.get('title') for it in all_iterations]}"
        )
    return field["id"], iteration["id"]


def get_project_id():
    return run_json(
        ["gh", "project", "view", PROJECT_NUMBER, "--owner", PROJECT_OWNER, "--format", "json"]
    )["id"]


def list_project_items():
    """Fetch all items on the board, paginated, mapping issue URL -> item id."""
    items = []
    page = 1
    while True:
        result = run_json(
            [
                "gh", "project", "item-list", PROJECT_NUMBER,
                "--owner", PROJECT_OWNER, "--format", "json", "--limit", "200",
            ]
        )
        items = result.get("items", [])
        break  # gh project item-list already returns everything up to --limit
    url_to_id = {}
    for item in items:
        content = item.get("content", {})
        url = content.get("url")
        if url:
            url_to_id[url] = item["id"]
    return url_to_id


def main():
    with open(CREATED_ISSUES_FILE) as f:
        data = json.load(f)

    urls = [data["story"]] + [i["url"] for i in data["issues"]]
    print(f"Loaded {len(urls)} issue URLs (including story) from {CREATED_ISSUES_FILE}\n")

    project_id = get_project_id()
    sprint_field_id, sprint_iteration_id = get_field_and_iteration_id(project_id)

    print("Fetching current project items...")
    url_to_item_id = list_project_items()

    updated, missing = 0, []
    for url in urls:
        item_id = url_to_item_id.get(url)
        if not item_id:
            missing.append(url)
            continue
        try:
            run(
                [
                    "gh", "project", "item-edit",
                    "--project-id", project_id,
                    "--id", item_id,
                    "--field-id", sprint_field_id,
                    "--iteration-id", sprint_iteration_id,
                ]
            )
            updated += 1
        except subprocess.CalledProcessError as e:
            print(f"  ! FAILED for {url}: {e.stderr.strip()}", file=sys.stderr)

    print(f"\nUpdated {updated}/{len(urls)} items to '{SPRINT_ITERATION_NAME}'.")
    if missing:
        print(f"{len(missing)} URLs were not found on the board (not added yet?):")
        for u in missing:
            print(" -", u)


if __name__ == "__main__":
    main()
