from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def ensure_outdir() -> Path:
    out = Path("benchmarks/out")
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_json(results: dict[str, Any]) -> Path:
    out = ensure_outdir() / "results.json"
    out.write_text(json.dumps(results, indent=2, sort_keys=True))
    return out


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _geom_mean(values: list[float]) -> float:
    vals = [v for v in values if v > 0]
    if not vals:
        return 0.0
    return math.exp(sum(math.log(v) for v in vals) / len(vals))


def _frameworks(results: dict[str, Any]) -> list[str]:
    return sorted(results.get("frameworks", {}).keys())


def _scenario_names(results: dict[str, Any], group: str) -> list[str]:
    names: set[str] = set()
    for fw, fwdata in results["frameworks"].items():
        for name in fwdata.get(group, {}).keys():
            names.add(name)
    return sorted(names)


def _pick_winner(
    frameworks: list[str], metric_by_fw: dict[str, float], higher_is_better: bool
) -> tuple[str, float]:
    items = [(fw, metric_by_fw.get(fw, 0.0)) for fw in frameworks]
    if higher_is_better:
        fw, v = max(items, key=lambda t: t[1])
    else:
        # lower is better, but ignore 0 (missing)
        items2 = [(fw, v) for fw, v in items if v > 0]
        if not items2:
            return ("n/a", 0.0)
        fw, v = min(items2, key=lambda t: t[1])
    return fw, v


def _build_conclusions(results: dict[str, Any]) -> dict[str, Any]:
    fws = _frameworks(results)
    http_scenarios = _scenario_names(results, "http")
    ws_scenarios = _scenario_names(results, "ws")

    per_scenario: list[dict[str, Any]] = []

    # Per-scenario winners (HTTP)
    for sc in http_scenarios:
        ops = {}
        p95 = {}
        errors = {}
        for fw in fws:
            s = results["frameworks"][fw]["http"].get(sc)
            if not s:
                continue
            ops[fw] = _safe_float(s.get("ops_per_s"))
            p95[fw] = _safe_float(s.get("p95_ms"))
            errors[fw] = int(s.get("errors", 0))

        ops_w, ops_v = _pick_winner(fws, ops, higher_is_better=True)
        p95_w, p95_v = _pick_winner(fws, p95, higher_is_better=False)

        per_scenario.append(
            {
                "group": "http",
                "scenario": sc,
                "winner_ops": {"framework": ops_w, "ops_per_s": ops_v},
                "winner_p95": {"framework": p95_w, "p95_ms": p95_v},
                "errors": errors,
            }
        )

    # Per-scenario winners (WS)
    for sc in ws_scenarios:
        ops = {}
        p95 = {}
        errors = {}
        for fw in fws:
            s = results["frameworks"][fw]["ws"].get(sc)
            if not s:
                continue
            ops[fw] = _safe_float(s.get("ops_per_s"))
            p95[fw] = _safe_float(s.get("p95_ms"))
            errors[fw] = int(s.get("errors", 0))

        ops_w, ops_v = _pick_winner(fws, ops, higher_is_better=True)
        p95_w, p95_v = _pick_winner(fws, p95, higher_is_better=False)

        per_scenario.append(
            {
                "group": "ws",
                "scenario": sc,
                "winner_ops": {"framework": ops_w, "ops_per_s": ops_v},
                "winner_p95": {"framework": p95_w, "p95_ms": p95_v},
                "errors": errors,
            }
        )

    # Overall score: geometric mean of ops/s across HTTP scenarios (more stable than averaging)
    overall_ops_gm: dict[str, float] = {}
    overall_p95_mean: dict[str, float] = {}
    overall_errors: dict[str, int] = {}

    for fw in fws:
        ops_vals: list[float] = []
        p95_vals: list[float] = []
        err_sum = 0

        for sc in http_scenarios:
            s = results["frameworks"][fw]["http"].get(sc)
            if not s:
                continue
            ops_vals.append(_safe_float(s.get("ops_per_s")))
            p95 = _safe_float(s.get("p95_ms"))
            if p95 > 0:
                p95_vals.append(p95)
            err_sum += int(s.get("errors", 0))

        overall_ops_gm[fw] = _geom_mean(ops_vals)
        overall_p95_mean[fw] = (sum(p95_vals) / len(p95_vals)) if p95_vals else 0.0
        overall_errors[fw] = err_sum

    overall_ops_w, overall_ops_v = _pick_winner(fws, overall_ops_gm, higher_is_better=True)
    overall_p95_w, overall_p95_v = _pick_winner(fws, overall_p95_mean, higher_is_better=False)

    return {
        "frameworks": fws,
        "http_scenarios": http_scenarios,
        "ws_scenarios": ws_scenarios,
        "per_scenario": per_scenario,
        "overall": {
            "ops_geom_mean": overall_ops_gm,
            "p95_mean": overall_p95_mean,
            "errors": overall_errors,
            "winner_ops_geom_mean": {"framework": overall_ops_w, "ops_per_s": overall_ops_v},
            "winner_p95_mean": {"framework": overall_p95_w, "p95_ms": overall_p95_v},
        },
    }


