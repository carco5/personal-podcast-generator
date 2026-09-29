"""Dashboard metrics, computed in SQL from the same tables the product writes."""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.catalog import CATALOG
from app.config import Settings
from app.pipeline.voice import VOICE_MODEL
from app.schemas import (
    Activation,
    Cohort,
    Delivery,
    Depth,
    DropOffPoint,
    EpisodeCost,
    FailureRow,
    Funnel,
    OperationsMetrics,
    Outcomes,
    ProductMetrics,
    RunRow,
    Spend,
    StageRow,
    TopicRow,
    VoiceMonth,
    WeekPoint,
)
from app.worker import BUDGET_EXCEEDED, spent_in_window

SLOT_SECONDS = 15
STREAM_SECONDS = 60
ENGAGED_SHARE = 0.4
WEEKS = 8
WINDOW = timedelta(days=28)
SETTLE = timedelta(days=1)
RECENT_RUNS = 20
STAGE_ORDER = ["fetch", "select", "write", "check", "voice", "master"]

EPISODES = """
WITH eps AS (
    SELECT e.*, u.created_at AS joined_at, u.is_synthetic
    FROM episodes e JOIN users u ON u.id = e.user_id
    WHERE :simulated OR NOT u.is_synthetic
)
"""
LISTENS = (
    EPISODES
    + """
, slots AS (
    SELECT le.episode_id, floor(le.position_seconds / :slot)::int AS slot,
           min(le.created_at) AS heard_at
    FROM listen_events le JOIN eps ON eps.id = le.episode_id
    WHERE le.kind = 'heartbeat'
    GROUP BY 1, 2
),
running AS (
    SELECT s.episode_id, s.heard_at, eps.duration_seconds,
           sum(greatest(0, least(:slot, eps.duration_seconds - s.slot * :slot)))
               OVER (PARTITION BY s.episode_id ORDER BY s.heard_at, s.slot) AS heard
    FROM slots s JOIN eps ON eps.id = s.episode_id
),
listens AS (
    SELECT eps.id, eps.user_id, eps.joined_at, eps.finished_at, eps.duration_seconds,
           eps.chapters, p.played_at, coalesce(r.heard_seconds, 0) AS heard_seconds,
           r.streamed_at, r.engaged_at
    FROM eps
    LEFT JOIN (
        SELECT episode_id, min(created_at) AS played_at FROM listen_events GROUP BY episode_id
    ) p ON p.episode_id = eps.id
    LEFT JOIN (
        SELECT episode_id, max(heard) AS heard_seconds,
               min(heard_at) FILTER (WHERE heard >= :stream) AS streamed_at,
               min(heard_at) FILTER (WHERE heard >= :engaged * duration_seconds) AS engaged_at
        FROM running GROUP BY episode_id
    ) r ON r.episode_id = eps.id
    WHERE eps.status = 'completed'
)
"""
)

WEEKLY = """
SELECT w.week_start, count(l.id) AS engaged_listens, count(DISTINCT l.user_id) AS engaged_listeners
FROM generate_series(
    date_trunc('week', CAST(:now AS timestamptz), 'UTC') - (:weeks - 1) * interval '1 week',
    date_trunc('week', CAST(:now AS timestamptz), 'UTC'),
    interval '1 week'
) AS w(week_start)
LEFT JOIN listens l
    ON l.engaged_at >= w.week_start AND l.engaged_at < w.week_start + interval '1 week'
GROUP BY w.week_start
ORDER BY w.week_start
"""

FUNNEL = """
SELECT count(*) AS generated, count(played_at) AS played, count(streamed_at) AS streamed,
       count(engaged_at) AS engaged,
       coalesce(avg(least(heard_seconds / duration_seconds, 1))
                FILTER (WHERE played_at IS NOT NULL), 0) AS average_share_heard
FROM listens
WHERE finished_at >= :since AND finished_at < :until
"""

ACTIVATION = """
SELECT count(*) AS new_listeners,
       count(*) FILTER (WHERE engaged_at < finished_at + interval '1 day') AS activated
FROM (SELECT DISTINCT ON (user_id) * FROM listens ORDER BY user_id, finished_at) AS firsts
WHERE finished_at >= :since AND finished_at < :until
"""

DROP_OFF = """
SELECT d.share AS share_of_episode,
       count(*) FILTER (WHERE EXISTS (
           SELECT 1 FROM slots s
           WHERE s.episode_id = l.id AND s.slot = floor(d.share * l.duration_seconds / :slot)
       )) AS listening
FROM listens l CROSS JOIN (SELECT generate_series(0, 90, 10) / 100.0 AS share) AS d
WHERE l.played_at IS NOT NULL AND l.finished_at >= :since AND l.finished_at < :until
GROUP BY d.share
ORDER BY d.share
"""

