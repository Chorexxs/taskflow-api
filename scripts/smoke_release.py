"""Release smoke test (T-080).

Runs the 13 post-deploy checks against a live API and exits non-zero on the
first failure. It creates a disposable team/project/task/comment/attachment with
a unique suffix, so it is safe against production but leaves test data behind.

Example:
    python scripts/smoke_release.py --base-url https://taskflow-api-gkgl.onrender.com
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence

import httpx


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TaskFlow release smoke test")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=60.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    base = args.base_url.rstrip("/")
    suffix = str(int(time.time()))
    email = f"smoke+{suffix}@example.com"
    password = "SmokeTest123!"
    team_slug = f"smoke-team-{suffix}"
    project_name = f"Smoke Project {suffix}"
    task_title = f"Smoke Task {suffix}"
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'}  {name}{f': {detail}' if detail else ''}")

    with httpx.Client(base_url=base, timeout=args.timeout) as client:
        health = client.get("/health")
        check("health", health.status_code == 200, str(health.status_code))

        live = client.get("/health/live")
        check("health/live", live.status_code == 200, str(live.status_code))

        ready = client.get("/health/ready")
        check("health/ready", ready.status_code == 200, str(ready.status_code))

        register = client.post("/api/v1/auth/register", json={"email": email, "password": password})
        check("register", register.status_code == 201, str(register.status_code))
        check(
            "rate-limit headers",
            "X-RateLimit-Limit" in register.headers,
            register.headers.get("X-RateLimit-Limit", "missing"),
        )

        login = client.post("/api/v1/auth/login", data={"username": email, "password": password})
        check("login", login.status_code == 200, str(login.status_code))
        token = login.json().get("access_token", "") if login.status_code == 200 else ""
        headers = {"Authorization": f"Bearer {token}"}

        team = client.post(
            "/api/v1/teams/",
            json={"name": f"Smoke Team {suffix}", "slug": team_slug},
            headers=headers,
        )
        check("create team", team.status_code == 201, str(team.status_code))

        project = client.post(
            f"/api/v1/teams/{team_slug}/projects/",
            json={"name": project_name},
            headers=headers,
        )
        check("create project", project.status_code == 201, str(project.status_code))

        project_path = f"/api/v1/teams/{team_slug}/projects/{project_name}"
        task = client.post(f"{project_path}/tasks/", json={"title": task_title}, headers=headers)
        check("create task", task.status_code == 201, str(task.status_code))

        comment = client.post(
            f"{project_path}/tasks/{task_title}/comments/",
            json={"content": "Smoke comment"},
            headers=headers,
        )
        check("create comment", comment.status_code == 201, str(comment.status_code))

        attachment = client.post(
            f"{project_path}/tasks/{task_title}/attachments/",
            files={"file": ("smoke.txt", b"release smoke", "text/plain")},
            headers=headers,
        )
        check("upload attachment", attachment.status_code == 201, str(attachment.status_code))

        search = client.get(
            f"/api/v1/teams/{team_slug}/search", params={"q": "Smoke"}, headers=headers
        )
        check("search", search.status_code == 200, str(search.status_code))

        notifications = client.get("/api/v1/notifications/unread-count", headers=headers)
        check(
            "unread notifications",
            notifications.status_code == 200,
            str(notifications.status_code),
        )

        missing = client.get("/api/v1/teams/does-not-exist-smoke", headers=headers)
        envelope = (
            missing.json()
            if missing.headers.get("content-type", "").startswith("application/json")
            else {}
        )
        check(
            "404 error envelope",
            missing.status_code == 404 and bool(envelope.get("error", {}).get("code")),
            f"{missing.status_code} {envelope.get('error', {}).get('code', '')}",
        )

    failed = [name for name, ok, _ in checks if not ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    if failed:
        print(f"Failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
