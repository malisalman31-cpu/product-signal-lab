PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS user_journeys (
    user_id INTEGER PRIMARY KEY,
    cohort_week INTEGER NOT NULL CHECK (cohort_week BETWEEN 0 AND 11),
    acquisition_channel TEXT NOT NULL CHECK (
        acquisition_channel IN ('Organic', 'Paid Search', 'Social', 'Referral', 'Partnership')
    ),
    platform TEXT NOT NULL CHECK (platform IN ('Web', 'iOS', 'Android')),
    experiment_variant TEXT NOT NULL CHECK (experiment_variant IN ('A', 'B')),
    completed_onboarding INTEGER NOT NULL CHECK (completed_onboarding IN (0, 1)),
    activated INTEGER NOT NULL CHECK (activated IN (0, 1)),
    subscribed INTEGER NOT NULL CHECK (subscribed IN (0, 1)),
    retained_w1 INTEGER NOT NULL CHECK (retained_w1 IN (0, 1)),
    retained_w2 INTEGER NOT NULL CHECK (retained_w2 IN (0, 1)),
    retained_w3 INTEGER NOT NULL CHECK (retained_w3 IN (0, 1)),
    retained_w4 INTEGER NOT NULL CHECK (retained_w4 IN (0, 1)),
    retained_w5 INTEGER NOT NULL CHECK (retained_w5 IN (0, 1)),
    retained_w6 INTEGER NOT NULL CHECK (retained_w6 IN (0, 1)),
    revenue_90d REAL NOT NULL CHECK (revenue_90d >= 0)
);

CREATE INDEX IF NOT EXISTS idx_journeys_channel_platform
ON user_journeys(acquisition_channel, platform);

CREATE INDEX IF NOT EXISTS idx_journeys_variant
ON user_journeys(experiment_variant);

CREATE INDEX IF NOT EXISTS idx_journeys_cohort
ON user_journeys(cohort_week);

PRAGMA optimize;