TOPICS = """
, sections AS (
    SELECT l.id AS episode_id, c.value ->> 'key' AS topic,
           CASE WHEN c.n = 1 THEN 0 ELSE (c.value ->> 'start')::float END AS starts,
           coalesce(lead((c.value ->> 'start')::float) OVER (PARTITION BY l.id ORDER BY c.n),
                    l.duration_seconds) AS ends
    FROM listens l
    CROSS JOIN LATERAL jsonb_array_elements(l.chapters) WITH ORDINALITY AS c(value, n)
    WHERE l.played_at IS NOT NULL AND l.finished_at >= :since AND l.finished_at < :until
)
SELECT sec.topic, count(*) AS episodes,
       count(first_slot.slot) AS started,
       count(*) FILTER (WHERE first_slot.slot IS NOT NULL AND last_slot.slot IS NOT NULL)
           AS finished
FROM sections sec
LEFT JOIN slots first_slot
    ON first_slot.episode_id = sec.episode_id AND first_slot.slot = ceil(sec.starts / :slot)
LEFT JOIN slots last_slot
    ON last_slot.episode_id = sec.episode_id AND last_slot.slot = ceil(sec.ends / :slot) - 1
WHERE sec.topic NOT IN ('intro', 'closing')
  AND ceil(sec.starts / :slot) <= ceil(sec.ends / :slot) - 1
GROUP BY sec.topic
ORDER BY sec.topic
"""

COHORTS = """
SELECT date_trunc('week', u.created_at, 'UTC') AS week_start, count(*) AS listeners,
       count(*) FILTER (WHERE u.created_at + interval '7 days' <= :now) AS week1_eligible,
       count(*) FILTER (WHERE u.created_at + interval '7 days' <= :now AND EXISTS (
           SELECT 1 FROM listens l WHERE l.user_id = u.id
           AND l.engaged_at >= u.created_at AND l.engaged_at < u.created_at + interval '7 days'
       )) AS week1_retained,
       count(*) FILTER (WHERE u.created_at + interval '28 days' <= :now) AS week4_eligible,
       count(*) FILTER (WHERE u.created_at + interval '28 days' <= :now AND EXISTS (
           SELECT 1 FROM listens l WHERE l.user_id = u.id
           AND l.engaged_at >= u.created_at + interval '21 days'
           AND l.engaged_at < u.created_at + interval '28 days'
       )) AS week4_retained
FROM users u
WHERE (:simulated OR NOT u.is_synthetic)
  AND u.created_at >= date_trunc('week', CAST(:now AS timestamptz), 'UTC')
                      - (:weeks - 1) * interval '1 week'
GROUP BY 1
ORDER BY 1
"""

DELIVERY = """
SELECT count(*) AS due,
       count(*) FILTER (WHERE status = 'completed' AND finished_at <= scheduled_for) AS on_time
FROM eps
WHERE trigger = 'scheduled' AND status IN ('completed', 'failed')
  AND scheduled_for >= :window_start AND scheduled_for <= :now
"""


def product_metrics(session: Session, now: datetime, include_simulated: bool) -> ProductMetrics:
    params = {
        "simulated": include_simulated,
        "now": now,
        "slot": SLOT_SECONDS,
        "stream": STREAM_SECONDS,
        "engaged": ENGAGED_SHARE,
        "weeks": WEEKS,
        "since": now - WINDOW,
        "until": now - SETTLE,
        "window_start": now - WINDOW,
    }

    def rows(query: str) -> list[dict[str, Any]]:
        return [dict(row._mapping) for row in session.execute(text(LISTENS + query), params)]

    funnel = rows(FUNNEL)[0]
    average = funnel.pop("average_share_heard")
    topics = [
        TopicRow(
            **row, name=CATALOG[row["topic"]].name if row["topic"] in CATALOG else row["topic"]
        )
        for row in rows(TOPICS)
    ]
    simulated = session.scalar(text("SELECT count(*) FROM users WHERE is_synthetic"))
    return ProductMetrics(
        include_simulated=include_simulated,
        simulated_listeners=simulated,
        weeks=[WeekPoint(**row) for row in rows(WEEKLY)],
        funnel=Funnel(since=params["since"], until=params["until"], **funnel),
        activation=Activation(**rows(ACTIVATION)[0]),
        depth=Depth(
            played=funnel["played"],
            average_share_heard=float(average),
            drop_off=[DropOffPoint(**row) for row in rows(DROP_OFF)],
        ),
        topics=topics,
        cohorts=[Cohort(**row) for row in rows(COHORTS)],
        delivery=Delivery(**rows(DELIVERY)[0]),
    )


OUTCOMES = """
SELECT count(*) FILTER (WHERE status = 'completed') AS completed,
       count(*) FILTER (WHERE status = 'skipped') AS skipped,
       count(*) FILTER (WHERE status = 'failed' AND status_reason NOT LIKE :capped) AS failed,
       count(*) FILTER (WHERE status = 'failed' AND status_reason LIKE :capped) AS capped
FROM eps
WHERE created_at >= :since
"""