def _try_write_charts(results: dict[str, Any]) -> list[str]:
    """
    Writes PNG charts to benchmarks/out/.
    Returns a list of filenames created (relative names).
    """
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception:
        return []

    out = ensure_outdir()
    fws = _frameworks(results)
    http_scenarios = _scenario_names(results, "http")

    created: list[str] = []

    # Chart 1: Overall ops/s geometric mean
    conclusions = _build_conclusions(results)
    gm = conclusions["overall"]["ops_geom_mean"]
    values = [float(gm.get(fw, 0.0)) for fw in fws]

    plt.figure()
    plt.bar(fws, values)
    plt.title("Overall throughput (HTTP) – geometric mean of ops/s")
    plt.ylabel("ops/s (higher is better)")
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    fname = "chart_overall_ops_geom_mean.png"
    plt.savefig(out / fname, dpi=160)
    plt.close()
    created.append(fname)

    # Chart 2: Per-scenario p95 latency (HTTP) – one chart per scenario (readable)
    for sc in http_scenarios:
        p95 = []
        for fw in fws:
            s = results["frameworks"][fw]["http"].get(sc)
            p95.append(_safe_float(s.get("p95_ms")) if s else 0.0)

        plt.figure()
        plt.bar(fws, p95)
        plt.title(f"HTTP p95 latency – {sc}")
        plt.ylabel("p95 (ms) (lower is better)")
        plt.xticks(rotation=25, ha="right")
        plt.tight_layout()
        fname = f"chart_http_p95_{sc}.png"
        plt.savefig(out / fname, dpi=160)
        plt.close()
        created.append(fname)

    return created


def write_markdown(results: dict[str, Any]) -> Path:
    out = ensure_outdir() / "results.md"
    conclusions = _build_conclusions(results)
    charts = _try_write_charts(results)

    lines: list[str] = []
    lines.append("# Benchmark Results\n")
    lines.append("All runs: Palfrey server, same host/port, one framework at a time.\n")

    # Conclusions section (human-readable)
    ov = conclusions["overall"]
    lines.append("## Conclusions\n")

    lines.append(
        f"- **Best overall HTTP throughput (geometric mean ops/s):** "
        f"`{ov['winner_ops_geom_mean']['framework']}` "
        f"({ov['winner_ops_geom_mean']['ops_per_s']:.2f} ops/s)\n"
    )
    lines.append(
        f"- **Best overall HTTP p95 latency (mean across HTTP scenarios):** "
        f"`{ov['winner_p95_mean']['framework']}` "
        f"({ov['winner_p95_mean']['p95_ms']:.3f} ms)\n"
    )

    # Error summary
    err_sorted = sorted(ov["errors"].items(), key=lambda t: t[1], reverse=True)
    if err_sorted:
        lines.append("### Errors (HTTP total)\n")
        for fw, e in err_sorted:
            lines.append(f"- `{fw}`: {e}\n")

    # Per-scenario winners
    lines.append("\n### Per-scenario winners\n")
    lines.append("| Group | Scenario | Best ops/s | Best p95 latency |")
    lines.append("|---|---|---|---|")
    for row in conclusions["per_scenario"]:
        lines.append(
            f"| {row['group']} | {row['scenario']} | "
            f"{row['winner_ops']['framework']} ({row['winner_ops']['ops_per_s']:.2f}) | "
            f"{row['winner_p95']['framework']} ({row['winner_p95']['p95_ms']:.3f} ms) |"
        )

    # Charts (if matplotlib installed)
    if charts:
        lines.append("\n## Charts\n")
        lines.append("These images are written to `benchmarks/out/`.\n")
        for c in charts:
            lines.append(f"![{c}](./{c})\n")

    # Raw tables
    for fw, fwdata in results["frameworks"].items():
        lines.append(f"\n## {fw}\n")
        for group_name in ("http", "ws"):
            if group_name not in fwdata:
                continue
            lines.append(f"### {group_name.upper()}\n")
            lines.append(
                "| Scenario | OK | Errors | Ops/s | p50 (ms) | p95 (ms) | p99 (ms) | mean (ms) | min (ms) | max (ms) |"
            )
            lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
            for scenario_name, summary in fwdata[group_name].items():
                lines.append(
                    f"| {scenario_name} | {summary['ok']} | {summary['errors']} | "
                    f"{summary['ops_per_s']:.2f} | {summary['p50_ms']:.3f} | {summary['p95_ms']:.3f} | "
                    f"{summary['p99_ms']:.3f} | {summary['mean_ms']:.3f} | {summary['min_ms']:.3f} | {summary['max_ms']:.3f} |"
                )
            lines.append("")

    out.write_text("\n".join(lines))
    return out
