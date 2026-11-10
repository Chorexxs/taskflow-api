"""Smoke de performance para el release de TaskFlow (T-080).

Mide la latencia de endpoints de lectura y falla si el p95 supera el objetivo
de NFR-PERF-01 (300 ms por defecto). Usa solo la libreria estandar.

Ejemplos:
    python scripts/smoke_performance.py --base-url http://localhost:8000
    python scripts/smoke_performance.py --samples 30 --json
    python scripts/smoke_performance.py --token "$TOKEN" --samples 20

El token es opcional: sin el solo se miden los endpoints de salud.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Sequence


@dataclass
class EndpointResult:
    name: str
    path: str
    samples: int
    errors: int
    statuses: list[int]
    p50_ms: float
    p95_ms: float
    max_ms: float


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


def _request(url: str, token: str | None, timeout: float) -> tuple[int, float]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        exc.read()
        status = exc.code
    elapsed_ms = (time.perf_counter() - started) * 1000
    return status, elapsed_ms


def measure(
    name: str,
    path: str,
    base_url: str,
    samples: int,
    token: str | None,
    timeout: float,
) -> EndpointResult:
    url = base_url.rstrip("/") + path
    latencies: list[float] = []
    statuses: list[int] = []
    errors = 0
    for _ in range(samples):
        status, elapsed = _request(url, token, timeout)
        statuses.append(status)
        if status >= 400:
            errors += 1
        else:
            latencies.append(elapsed)
    return EndpointResult(
        name=name,
        path=path,
        samples=samples,
        errors=errors,
        statuses=statuses,
        p50_ms=round(_percentile(latencies, 0.50), 1),
        p95_ms=round(_percentile(latencies, 0.95), 1),
        max_ms=round(max(latencies) if latencies else 0.0, 1),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smoke de performance de TaskFlow")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="URL base de la API (por defecto http://localhost:8000)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=20,
        help="Peticiones por endpoint (por defecto 20)",
    )
    parser.add_argument(
        "--threshold-ms",
        type=float,
        default=300.0,
        help="p95 maximo permitido en lecturas (NFR-PERF-01)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Timeout por peticion en segundos",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Access token opcional para medir endpoints autenticados",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Imprime el resultado como JSON",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.samples < 1:
        print("--samples debe ser >= 1", file=sys.stderr)
        return 2

    endpoints = [
        ("health", "/health"),
        ("health_live", "/health/live"),
        ("health_ready", "/health/ready"),
    ]
    if args.token:
        endpoints.extend(
            [
                ("current_user", "/api/v1/users/me"),
                ("unread_notifications", "/api/v1/notifications/unread-count"),
            ]
        )

    # Calentamiento: evita medir el arranque en frio de Render como p95.
    try:
        _request(args.base_url.rstrip("/") + "/health/live", args.token, args.timeout)
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"No se pudo alcanzar {args.base_url}: {exc}", file=sys.stderr)
        return 2

    results = [
        measure(name, path, args.base_url, args.samples, args.token, args.timeout)
        for name, path in endpoints
    ]

    failed = False
    if args.json:
        print(json.dumps([asdict(result) for result in results], indent=2))
    else:
        print(f"Smoke de performance contra {args.base_url}")
        print(f"{'endpoint':<22}{'p50':>8}{'p95':>8}{'max':>8}{'errores':>9}")
        for result in results:
            print(
                f"{result.name:<22}{result.p50_ms:>7.1f}ms"
                f"{result.p95_ms:>7.1f}ms{result.max_ms:>7.1f}ms"
                f"{result.errors:>9}"
            )

    for result in results:
        if result.errors:
            print(
                f"FALLO: {result.name} devolvio {result.errors} error(es) "
                f"({sorted(set(result.statuses))})",
                file=sys.stderr,
            )
            failed = True
        if result.p95_ms > args.threshold_ms:
            print(
                f"FALLO: {result.name} p95={result.p95_ms}ms supera "
                f"{args.threshold_ms}ms (NFR-PERF-01)",
                file=sys.stderr,
            )
            failed = True

    if failed:
        return 1
    print("OK: latencias y errores dentro del objetivo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
