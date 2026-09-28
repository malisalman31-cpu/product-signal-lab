import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SiteContractTests(unittest.TestCase):
    def test_dashboard_has_accessible_analysis_controls(self):
        html = (ROOT / "dist" / "index.html").read_text(encoding="utf-8")
        for expected in (
            'id="channel-filter"',
            'id="platform-filter"',
            'id="export-button"',
            'id="retention-table"',
            'aria-live="polite"',
        ):
            self.assertIn(expected, html)

    def test_dashboard_uses_local_assets(self):
        html = (ROOT / "dist" / "index.html").read_text(encoding="utf-8")
        self.assertIn('src="./app.js"', html)
        self.assertIn('href="./styles.css"', html)
        self.assertNotIn("https://cdn.", html)

    def test_hosting_manifest_targets_static_output(self):
        manifest = json.loads((ROOT / ".openai" / "hosting.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["static"]["directory"], "dist")


if __name__ == "__main__":
    unittest.main()
