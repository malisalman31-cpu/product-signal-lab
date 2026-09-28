# Product Signal Lab

Product Signal Lab is a working product-analytics portfolio project built around Python and SQL. It converts 30,000 deterministic synthetic SaaS user journeys into an interactive funnel, retention cohort table, and A/B experiment decision.

**Live site:** https://product-signal-lab.workspace-016092.chatgpt.site

## Why this project exists

The project demonstrates the analysis work expected in product analyst, data analyst, data scientist, and data-informed product roles:

- define a trustworthy event and user schema;
- validate funnel ordering and data quality;
- write indexed SQL for segment, funnel, cohort, and experiment analysis;
- measure activation, conversion, retention, and revenue;
- calculate a two-proportion z-test and 95% confidence interval; and
- translate statistical output into a clear ship-or-hold decision.

All data is synthetic. No customer or applicant information is included.

## Architecture

- `analysis/pipeline.py` generates seeded user journeys, builds SQLite, validates query plans, computes experiment statistics, and exports the dashboard cube.
- `sql/schema.sql` defines constraints and three indexes based on real query patterns.
- `sql/queries.sql` contains readable funnel, retention, and experiment queries.
- `dist/data/summary.json` contains 24 precomputed channel and platform segments.
- `dist/app.js` powers the visible filters, cohort heatmap, CSV export, and decision card.
- `dist/webmcp.js` exposes the same analysis actions to compatible browser agents.

## Run locally

```bash
python3 analysis/pipeline.py
python3 -m http.server 4182 --directory dist --bind 127.0.0.1
```

Open http://127.0.0.1:4182.

## Test

```bash
python3 analysis/pipeline.py --check --output /tmp/product-signal-summary.json
python3 -m unittest discover -s tests -p 'test_*.py'
node --check dist/app.js
node --check dist/webmcp.js
node --test tests/*.test.js
```

The pipeline tests deterministic generation, schema constraints, indexed query plans, funnel ordering, filter combinations, experiment bounds, and JSON output. GitHub Actions repeats the full suite on every push and pull request.

## Analysis boundaries

The dataset is a deterministic simulation for portfolio demonstration. The experiment effect and user behavior are intentionally generated, so findings should not be interpreted as evidence about a real product or population.

## License

MIT
