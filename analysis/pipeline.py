"""Generate, validate, query, and export Product Signal Lab data."""

from __future__ import annotations

import argparse
import json
import math
import random
import sqlite3
from pathlib import Path
from typing import Iterable

CHANNELS = ("Organic", "Paid Search", "Social", "Referral", "Partnership")
CHANNEL_WEIGHTS = (0.30, 0.24, 0.18, 0.17, 0.11)
PLATFORMS = ("Web", "iOS", "Android")
PLATFORM_WEIGHTS = (0.46, 0.31, 0.23)
DEFAULT_USERS = 30_000
DEFAULT_SEED = 73


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def simulate_users(count: int = DEFAULT_USERS, seed: int = DEFAULT_SEED) -> list[tuple]:
    if count < 500:
        raise ValueError("count must be at least 500 for stable segment estimates")

    rng = random.Random(seed)
    channel_effect = {
        "Organic": 0.05,
        "Paid Search": -0.03,
        "Social": -0.07,
        "Referral": 0.10,
        "Partnership": 0.03,
    }
    platform_effect = {"Web": -0.02, "iOS": 0.04, "Android": 0.0}
    rows: list[tuple] = []

    for user_id in range(1, count + 1):
        cohort_week = rng.randrange(12)
        channel = rng.choices(CHANNELS, weights=CHANNEL_WEIGHTS, k=1)[0]
        platform = rng.choices(PLATFORMS, weights=PLATFORM_WEIGHTS, k=1)[0]
        variant = "B" if rng.random() < 0.5 else "A"

        quality = channel_effect[channel] + platform_effect[platform] + cohort_week * 0.003
        onboarding_probability = clamp(0.80 + quality * 0.55 + (0.018 if variant == "B" else 0))
        completed_onboarding = int(rng.random() < onboarding_probability)

        activation_probability = clamp(0.72 + quality * 0.60 + (0.052 if variant == "B" else 0))
        activated = int(completed_onboarding and rng.random() < activation_probability)

        subscription_probability = clamp(0.28 + quality * 0.30 + (0.012 if variant == "B" else 0))
        subscribed = int(activated and rng.random() < subscription_probability)

        retention_base = clamp(0.74 + quality * 0.45 + (0.012 if variant == "B" else 0))
        retained: list[int] = []
        still_active = bool(activated)
        for week in range(1, 7):
            weekly_probability = clamp(retention_base - week * 0.052)
            still_active = still_active and rng.random() < weekly_probability
            retained.append(int(still_active))

        revenue = 0.0
        if subscribed:
            monthly = {"Web": 29.0, "iOS": 31.0, "Android": 27.0}[platform]
            revenue = round(monthly * rng.choice((1, 2, 3)) + rng.uniform(0, 12), 2)

        rows.append(
            (
                user_id,
                cohort_week,
                channel,
                platform,
                variant,
                completed_onboarding,
                activated,
                subscribed,
                *retained,
                revenue,
            )
        )
    return rows


