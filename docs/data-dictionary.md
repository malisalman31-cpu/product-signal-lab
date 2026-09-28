# Data dictionary

The checked-in dataset is synthetic and deterministic. It is designed to demonstrate analysis techniques without exposing real customer information.

| Field | Type | Definition |
| --- | --- | --- |
| user_id | integer | Unique simulated user identifier |
| cohort_week | integer | Signup week from 0 through 11 |
| acquisition_channel | text | Organic, Paid Search, Social, Referral, or Partnership |
| platform | text | Web, iOS, or Android |
| experiment_variant | text | Randomized control A or treatment B |
| completed_onboarding | boolean integer | User completed onboarding |
| activated | boolean integer | User reached the activation event after onboarding |
| subscribed | boolean integer | Activated user purchased a subscription |
| retained_w1 to retained_w6 | boolean integer | User was active in the indicated week |
| revenue_90d | real | Simulated revenue during the first 90 days |

Funnel stages are intentionally ordered: a user cannot activate without onboarding or subscribe without activation. The pipeline validates those invariants before exporting results.
