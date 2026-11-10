"""Import the SDD backlog into GitHub labels, milestones and issues (T-003).

Parses the tables in ``specs/taskflow/tasks.md`` and creates the missing items
idempotently. Requires a token with ``repo`` permissions in ``GITHUB_TOKEN``.

Example:
    GITHUB_TOKEN=... python scripts/import_github_backlog.py \
        --repo Chorexxs/taskflow-api --dry-run
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

LABELS = {
    "s0": ("B60205", "Crítico"),
    "s1": ("D93F0B", "Alto"),
    "security": ("0E8A16", "Seguridad"),
    "frontend": ("1D76DB", "Frontend"),
    "db": ("5319E7", "Base de datos"),
    "docs": ("FBCA04", "Documentación"),
}

PHASE_RE = re.compile(r"^##\s+(P\d)\s*[—:-]\s*(.+?)\s*$")
TASK_RE = re.compile(r"^\|\s*(T-\d{3})\s*\|")


@dataclass
class Task:
    task_id: str
    title: str
    priority: str
    deps: str
    size: str
    refs: str
    acceptance: str
    phase: str
    phase_title: str


def parse_tasks(path: str) -> list[Task]:
    tasks: list[Task] = []
    phase = ""
    phase_title = ""
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            phase_match = PHASE_RE.match(line)
            if phase_match:
                phase = phase_match.group(1)
                phase_title = f"{phase} — {phase_match.group(2)}"
                continue
            if not TASK_RE.match(line):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 7:
                continue
            tasks.append(
                Task(
                    task_id=cells[0],
                    title=cells[1],
                    priority=cells[2],
                    deps=cells[3],
                    size=cells[4],
                    refs=cells[5],
                    acceptance=cells[6],
                    phase=phase,
                    phase_title=phase_title,
                )
            )
    return tasks


def labels_for(task: Task) -> list[str]:
    labels: list[str] = []
    if task.priority.upper().startswith("S0"):
        labels.append("s0")
    if task.priority.upper().startswith("S1"):
        labels.append("s1")
    haystack = f"{task.title} {task.refs} {task.acceptance}".lower()
    if any(
        word in haystack
        for word in ("nfr-sec", "sec-", "security", "auth", "cors", "token", "upload", "secret")
    ):
        labels.append("security")
    if any(
        word in haystack
        for word in (
            "frontend",
            "react",
            "vitest",
            " a11y",
            "accesibilidad",
            "ui ",
            "responsive",
            "tema",
        )
    ):
        labels.append("frontend")
    if any(
        word in haystack
        for word in ("migr", " db", "schema", "índice", "constraint", "slug", "storage")
    ):
        labels.append("db")
    if any(
        word in haystack
        for word in ("docs", "documentación", "readme", "adr", "runbook", "release")
    ):
        labels.append("docs")
    return list(dict.fromkeys(labels))


def issue_body(task: Task) -> str:
    return "\n".join(
        [
            f"**Fase:** {task.phase_title or task.phase}",
            f"**Tarea:** {task.title}",
            f"**Prioridad:** {task.priority}",
            f"**Dependencias:** {task.deps}",
            f"**Tamaño:** {task.size}",
            f"**Refs:** {task.refs}",
            f"**Aceptación:** {task.acceptance}",
            "",
            "Fuente: `specs/taskflow/tasks.md` (SDD).",
        ]
    )


def request(client: httpx.Client, method: str, path: str, **kwargs):
    response = client.request(method, path, **kwargs)
    if response.status_code >= 400:
        print(
            f"ERROR {method} {path} -> {response.status_code}: {response.text[:300]}",
            file=sys.stderr,
        )
        response.raise_for_status()
    return response


def list_paginated(client: httpx.Client, path: str, params: dict) -> list[dict]:
    items: list[dict] = []
    page = 1
    while True:
        response = request(client, "GET", path, params={**params, "per_page": 100, "page": page})
        batch = response.json()
        if not batch:
            break
        items.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="Import TaskFlow backlog into GitHub")
    parser.add_argument("--repo", default="Chorexxs/taskflow-api")
    parser.add_argument("--tasks", default="specs/taskflow/tasks.md")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 2

    tasks = parse_tasks(args.tasks)
    if not tasks:
        print("No tasks found", file=sys.stderr)
        return 2

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "taskflow-backlog-import",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    base = f"/repos/{args.repo}"

    with httpx.Client(base_url="https://api.github.com", headers=headers, timeout=60) as client:
        existing_labels = {label["name"] for label in list_paginated(client, f"{base}/labels", {})}
        for name, (color, description) in LABELS.items():
            if name in existing_labels:
                continue
            print(f"label {name}")
            if not args.dry_run:
                request(
                    client,
                    "POST",
                    f"{base}/labels",
                    json={"name": name, "color": color, "description": description},
                )

        existing_milestones = {
            milestone["title"]: milestone["number"]
            for milestone in list_paginated(client, f"{base}/milestones", {"state": "all"})
        }
        milestones: dict[str, int] = dict(existing_milestones)
        phase_titles = {task.phase_title for task in tasks if task.phase_title}
        for title in sorted(phase_titles):
            if title in milestones:
                continue
            print(f"milestone {title}")
            if not args.dry_run:
                response = request(
                    client,
                    "POST",
                    f"{base}/milestones",
                    json={"title": title, "state": "open"},
                )
                milestones[title] = response.json()["number"]

        existing_issues = {
            issue["title"].split(":", 1)[0]
            for issue in list_paginated(client, f"{base}/issues", {"state": "all"})
            if issue["title"].startswith("T-")
        }
        created = skipped = 0
        for task in tasks:
            if task.task_id in existing_issues:
                skipped += 1
                continue
            payload = {
                "title": f"{task.task_id}: {task.title}",
                "body": issue_body(task),
                "labels": labels_for(task),
            }
            if task.phase_title in milestones:
                payload["milestone"] = milestones[task.phase_title]
            print(f"issue {task.task_id}: {task.title}")
            if not args.dry_run:
                request(client, "POST", f"{base}/issues", json=payload)
            created += 1

    print(f"\n{created} issues created, {skipped} already present, {len(tasks)} tasks parsed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