COSTS = """
, costs AS (
    SELECT sr.episode_id, pc.provider, sum(pc.cost_usd) AS cost
    FROM provider_calls pc JOIN stage_runs sr ON sr.id = pc.stage_run_id
    GROUP BY 1, 2
)
SELECT count(DISTINCT eps.id) AS completed,
       coalesce(sum(c.cost) FILTER (WHERE c.provider = 'openai'), 0) AS openai_usd,
       coalesce(sum(c.cost) FILTER (WHERE c.provider = 'elevenlabs'), 0) AS elevenlabs_usd
FROM eps LEFT JOIN costs c ON c.episode_id = eps.id
WHERE eps.status = 'completed' AND eps.created_at >= :since
  AND EXISTS (SELECT 1 FROM stage_runs sr WHERE sr.episode_id = eps.id)
"""

VOICE_MONTH = """
SELECT
    (SELECT coalesce(sum(pc.characters), 0)
     FROM provider_calls pc
     JOIN stage_runs sr ON sr.id = pc.stage_run_id JOIN eps ON eps.id = sr.episode_id
     WHERE pc.provider = 'elevenlabs' AND pc.created_at >= :month_start) AS billed_characters,
    (SELECT coalesce(sum((sr.details ->> 'reused_characters')::int), 0)
     FROM stage_runs sr JOIN eps ON eps.id = sr.episode_id
     WHERE sr.stage = 'voice' AND sr.status = 'completed' AND sr.details ->> 'voice' = :voice
       AND sr.finished_at >= :month_start) AS reused_characters
"""

STAGES = """
, stage_costs AS (
    SELECT stage_run_id, sum(cost_usd) AS cost FROM provider_calls GROUP BY stage_run_id
)
SELECT sr.stage, count(*) AS runs, count(*) FILTER (WHERE sr.status = 'failed') AS failed,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM sr.finished_at - sr.started_at))
           FILTER (WHERE sr.status = 'completed') AS p50_seconds,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY extract(epoch FROM sr.finished_at - sr.started_at))
           FILTER (WHERE sr.status = 'completed') AS p95_seconds,
       coalesce(sum(c.cost), 0) AS cost_usd
FROM stage_runs sr
JOIN eps ON eps.id = sr.episode_id
LEFT JOIN stage_costs c ON c.stage_run_id = sr.id
WHERE sr.started_at >= :since AND sr.status <> 'in_progress'
GROUP BY sr.stage
"""

FAILURES = """
SELECT CASE WHEN status_reason LIKE :capped THEN 'spending cap'
            ELSE split_part(status_reason, ':', 1) END AS category,
       count(*) AS count,
       (array_agg(status_reason ORDER BY finished_at DESC NULLS LAST))[1] AS latest
FROM eps
WHERE status = 'failed' AND created_at >= :since
GROUP BY 1
ORDER BY 2 DESC, 1
"""

RUNS = """
SELECT eps.id, eps.is_synthetic AS simulated, eps.trigger, eps.status, eps.status_reason,
       eps.scheduled_for, eps.finished_at,
       (SELECT coalesce(sum(pc.cost_usd), 0) FROM provider_calls pc
        JOIN stage_runs sr ON sr.id = pc.stage_run_id WHERE sr.episode_id = eps.id) AS cost_usd,
       (SELECT coalesce(jsonb_agg(jsonb_build_object(
                   'stage', sr.stage, 'status', sr.status,
                   'seconds', extract(epoch FROM sr.finished_at - sr.started_at)
               ) ORDER BY sr.id), '[]')
        FROM stage_runs sr WHERE sr.episode_id = eps.id AND sr.attempt = eps.attempts) AS stages
FROM eps
ORDER BY eps.created_at DESC, eps.id DESC
LIMIT :limit
"""


def operations_metrics(
    session: Session, now: datetime, include_simulated: bool, config: Settings
) -> OperationsMetrics:
    params = {
        "simulated": include_simulated,
        "since": now - WINDOW,
        "capped": f"{BUDGET_EXCEEDED}%",
        "month_start": now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
        "voice": VOICE_MODEL,
        "limit": RECENT_RUNS,
    }

    def rows(query: str) -> list[dict[str, Any]]:
        return [dict(row._mapping) for row in session.execute(text(EPISODES + query), params)]

    stages = {row["stage"]: StageRow(**row) for row in rows(STAGES)}
    return OperationsMetrics(
        include_simulated=include_simulated,
        since=params["since"],
        outcomes=Outcomes(**rows(OUTCOMES)[0]),
        cost=EpisodeCost(**rows(COSTS)[0]),
        spend=Spend(
            last_24h_usd=float(spent_in_window(session, now)),
            daily_cap_usd=float(config.worker_daily_budget_usd),
        ),
        voice_month=VoiceMonth(month_start=params["month_start"], **rows(VOICE_MONTH)[0]),
        stages=[stages[name] for name in STAGE_ORDER if name in stages],
        failures=[FailureRow(**row) for row in rows(FAILURES)],
        runs=[RunRow(**row) for row in rows(RUNS)],
    )
