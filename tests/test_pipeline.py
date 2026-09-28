import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from analysis.pipeline import (
    DEFAULT_SEED,
    analyze_segment,
    build_summary,
    create_database,
    simulate_users,
    validate_database,
    where_clause,
)


ROOT = Path(__file__).resolve().parents[1]


class ProductSignalPipelineTests(unittest.TestCase):
    def connection_with_rows(self, count=2_000):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        create_database(connection, simulate_users(count), ROOT / "sql" / "schema.sql")
        return connection

    def test_generation_is_deterministic(self):
        self.assertEqual(simulate_users(500, DEFAULT_SEED), simulate_users(500, DEFAULT_SEED))

    def test_generation_rejects_small_samples(self):
        with self.assertRaisesRegex(ValueError, "at least 500"):
            simulate_users(499)

    def test_schema_constraints_and_funnel_order(self):
        connection = self.connection_with_rows()
        validation = validate_database(connection)
        self.assertEqual(validation["users"], 2_000)
        self.assertTrue(validation["index_verified"])
        connection.close()

    def test_composite_index_serves_common_filter(self):
        connection = self.connection_with_rows()
        plan = connection.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM user_journeys WHERE acquisition_channel = ? AND platform = ?",
            ("Referral", "iOS"),
        ).fetchall()
        self.assertIn("idx_journeys_channel_platform", " ".join(str(v) for row in plan for v in row))
        connection.close()

    def test_segment_funnel_is_monotonic(self):
        connection = self.connection_with_rows()
        segment = analyze_segment(connection, "All channels", "All platforms")
        counts = [stage["count"] for stage in segment["funnel"]]
        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertEqual(len(segment["retention"]), 12)
        connection.close()

    def test_channel_and_platform_filters(self):
        connection = self.connection_with_rows()
        all_users = analyze_segment(connection, "All channels", "All platforms")["users"]
        referral_ios = analyze_segment(connection, "Referral", "iOS")["users"]
        self.assertGreater(all_users, referral_ios)
        self.assertGreater(referral_ios, 0)
        connection.close()

    def test_invalid_filters_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported channel"):
            where_clause("Unknown", "All platforms")
        with self.assertRaisesRegex(ValueError, "unsupported platform"):
            where_clause("All channels", "Desktop")

    def test_summary_contains_every_filter_combination(self):
        connection = self.connection_with_rows()
        summary = build_summary(connection)
        self.assertEqual(len(summary["segments"]), 24)
        self.assertIn("Referral|iOS", summary["segments"])
        connection.close()

    def test_experiment_statistics_are_bounded(self):
        connection = self.connection_with_rows()
        experiment = analyze_segment(connection, "All channels", "All platforms")["experiment"]
        self.assertGreaterEqual(experiment["p_value"], 0)
        self.assertLessEqual(experiment["p_value"], 1)
        self.assertGreater(experiment["treatment_rate"], experiment["control_rate"])
        connection.close()

    def test_summary_is_json_serializable(self):
        connection = self.connection_with_rows(1_000)
        payload = json.dumps(build_summary(connection))
        self.assertIn("activation_rate", payload)
        connection.close()


if __name__ == "__main__":
    unittest.main()