def create_database(connection: sqlite3.Connection, rows: Iterable[tuple], schema_path: Path) -> None:
    connection.executescript(schema_path.read_text(encoding="utf-8"))
    connection.executemany(
        """
        INSERT INTO user_journeys (
            user_id, cohort_week, acquisition_channel, platform, experiment_variant,
            completed_onboarding, activated, subscribed,
            retained_w1, retained_w2, retained_w3, retained_w4, retained_w5, retained_w6,
            revenue_90d
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    connection.commit()


def where_clause(channel: str, platform: str) -> tuple[str, list[str]]:
    clauses: list[str] = []
    parameters: list[str] = []
    if channel != "All channels":
        if channel not in CHANNELS:
            raise ValueError(f"unsupported channel: {channel}")
        clauses.append("acquisition_channel = ?")
        parameters.append(channel)
    if platform != "All platforms":
        if platform not in PLATFORMS:
            raise ValueError(f"unsupported platform: {platform}")
        clauses.append("platform = ?")
        parameters.append(platform)
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), parameters


def normal_cdf(value: float) -> float:
    return 0.5 * (1 + math.erf(value / math.sqrt(2)))


def experiment_stats(rows: list[sqlite3.Row]) -> dict:
    by_variant = {row["experiment_variant"]: row for row in rows}
    control = by_variant["A"]
    treatment = by_variant["B"]
    rate_a = control["activations"] / control["users"]
    rate_b = treatment["activations"] / treatment["users"]
    difference = rate_b - rate_a
    pooled = (control["activations"] + treatment["activations"]) / (
        control["users"] + treatment["users"]
    )
    standard_error = math.sqrt(
        pooled
        * (1 - pooled)
        * (1 / control["users"] + 1 / treatment["users"])
    )
    z_score = difference / standard_error if standard_error else 0.0
    p_value = 2 * (1 - normal_cdf(abs(z_score)))
    interval_error = 1.96 * math.sqrt(
        rate_a * (1 - rate_a) / control["users"]
        + rate_b * (1 - rate_b) / treatment["users"]
    )
    return {
        "control_users": control["users"],
        "treatment_users": treatment["users"],
        "control_rate": round(rate_a, 4),
        "treatment_rate": round(rate_b, 4),
        "absolute_lift": round(difference, 4),
        "relative_lift": round(difference / rate_a, 4),
        "p_value": round(p_value, 5),
        "ci_low": round(difference - interval_error, 4),
        "ci_high": round(difference + interval_error, 4),
        "control_retention_w4": round(control["retention_w4"], 4),
        "treatment_retention_w4": round(treatment["retention_w4"], 4),
        "decision": "Ship treatment B" if p_value < 0.05 and difference > 0 else "Keep collecting data",
    }


def analyze_segment(connection: sqlite3.Connection, channel: str, platform: str) -> dict:
    where, parameters = where_clause(channel, platform)
    funnel = connection.execute(
        f"""
        SELECT COUNT(*) AS signed_up,
               SUM(completed_onboarding) AS completed_onboarding,
               SUM(activated) AS activated,
               SUM(subscribed) AS subscribed,
               AVG(retained_w4) AS retention_w4,
               SUM(revenue_90d) AS revenue_90d
        FROM user_journeys{where}
        """,
        parameters,
    ).fetchone()
    if not funnel or funnel["signed_up"] == 0:
        raise ValueError("segment has no users")

    cohort_rows = connection.execute(
        f"""
        SELECT cohort_week,
               COUNT(*) AS users,
               AVG(retained_w1) AS w1,
               AVG(retained_w2) AS w2,
               AVG(retained_w3) AS w3,
               AVG(retained_w4) AS w4,
               AVG(retained_w5) AS w5,
               AVG(retained_w6) AS w6
        FROM user_journeys{where}
        GROUP BY cohort_week
        ORDER BY cohort_week
        """,
        parameters,
    ).fetchall()

    variant_where = where + (" AND " if where else " WHERE ") + "experiment_variant IN ('A', 'B')"
    experiment_rows = connection.execute(
        f"""
        SELECT experiment_variant,
               COUNT(*) AS users,
               SUM(activated) AS activations,
               AVG(retained_w4) AS retention_w4
        FROM user_journeys{variant_where}
        GROUP BY experiment_variant
        ORDER BY experiment_variant
        """,
        parameters,
    ).fetchall()

    signed_up = funnel["signed_up"]
    stages = [
        {"name": "Signed up", "count": signed_up, "rate": 1.0},
        {
            "name": "Completed onboarding",
            "count": funnel["completed_onboarding"],
            "rate": round(funnel["completed_onboarding"] / signed_up, 4),
        },
        {
            "name": "Activated",
            "count": funnel["activated"],
            "rate": round(funnel["activated"] / signed_up, 4),
        },
        {
            "name": "Subscribed",
            "count": funnel["subscribed"],
            "rate": round(funnel["subscribed"] / signed_up, 4),
        },
    ]
    retention = [
        {
            "cohort": f"Week {row['cohort_week'] + 1:02d}",
            "users": row["users"],
            "rates": [1.0] + [round(row[f"w{week}"], 4) for week in range(1, 7)],
        }
        for row in cohort_rows
    ]
    experiment = experiment_stats(experiment_rows)
    return {
        "label": " · ".join(value for value in (channel, platform) if not value.startswith("All")) or "All users",
        "users": signed_up,
        "activation_rate": stages[2]["rate"],
        "conversion_rate": stages[3]["rate"],
        "retention_w4": round(funnel["retention_w4"], 4),
        "revenue_90d": round(funnel["revenue_90d"], 2),
        "funnel": stages,
        "retention": retention,
        "experiment": experiment,
    }


def build_summary(connection: sqlite3.Connection) -> dict:
    segments: dict[str, dict] = {}
    channel_options = ("All channels",) + CHANNELS
    platform_options = ("All platforms",) + PLATFORMS
    for channel in channel_options:
        for platform in platform_options:
            key = f"{channel}|{platform}"
            segments[key] = analyze_segment(connection, channel, platform)

    return {
        "metadata": {
            "title": "Product Signal Lab",
            "users": DEFAULT_USERS,
            "cohort_count": 12,
            "seed": DEFAULT_SEED,
            "source": "Deterministic synthetic SaaS journey data",
            "generated_on": "2026-09-01",
        },
        "filters": {
            "channels": ["All channels", *CHANNELS],
            "platforms": ["All platforms", *PLATFORMS],
        },
        "segments": segments,
    }


def validate_database(connection: sqlite3.Connection) -> dict:
    row = connection.execute(
        """
        SELECT COUNT(*) AS users,
               COUNT(DISTINCT user_id) AS unique_users,
               SUM(activated > completed_onboarding) AS invalid_activation,
               SUM(subscribed > activated) AS invalid_subscription
        FROM user_journeys
        """
    ).fetchone()
    if row["users"] != row["unique_users"]:
        raise ValueError("duplicate users found")
    if row["invalid_activation"] or row["invalid_subscription"]:
        raise ValueError("funnel ordering is invalid")

    plan = connection.execute(
        """
        EXPLAIN QUERY PLAN
        SELECT * FROM user_journeys
        WHERE acquisition_channel = ? AND platform = ?
        """,
        ("Organic", "Web"),
    ).fetchall()
    plan_text = " ".join(str(value) for item in plan for value in item)
    if "idx_journeys_channel_platform" not in plan_text:
        raise ValueError("expected composite index was not used")
    return {"users": row["users"], "index_verified": True}


def run_pipeline(
    output_json: Path,
    database_path: Path | None = None,
    count: int = DEFAULT_USERS,
    seed: int = DEFAULT_SEED,
) -> dict:
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "sql" / "schema.sql"
    connection = sqlite3.connect(database_path or ":memory:")
    connection.row_factory = sqlite3.Row
    try:
        create_database(connection, simulate_users(count, seed), schema_path)
        validation = validate_database(connection)
        summary = build_summary(connection)
        summary["metadata"]["users"] = count
        summary["metadata"]["seed"] = seed
        summary["metadata"]["validation"] = validation
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary
    finally:
        connection.close()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=root / "dist" / "data" / "summary.json")
    parser.add_argument("--database", type=Path)
    parser.add_argument("--count", type=int, default=DEFAULT_USERS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    summary = run_pipeline(args.output, args.database, args.count, args.seed)
    if args.check:
        assert summary["metadata"]["validation"]["index_verified"]
        assert len(summary["segments"]) == 24


if __name__ == "__main__":
    main()
