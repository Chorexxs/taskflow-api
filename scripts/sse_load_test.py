"""SSE load test for notifications (T-081).

Opens N concurrent authenticated ``/api/v1/notifications/stream`` connections
for a fixed duration and reports handshake latency, errors and received frames.

Example:
    python scripts/sse_load_test.py \
        --base-url http://127.0.0.1:8000 --token "$TOKEN" \
        --connections 500 --duration 10

For a local run, disable the per-IP rate limit and raise the connection caps:

    RATE_LIMIT_ENABLED=false SSE_MAX_CONNECTIONS=600 \
    SSE_MAX_CONNECTIONS_PER_USER=600 python -m uvicorn app.main:app
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from dataclasses import dataclass, field
from typing import Sequence

import httpx


@dataclass
class StreamResult:
    opened: bool = False
    status: int | None = None
    error: str | None = None
    handshake_ms: float = 0.0
    events: int = 0
    heartbeats: int = 0
    closed_reason: str = "timeout"

    def as_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class Summary:
    total: int = 0
    opened: int = 0
    failed: int = 0
    statuses: dict[int, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    handshakes: list[float] = field(default_factory=list)
    events: int = 0
    heartbeats: int = 0


async def _open_stream(
    client: httpx.AsyncClient,
    url: str,
    token: str,
    deadline: float,
) -> StreamResult:
    result = StreamResult()
    headers = {"Accept": "text/event-stream", "Authorization": f"Bearer {token}"}
    started = time.perf_counter()
    try:
        async with client.stream("GET", url, headers=headers, timeout=None) as response:
            result.status = response.status_code
            result.handshake_ms = (time.perf_counter() - started) * 1000
            if response.status_code != 200:
                result.error = f"HTTP {response.status_code}"
                return result
            result.opened = True
            async for line in response.aiter_lines():
                if time.perf_counter() >= deadline:
                    break
                if line.startswith("data:"):
                    result.events += 1
                elif line.startswith(": heartbeat"):
                    result.heartbeats += 1
    except asyncio.CancelledError:  # pragma: no cover - shutdown
        raise
    except Exception as exc:  # noqa: BLE001 - report any transport error
        result.error = type(exc).__name__
    return result


def _percentile(values: Sequence[float], percentile: float) -> float:
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SSE load test for TaskFlow")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", required=True, help="Access token")
    parser.add_argument("--connections", type=int, default=500)
    parser.add_argument("--duration", type=float, default=10.0, help="Seconds")
    parser.add_argument(
        "--min-opened-ratio",
        type=float,
        default=0.99,
        help="Fail if fewer than this ratio of connections opened",
    )
    parser.add_argument("--json", action="store_true")
    return parser


async def run_load_test(args: argparse.Namespace) -> int:
    url = args.base_url.rstrip("/") + "/api/v1/notifications/stream"
    limits = httpx.Limits(
        max_connections=args.connections,
        max_keepalive_connections=args.connections,
    )
    async with httpx.AsyncClient(limits=limits, timeout=None) as client:
        # Warm up so TLS/handshake setup is not mixed with the measurement.
        await _open_stream(client, url, args.token, time.perf_counter())

        deadline = time.perf_counter() + args.duration
        tasks = [
            asyncio.create_task(_open_stream(client, url, args.token, deadline))
            for _ in range(args.connections)
        ]
        results = await asyncio.gather(*tasks)

    summary = Summary(total=len(results))
    for result in results:
        if result.opened:
            summary.opened += 1
            summary.handshakes.append(result.handshake_ms)
            summary.events += result.events
            summary.heartbeats += result.heartbeats
        else:
            summary.failed += 1
            if result.status is not None:
                summary.statuses[result.status] = summary.statuses.get(result.status, 0) + 1
            if result.error and len(summary.errors) < 10:
                summary.errors.append(result.error)

    p50 = round(_percentile(summary.handshakes, 0.50), 1)
    p95 = round(_percentile(summary.handshakes, 0.95), 1)

    if args.json:
        import json

        print(
            json.dumps(
                {
                    "total": summary.total,
                    "opened": summary.opened,
                    "failed": summary.failed,
                    "statuses": summary.statuses,
                    "errors": summary.errors,
                    "handshake_p50_ms": p50,
                    "handshake_p95_ms": p95,
                    "events": summary.events,
                    "heartbeats": summary.heartbeats,
                },
                indent=2,
            )
        )
    else:
        print(f"SSE load test against {url}")
        print(f"connections: {summary.total}")
        print(f"opened:      {summary.opened}")
        print(f"failed:      {summary.failed} {summary.statuses or ''}")
        print(f"handshake p50/p95: {p50} ms / {p95} ms")
        print(f"events: {summary.events}  heartbeats: {summary.heartbeats}")
        if summary.errors:
            print(f"errors: {', '.join(summary.errors)}", file=sys.stderr)

    ratio = summary.opened / summary.total if summary.total else 0.0
    if ratio < args.min_opened_ratio:
        print(
            f"FALLO: solo se abrieron {summary.opened}/{summary.total} "
            f"conexiones ({ratio:.0%} < {args.min_opened_ratio:.0%})",
            file=sys.stderr,
        )
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.connections < 1:
        print("--connections debe ser >= 1", file=sys.stderr)
        return 2
    return asyncio.run(run_load_test(args))


if __name__ == "__main__":
    raise SystemExit(main())
