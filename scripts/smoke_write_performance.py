"""Write performance smoke (T-111).

Measures create/update latency for tasks against a live API and fails when the
p95 exceeds the configured threshold. Intended for staging, a local server or a
controlled production check (it leaves a disposable team/project behind).

Examples:
    python scripts/smoke_write_performance.py --base-url http://127.0.0.1:8000
    python scripts/smoke_write_performance.py --base-url https://... --samples 10
    SMOKE_TOKEN=... python scripts/smoke_write_performance.py --base-url https://...
"""

from __future__ import annotations

import argparse
import os
import secrets
import statistics
import sys
import time
from collections.abc import Sequence

import httpx


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _times(values: list[float]) -> str:
    return (
        f"p50={_percentile(values, 0.50):.1f}ms "
        f"p95={_percentile(values, 0.95):.1f}ms "
        f"max={max(values):.1f}ms"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TaskFlow write performance smoke")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", default=os.environ.get("SMOKE_TOKEN", ""))
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--threshold-ms", type=float, default=500.0)
    parser.add_argument("--timeout", type=float, default=60.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.samples < 1:
        print("--samples must be >= 1", file=sys.stderr)
        return 2
    base = args.base_url.rstrip("/")
    suffix = str(int(time.time()))
    password = secrets.token_urlsafe(24)
    email = f"write-smoke+{suffix}@example.com"

    with httpx.Client(base_url=base, timeout=args.timeout) as client:
        token = args.token
        if not token:
            registered = client.post(
                "/api/v1/auth/register",
                json={"email": email, "password": password},
            )
            if registered.status_code != 201:
                print(f"register failed: {registered.status_code}", file=sys.stderr)
                return 1
            login = client.post(
                "/api/v1/auth/login",
                data={"username": email, "password": password},
            )
            if login.status_code != 200:
                print(f"login failed: {login.status_code}", file=sys.stderr)
                return 1
            token = login.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        team = client.post(
            "/api/v1/teams/",
            json={"name": f"Write Smoke {suffix}", "slug": f"write-smoke-{suffix}"},
            headers=headers,
        )
        if team.status_code != 201:
            print(f"team failed: {team.status_code}", file=sys.stderr)
            return 1
        team_slug = team.json()["slug"]
        project = client.post(
            f"/api/v1/teams/{team_slug}/projects/",
            json={"name": f"Write Project {suffix}"},
            headers=headers,
        )
        if project.status_code != 201:
            print(f"project failed: {project.status_code}", file=sys.stderr)
            return 1
        project_name = project.json()["name"]
        project_id = project.json()["id"]
        tasks_url = f"/api/v1/teams/{team_slug}/projects/{project_id}/tasks/"

        create_times: list[float] = []
        update_times: list[float] = []
        errors = 0
        created: list[int] = []
        for index in range(args.samples):
            started = time.perf_counter()
            created_response = client.post(
                tasks_url,
                json={"title": f"Write smoke {index} {suffix}"},
                headers=headers,
            )
            create_times.append((time.perf_counter() - started) * 1000)
            if created_response.status_code != 201:
                errors += 1
                continue
            created.append(created_response.json()["id"])

            started = time.perf_counter()
            updated = client.patch(
                f"{tasks_url}{created_response.json()['id']}/status",
                json={"status": "in_progress"},
                headers=headers,
            )
            update_times.append((time.perf_counter() - started) * 1000)
            if updated.status_code != 200:
                errors += 1

        for task_id in created:
            client.delete(f"{tasks_url}{task_id}", headers=headers)

        p95_create = _percentile(create_times, 0.95)
        p95_update = _percentile(update_times, 0.95)
        print(f"create tasks ({len(create_times)}): {_times(create_times)}")
        print(f"update status ({len(update_times)}): {_times(update_times)}")
        print(
            f"median create={statistics.median(create_times):.1f}ms "
            f"errors={errors}"
        )

        if errors:
            print(f"{errors} requests failed", file=sys.stderr)
            return 1
        if p95_create > args.threshold_ms or p95_update > args.threshold_ms:
            print(
                f"p95 exceeds {args.threshold_ms:.0f}ms "
                f"(create={p95_create:.1f}, update={p95_update:.1f})",
                file=sys.stderr,
            )
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
