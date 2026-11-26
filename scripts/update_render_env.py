"""Point the Render service at the new database (T-131).

Updates the service's environment variables through the Render REST API,
removes the retired InsForge ones and optionally triggers a deploy, without
ever printing a value.

    export RENDER_API_KEY=rnd_...
    python scripts/update_render_env.py --service taskflow-api --apply --deploy --wait

Examples:

    # Show the plan without calling the API
    python scripts/update_render_env.py --dry-run

    # Only rewrite env vars, do not redeploy
    python scripts/update_render_env.py --apply
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import httpx

API = "https://api.render.com/v1"

# Variables that must exist on the API service after the migration. Values come
# from the local .env that `neon env pull` keeps up to date.
FROM_LOCAL_ENV = ("DATABASE_URL", "DATABASE_URL_UNPOOLED")
STATIC = {"DB_SSLMODE": "require", "STORAGE_BACKEND": "database"}
RETIRED = ("INSFORGE_URL", "INSFORGE_API_KEY", "INSFORGE_STORAGE_BUCKET")


def read_local_env(path: Path) -> dict[str, str]:
    """Parse a dotenv file without importing the app settings."""
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def build_plan(local: dict[str, str]) -> dict[str, str]:
    """Return the variables to set, rejecting missing/empty local values."""
    plan = dict(STATIC)
    missing = []
    for key in FROM_LOCAL_ENV:
        value = local.get(key, "")
        if not value:
            missing.append(key)
            continue
        plan[key] = value
    if missing:
        raise SystemExit(f"Missing {', '.join(missing)} in .env; run `neon env pull` first.")
    return plan


def client(api_key: str) -> httpx.Client:
    return httpx.Client(
        base_url=API,
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        timeout=60.0,
    )


def find_service(http: httpx.Client, name: str) -> dict:
    response = http.get("/services", params={"name": name, "limit": 20})
    response.raise_for_status()
    services = [item["service"] for item in response.json()]
    matches = [service for service in services if service.get("name") == name]
    if not matches:
        raise SystemExit(f"Service '{name}' not found in this Render account")
    if len(matches) > 1:
        raise SystemExit(f"Service name '{name}' is ambiguous; pass --service-id")
    return matches[0]


def current_env(http: httpx.Client, service_id: str) -> list[dict]:
    response = http.get(f"/services/{service_id}/env-vars", params={"limit": 100})
    response.raise_for_status()
    return [item["envVar"] for item in response.json()]


def upsert(http: httpx.Client, service_id: str, key: str, value: str) -> None:
    response = http.put(f"/services/{service_id}/env-vars/{key}", json={"value": value})
    response.raise_for_status()


def delete(http: httpx.Client, service_id: str, key: str) -> None:
    response = http.delete(f"/services/{service_id}/env-vars/{key}")
    if response.status_code not in (204, 404):
        response.raise_for_status()


def trigger_deploy(http: httpx.Client, service_id: str) -> str:
    response = http.post(f"/services/{service_id}/deploys", json={})
    response.raise_for_status()
    return response.json()["id"]


def wait_for_deploy(http: httpx.Client, service_id: str, deploy_id: str, timeout: int) -> str:
    deadline = time.monotonic() + timeout
    status = "created"
    while time.monotonic() < deadline:
        response = http.get(f"/services/{service_id}/deploys/{deploy_id}")
        response.raise_for_status()
        status = response.json()["status"]
        if status in {"live", "deactivated", "build_failed", "update_failed", "canceled"}:
            return status
        time.sleep(15)
    return f"timeout (last status: {status})"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update the Render env for the Neon cutover")
    parser.add_argument("--service", default="taskflow-api", help="Render service name")
    parser.add_argument("--service-id", default=None, help="Skip the name lookup")
    parser.add_argument("--env-file", default=".env", help="Local env with the Neon URLs")
    parser.add_argument("--apply", action="store_true", help="Actually call the Render API")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan and exit")
    parser.add_argument("--deploy", action="store_true", help="Trigger a deploy afterwards")
    parser.add_argument("--wait", action="store_true", help="Wait for the deploy to go live")
    parser.add_argument("--timeout", type=int, default=900, help="Deploy wait in seconds")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    local = read_local_env(Path(args.env_file))
    plan = build_plan(local)

    print(f"Set on {args.service}:")
    for key in plan:
        print(f"  {key}=<redacted>")
    print("Delete:")
    for key in RETIRED:
        print(f"  {key}")

    if args.dry_run or not args.apply:
        print("\nDry run: no requests sent. Add --apply to push the changes.")
        return 0

    api_key = os.environ.get("RENDER_API_KEY", "")
    if not api_key:
        raise SystemExit("RENDER_API_KEY is not set")

    with client(api_key) as http:
        service_id = args.service_id or find_service(http, args.service)["id"]
        print(f"\nService id: {service_id}")

        existing = {item["key"] for item in current_env(http, service_id)}
        for key, value in plan.items():
            upsert(http, service_id, key, value)
            print(f"  {'updated' if key in existing else 'created'} {key}")

        for key in RETIRED:
            if key in existing:
                delete(http, service_id, key)
                print(f"  deleted {key}")

        if args.deploy:
            deploy_id = trigger_deploy(http, service_id)
            print(f"\nDeploy {deploy_id} triggered")
            if args.wait:
                status = wait_for_deploy(http, service_id, deploy_id, args.timeout)
                print(f"Deploy status: {status}")
                if status != "live":
                    return 1
        else:
            print("\nEnv updated. Render restarts with the new values; use --deploy to force it.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
