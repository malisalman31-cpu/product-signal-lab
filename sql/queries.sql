-- Funnel: every stage uses the same user denominator.
SELECT
    COUNT(*) AS signed_up,
    SUM(completed_onboarding) AS completed_onboarding,
    SUM(activated) AS activated,
    SUM(subscribed) AS subscribed
FROM user_journeys
WHERE (:channel = 'All channels' OR acquisition_channel = :channel)
  AND (:platform = 'All platforms' OR platform = :platform);

-- Weekly retention cohorts.
SELECT
    cohort_week,
    COUNT(*) AS users,
    AVG(retained_w1) AS week_1,
    AVG(retained_w2) AS week_2,
    AVG(retained_w3) AS week_3,
    AVG(retained_w4) AS week_4,
    AVG(retained_w5) AS week_5,
    AVG(retained_w6) AS week_6
FROM user_journeys
WHERE (:channel = 'All channels' OR acquisition_channel = :channel)
  AND (:platform = 'All platforms' OR platform = :platform)
GROUP BY cohort_week
ORDER BY cohort_week;

-- Experiment readout by assignment.
SELECT
    experiment_variant,
    COUNT(*) AS users,
    SUM(activated) AS activations,
    AVG(activated) AS activation_rate,
    AVG(retained_w4) AS week_4_retention
FROM user_journeys
WHERE (:channel = 'All channels' OR acquisition_channel = :channel)
  AND (:platform = 'All platforms' OR platform = :platform)
GROUP BY experiment_variant
ORDER BY experiment_variant;
