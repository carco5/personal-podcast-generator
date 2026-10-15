# Architecture decisions

Each record has a status, a date, the context, the decision, the alternatives considered, the
trade-offs and the evidence behind it. Records are never deleted: if a decision changes, a new
record supersedes the old one and both stay here.

| # | Decision | Status |
|---|---|---|
| D1 | [Stack: FastAPI + PostgreSQL + React/TypeScript](#d1--stack-fastapi--postgresql--reacttypescript) | Accepted, revised in Step 8 |
| D2 | [The `episodes` table is the job queue, drained by one worker](#d2--the-episodes-table-is-the-job-queue-drained-by-one-worker) | Accepted, built in Step 6 |
| D3 | [A staged pipeline with checkpoints, using the provider SDKs directly](#d3--a-staged-pipeline-with-checkpoints-using-the-provider-sdks-directly) | Accepted |
| D4 | [News sources behind a `NewsProvider` interface](#d4--news-sources-behind-a-newsprovider-interface) | Accepted |
| D5 | [One OpenAI model per task](#d5--one-openai-model-per-task) | Accepted |
| D6 | [Voice: ElevenLabs v3 text-to-dialogue](#d6--voice-elevenlabs-v3-text-to-dialogue) | Accepted, validated in Step 3 |
| D7 | [Check the script before paying for voice](#d7--check-the-script-before-paying-for-voice) | Accepted |
| D8 | [Internal dashboard: product and operations](#d8--internal-dashboard-product-and-operations) | Accepted, refined in Step 8, built in Step 9 |
| D9 | [Frontend: a single-page app served by FastAPI](#d9--frontend-a-single-page-app-served-by-fastapi) | Accepted, built in Step 8 |
| D10 | [Runs locally with Docker Compose, including without API keys](#d10--runs-locally-with-docker-compose-including-without-api-keys) | Accepted, revised in Step 6 |
| D11 | [Cost-aware development](#d11--cost-aware-development) | Accepted |
| D12 | [Consistent REST conventions](#d12--consistent-rest-conventions) | Accepted |
| D13 | [Two fixed, configurable hosts](#d13--two-fixed-configurable-hosts) | Accepted |
| D14 | [Record the sample episode before building the web app](#d14--record-the-sample-episode-before-building-the-web-app) | Accepted, revised in Step 7 |
| D15 | [Repository layout, Python version and tooling](#d15--repository-layout-python-version-and-tooling) | Accepted |
| D16 | [Configuration and secrets](#d16--configuration-and-secrets) | Accepted |
| D17 | [PostgreSQL 18 in Compose](#d17--postgresql-18-in-compose) | Accepted |
| D18 | [Measure with a throwaway spike before building the pipeline](#d18--measure-with-a-throwaway-spike-before-building-the-pipeline) | Accepted |
| D19 | [An episode is shorter rather than padded](#d19--an-episode-is-shorter-rather-than-padded) | Accepted, revised in Step 8 |
| D20 | [Every check is proven by a sabotage test, and the judge is measured](#d20--every-check-is-proven-by-a-sabotage-test-and-the-judge-is-measured) | Accepted, measured in Step 5 |
| D21 | [Episodes of 3, 5 or 7 minutes, and a 5-minute sample](#d21--episodes-of-3-5-or-7-minutes-and-a-5-minute-sample) | Accepted |
| D22 | [The episode follows the listener's priorities](#d22--the-episode-follows-the-listeners-priorities) | Accepted, revised in Step 8 |
| D23 | [What an episode covers: what is new, or a catch-up the first time](#d23--what-an-episode-covers-what-is-new-or-a-catch-up-the-first-time) | Accepted |
| D24 | [Sources are ingested on a schedule and stored](#d24--sources-are-ingested-on-a-schedule-and-stored) | Accepted, built in Step 5 |
| D25 | [The data model grows step by step, and PostgreSQL enforces it](#d25--the-data-model-grows-step-by-step-and-postgresql-enforces-it) | Accepted |
| D26 | [Migrations with Alembic, applied by a prestart job](#d26--migrations-with-alembic-applied-by-a-prestart-job) | Accepted |
| D27 | [API without login: one current-user dependency, and the database as the guard](#d27--api-without-login-one-current-user-dependency-and-the-database-as-the-guard) | Accepted, revised in Step 8 |
| D28 | [Tests run against a real PostgreSQL](#d28--tests-run-against-a-real-postgresql) | Accepted |
| D29 | [One backend Dockerfile with a cached dependency layer and two targets](#d29--one-backend-dockerfile-with-a-cached-dependency-layer-and-two-targets) | Accepted, revised in Steps 6 and 8 |
| D30 | [Sources are downloaded like a responsible crawler](#d30--sources-are-downloaded-like-a-responsible-crawler) | Accepted |
| D31 | [Official data is read from the data inside official pages](#d31--official-data-is-read-from-the-data-inside-official-pages) | Accepted |
| D32 | [The pipeline runs as recorded stages, behind small provider interfaces](#d32--the-pipeline-runs-as-recorded-stages-behind-small-provider-interfaces) | Accepted |
| D33 | [Official results carry the players, and code computes the gaps](#d33--official-results-carry-the-players-and-code-computes-the-gaps) | Accepted |
| D34 | [Days are spoken relative to the episode, and code writes the labels](#d34--days-are-spoken-relative-to-the-episode-and-code-writes-the-labels) | Accepted |
| D35 | [Speech normalisation before the voice, with a pronunciation dictionary](#d35--speech-normalisation-before-the-voice-with-a-pronunciation-dictionary) | Accepted |
| D36 | [The same story under two URLs is one source](#d36--the-same-story-under-two-urls-is-one-source) | Accepted |
| D37 | [An editorial plan before writing](#d37--an-editorial-plan-before-writing) | Accepted |
| D38 | [The show's format comes from the listener's interests](#d38--the-shows-format-comes-from-the-listeners-interests) | Accepted |
| D39 | [The writer turns the plan into a conversation between two fans](#d39--the-writer-turns-the-plan-into-a-conversation-between-two-fans) | Accepted, revised in Step 10 |
| D40 | [Style lint, length control and a record of every episode](#d40--style-lint-length-control-and-a-record-of-every-episode) | Accepted, known issue resolved in Step 9 |
| D41 | [Episodes can be regenerated as of a past moment](#d41--episodes-can-be-regenerated-as-of-a-past-moment) | Accepted |
| D42 | [The plan keeps the source's framing, and a rejected turn is repaired, not the episode](#d42--the-plan-keeps-the-sources-framing-and-a-rejected-turn-is-repaired-not-the-episode) | Accepted |
| D43 | [Code picks each section's next game, and results are told the way fans tell them](#d43--code-picks-each-sections-next-game-and-results-are-told-the-way-fans-tell-them) | Accepted |
| D44 | [Records keep their scope, sections are linked, and a script can be re-checked](#d44--records-keep-their-scope-sections-are-linked-and-a-script-can-be-re-checked) | Accepted |
| D45 | [The sample is the best episode the product generated, and it can be reproduced](#d45--the-sample-is-the-best-episode-the-product-generated-and-it-can-be-reproduced) | Accepted |
| D46 | [Audio: ElevenLabs MP3 at 128 kbps, mastered in one pass](#d46--audio-elevenlabs-mp3-at-128-kbps-mastered-in-one-pass) | Accepted |
| D47 | [The worker: one polling loop, a short claim and a graceful stop](#d47--the-worker-one-polling-loop-a-short-claim-and-a-graceful-stop) | Accepted |
| D48 | [When episodes are made, and how much they may spend](#d48--when-episodes-are-made-and-how-much-they-may-spend) | Accepted |
| D49 | [The web app is served by FastAPI from the same image](#d49--the-web-app-is-served-by-fastapi-from-the-same-image) | Accepted |
| D50 | [Two screens and a minimal custom player](#d50--two-screens-and-a-minimal-custom-player) | Accepted |
| D51 | [Barça football and basketball are two sections of the catalogue](#d51--barça-football-and-basketball-are-two-sections-of-the-catalogue) | Accepted |
| D52 | [Listening events: one heartbeat per 15-second slot actually played](#d52--listening-events-one-heartbeat-per-15-second-slot-actually-played) | Accepted |
| D53 | [A fresh install shows the sample episode, without keys](#d53--a-fresh-install-shows-the-sample-episode-without-keys) | Accepted |
| D54 | [Dashboard metrics are computed in SQL from one definition of a listen](#d54--dashboard-metrics-are-computed-in-sql-from-one-definition-of-a-listen) | Accepted |
| D55 | [Simulated data lives in the same tables, marked on the user](#d55--simulated-data-lives-in-the-same-tables-marked-on-the-user) | Accepted |
| D56 | [The internal dashboard: its own API and page, and retries for real runs only](#d56--the-internal-dashboard-its-own-api-and-page-and-retries-for-real-runs-only) | Accepted |

---

## D1 · Stack: FastAPI + PostgreSQL + React/TypeScript

**Status:** Accepted · **Date:** 2026-09-26 · **Revised:** 2026-09-29 (Step 8)

**Context.** The product needs a user-facing UI, a backend that pulls news and generates audio on
a schedule, and an internal dashboard. FastAPI and PostgreSQL are the backend stack I already use
at work; React with TypeScript is a common choice for a product UI.

**Decision.** Backend: FastAPI, SQLAlchemy 2 (synchronous sessions), Alembic, psycopg 3 and
Pydantic 2, with API schemas kept separate from database tables. Frontend: React 19, Vite,
TypeScript, Tailwind 4, shadcn/ui, TanStack Query, Recharts and React Router.

**Alternatives considered.**
- *Full-stack TypeScript (Next.js):* no need for server-side rendering, and the generation
  pipeline is Python work.
- *Streamlit:* fast to build, but it produces an internal tool, not a product UI.
- *SQLModel:* still 0.x, and it makes the API contract depend on the table definitions.

**Trade-offs.** Synchronous sessions handle less concurrency than async ones. The load here is
tiny, and FastAPI runs plain `def` endpoints in a thread pool.

**Evidence.** PyPI (SQLModel 0.0.47, SQLAlchemy 2.1). The FastAPI SQL tutorial points to Alembic for
production migrations.

**Revised on 2026-09-29 (Step 8).** The web app uses shadcn/ui on Base UI (the CLI's current
default style), React Router 8 in declarative mode, and Vitest only for the listening counter;
type checking, ESLint, Prettier and the build cover the rest. See D49 and D50.

---

## D2 · The `episodes` table is the job queue, drained by one worker

**Status:** Accepted · **Date:** 2026-09-26 · **Revised:** 2026-09-27

**Context.** Episodes are generated on a per-user schedule. A generation takes minutes and calls
paid APIs, so it must survive restarts and must never run twice for the same slot.

**Decision.** There is no separate jobs table. An episode row carries `status` (`queued` →
`in_progress` → `completed` / `failed` / `skipped`), `scheduled_for` and `attempts`, and
`UNIQUE(user_id, scheduled_for)` prevents duplicates. A partial unique index allows at most one
`queued` or `in_progress` episode per user. `skipped` means there was no fresh material (D19). One worker loops over three tasks: every
three hours it ingests the catalogue sources (D24); it schedules due episodes (`INSERT … ON
CONFLICT DO NOTHING`); and it claims one queued episode and runs the pipeline. Claiming uses `SELECT … FOR UPDATE SKIP LOCKED`, so more workers can be added
without two of them taking the same episode.

**Alternatives considered.**
- *APScheduler inside the API process:* its state lives in memory, so it is lost on restart and
  duplicated when there are several API replicas.
- *Celery + Redis:* one more service to run and explain, for a single job type.
- *Temporal:* built for long, multi-step workflows across services; far more than one job type
  needs.
- *Procrastinate:* the same idea, on PostgreSQL, as a library. It is the natural next step at
  scale, but here it adds a dependency for one job type.
- *A generic `jobs` table:* there is only one kind of job, so it would duplicate the episode's
  state.

**Trade-offs.** No priorities and no sophisticated retry backoff. Polling adds a few seconds of
latency before a queued episode starts.

**Evidence.** PostgreSQL documentation on `SKIP LOCKED`: it "can be used to avoid lock contention
with multiple consumers accessing a queue-like table"
([docs](https://www.postgresql.org/docs/current/sql-select.html#SQL-FOR-UPDATE-SHARE)).
Revised on 2026-09-27 to add the ingest task (D24), and in Step 4 to add the `skipped` status
and the one-in-flight index (D25). Built in Step 6 (2026-09-29): the claim is the `SELECT … FOR
UPDATE SKIP LOCKED` plus the pipeline's first commit, which marks the episode `in_progress` and
releases the lock. How the worker runs and stops is in D47; when it schedules and how much it may
spend, in D48.

---

## D3 · A staged pipeline with checkpoints, using the provider SDKs directly

**Status:** Accepted · **Date:** 2026-09-26

**Context.** Generating an episode involves fetching news, choosing stories, writing a script,
voicing it and mastering the audio. Voice is by far the most expensive step.

**Decision.** Six stages: fetch → select → write → check → voice → master. Each stage persists
its output, so a retry restarts from the stage that failed. The OpenAI and ElevenLabs SDKs are
called directly.

**Alternatives considered.**
- *A single prompt that does everything:* impossible to measure, debug or retry in parts.
- *LangChain:* an abstraction layer that is not needed for two providers and a linear flow.
- *ElevenLabs "Create Podcast" (GenFM):* script and audio in one call, but a black box for
  sources and factual accuracy.

**Trade-offs.** More code than a single prompt.

**Evidence.** ElevenLabs bills per character, which makes voice the dominant cost. Checking the
script before voicing it (D7) avoids paying for audio that will be thrown away. Sources:
ElevenLabs API pricing and the GenFM documentation. Built in Step 5 as described in D32: in a real
test on 2026-09-28, an episode that failed during its first attempt resumed on retry without
repeating the paid stages.

---

## D4 · News sources behind a `NewsProvider` interface

**Status:** Accepted · **Date:** 2026-09-26 · **Revised:** 2026-09-27, 2026-09-28 (Step 5)

**Context.** The brief asks the backend to pull news "from APIs or scraping outlets' websites".
Every fact in the script must be checkable against the text it came from, so sources must provide
full text, and a fact is only as reliable as its source.

**Decision.**

*Source rule.* Data (scores, statistics and standings) always comes from an official source.
Context and stories come from the official source when it allows access, and otherwise from a
reference outlet, cited in the episode notes and checked by the judge (D7). News aggregators are
never used.

*Providers*, all behind one interface:
- **RSS feeds and sitemaps**, with the article text taken from the feed (`content:encoded`) or
  extracted from the page with trafilatura;
- the **official EuroLeague API**: results, quarter-by-quarter scores, the one or two best
  players of each game by valuation (with points, rebounds and assists), the standings and the
  next round;
- the **Guardian Open Platform**, optional (it needs a free key), for any free-text topic.

Structured data is rendered as a plain-text source with its own id, like an article, so the checks
in D7 treat both in the same way. An article needs a minimum amount of extracted text to count as
a source, and a story covered by two outlets is kept once.

*Catalogue*, official sources first:

| Topic | Official source | Reference outlets |
|---|---|---|
| FC Barcelona (football and basketball) | fcbarcelona.com, English articles sitemap, first teams only | The league sources below, filtered by the team's names |
| EuroLeague | The EuroLeague API | Eurohoops, Sportando |
| Liga ACB | acb.com: its calendar (results and next round, D31) and its game reports and news, in Spanish (recent-news sitemap and news listing) | None needed |
| NBA | None reachable: nba.com returns HTTP 403 | ESPN, CBS Sports |
| Champions League | UEFA's match and standings data (results, standings and next matchday), and the uefa.com news sitemap | The Guardian (`football/championsleague`) |
| LaLiga | laliga.com's English pages: results, standings and next matchday (D31). Its English news is corporate, so stories come from the reference outlet | The Guardian (`football/laligafootball`) |

Free-text topics use keywords over the catalogue and, with a key, the Guardian. Every source is
downloaded as described in D30.

**Alternatives considered.**
- *Official sources only:* the NBA's and the EuroLeague's websites block automated access (HTTP
  403 and 429), so there would be no NBA block and no EuroLeague stories beyond the data.
- *acb.com's undocumented internal API:* the calendar page already carries the same data, which is
  read from the page instead (D31). The official game reports carry the players' figures.
- *Google News RSS:* its links end in a consent wall.
- *Bing News RSS:* returned 0 results when measured.
- *Yahoo Sports:* an aggregator of other outlets' stories.
- *GNews and NewsAPI free tiers:* snippets instead of full text, delays of 12–24 h, and limited to
  development use.
- *OpenAI web search:* about $0.01 per call on top of tokens, and it returns a model summary
  rather than the original text, so numbers cannot be checked against a source.
- *ESPN's scoreboard API for NBA results:* it answers, but it is undocumented and its `robots.txt`
  cannot be read (HTTP 403). NBA scores come from ESPN and CBS game stories instead; the API is
  future work.
- *EuroLeague play-by-play data for highlights:* turning events into "moments" needs its own
  logic. Highlights come from game stories, and quarter scores show comebacks; play-by-play is
  future work.

**Trade-offs.**
- Without a Guardian key, a free-text topic only gets what the catalogue sources contain.
- ACB sources are in Spanish, so the model writes English from Spanish text and the judge compares
  across languages, both with a glossary of the reports' terms (D7).
- The NBA has no reachable official source, so its block relies on reference outlets.
- Pages extracted from fcbarcelona.com include share-button labels that have to be filtered out.

**Evidence.** Own measurements on 2026-09-26: feed freshness, availability of full text, and
HTTP status for every candidate source. The official pages of each provider:
[Guardian Open Platform](https://open-platform.theguardian.com/access/) and the
[EuroLeague API](https://api-live.euroleague.net/swagger/index.html). Revised on 2026-09-27 after
an audit of official sources, all checked with our User-Agent:
- the EuroLeague API's per-game statistics and standings endpoints returned HTTP 200;
- acb.com's `robots.txt` allows every user agent. It published an official report for each of
  the 9 games of round 1, with scores and players' points and valuation: 8 in its recent-news
  sitemap and 1 only in its news listing, so the provider reads both;
- fcbarcelona.com allows our user agent. Its English sitemap had 10 articles from the last 24
  hours, on football and on basketball;
- uefa.com allows our user agent, but had no men's Champions League news during the international
  window;
- euroleaguebasketball.net returned 429 and nba.com 403, even for `robots.txt`; laliga.com's
  `robots.txt` disallows its news pages;
- ESPN's scoreboard API returned 200 with our User-Agent, but its `robots.txt` returned 403. The
  NBA preseason starts on 2026-10-03;
- three stories appeared in both Eurohoops and Sportando within 48 hours, hence the duplicate
  filter.

Revised on 2026-09-28, when the providers were built and every source was checked again:
- **laliga.com was wrongly recorded as disallowed.** Its `robots.txt` has `Allow: /en-GB/` and
  `Disallow: /en-*/*`, of equal length; under RFC 9309 the allow rule wins the tie. Its English
  pages are allowed and its Spanish ones are not (D30).
- fcbarcelona.com's articles sitemap lists only its 10 latest articles across 8 sections
  (women's football, handball, futsal…), so the provider keeps the first teams' paths.
- CBS Sports' NBA feed also carried NFL and college football stories, and ESPN's carried fantasy
  articles, so each feed keeps only its section's paths.
- acb.com's short team names are cut for its web layout ("Casademont Zgz"), so the full names are
  used.
- A first real ingest of all 12 sources took 27 seconds and stored about 110 items.
- **The Champions League had news but no data**, so a catch-up could not tell FC Barcelona's
  matchday-1 game. UEFA's own data services, `match.uefa.com` and `standings.uefa.com` (the ones
  uefa.com uses), answer without a key and are allowed by `robots.txt`. They returned the 144
  league-phase games, with Barcelona 5–1 Feyenoord on 9 September and Galatasaray–Barcelona on 13
  October, and the 36-team table. UEFA names the club "Barcelona", so team names in the data are
  matched exactly, never as text: "Barcelona" must not match "RCD Espanyol de Barcelona".
- uefa.com's news sitemap once listed the same article twice, so a batch is deduplicated by URL
  before it is saved (D24).

---

## D5 · One OpenAI model per task

**Status:** Accepted · **Date:** 2026-09-26 · **Revised:** 2026-09-27, 2026-09-28

**Context.** Three stages use a language model: selecting stories and checking the script's
claims (D7), which are classification tasks, and writing the script, where quality is audible.

**Decision.** `gpt-6-sol` writes the script, and `gpt-6-luna` selects the stories and checks the
claims. They are settings, not hard-coded values (D16): `OPENAI_WRITE_MODEL`,
`OPENAI_SELECT_MODEL` and, since Step 5, `OPENAI_JUDGE_MODEL`, so the judge can be measured or
changed without touching selection. `gpt-6-astra` is kept only as an option to try on the sample
episode. A model without a known price is refused before any call is made.

**Alternatives considered.**
- *`gpt-6-astra` for writing:* about five times the price of `gpt-6-sol`.
- *`gpt-5.6-sol`:* twice the price of `gpt-6-sol`.

**Trade-offs.** Some writing quality compared with `gpt-6-astra`.

**Evidence.** [OpenAI pricing](https://developers.openai.com/api/docs/pricing). The real cost
per episode is measured in the Step 3 spike and recorded per call (D11). Revised on 2026-09-27,
when the claim check became a required stage (D7). Prices checked again on 2026-09-28 (standard
processing, per million tokens: `gpt-6-sol` $2.00 input, $0.20 cached, $2.50 cache write, $10.00
output; `gpt-6-luna` $0.10, $0.01, $0.125 and $0.50). On the first real episodes: selection
cost about $0.001, the script $0.04 and the judge $0.002.

---

## D6 · Voice: ElevenLabs v3 text-to-dialogue

**Status:** Accepted, validated in Step 3 · **Date:** 2026-09-26, validated 2026-09-27 ·
**Revised:** 2026-09-28 (Step 5)

**Context.** The episode is a conversation between two hosts, and it has to sound natural.

**Decision.** `eleven_v3` text-to-dialogue with two voices. The script is sent in chunks of at
most 2,000 characters, cut at segment boundaries. The rule is one request per segment, which
also gives the start time of each segment for free. With ffmpeg, the chunks are joined
with a 0.4 s silence, with 0.5 s before the first word and 1 s after the last, and the episode
is normalised to -16 LUFS with a true-peak ceiling of -1.5 dB. During development: fake audio, a
cache keyed by the hash of the text, and very short v3 texts.

Free checks on the audio:
- each chunk must last close to what its characters predict (about 12.4 per second), so a chunk
  that stopped early is detected and requested again;
- a silent chunk fails;
- the finished episode must measure -16 LUFS within 1 dB, with a true peak no higher than
  -1 dBFS.

**Alternatives considered.**
- *Flash models:* half the price, but they do not support text-to-dialogue.
- *One TTS request per turn, stitched together:* more requests, and more joins that can be heard.
- *Chunks that span several segments, with the `with-timestamps` variant of the endpoint:* fewer
  requests, but the segment start times would depend on parsing character timings.
- *OpenAI TTS:* one voice per request, so it has the same stitching problem as the previous
  option. It is the natural fallback provider, kept as future work.
- *A second provider as fallback:* a second audio path that would have to be tested by ear.

**Trade-offs.** If ElevenLabs is down, the episode fails; it can be retried (D2). A fallback
voice provider is a future improvement.

**Evidence.** ElevenLabs
[text-to-dialogue documentation](https://elevenlabs.io/docs/overview/capabilities/text-to-dialogue):
the API uses the Eleven v3 model, and requests should stay at or under 2,000 characters "for
reliable generation". A 71-character test dialogue on
2026-09-26 confirmed the two voices. The Step 3 spike ([measurements](spike.md)) validated the
chunking:
- the joins between three requests sounded natural when listened to;
- v3 adds no silence at the start or end of a request, so the pauses at the joins are the ones
  we add; without the lead-in, the episode started abruptly;
- the three segments came out within 0.4 LU of each other, so there are no volume jumps;
- the finished file measured -16.4 LUFS with a true peak of -1.9 dBFS, within
  [Apple Podcasts' audio requirements](https://podcasters.apple.com/support/893-audio-requirements)
  (-16 LKFS with a tolerance of 1 dB, true peak no higher than -1 dBFS).

The audio checks were added on 2026-09-27 after a review of every check. The endpoint's
documentation warns that requests over 2,000 characters "can terminate early". Chunks stay under
that limit, and the duration check still catches a truncated chunk at no cost.

Built in Step 5 (2026-09-28), with these details fixed:
- a segment longer than 2,000 characters is split between turns, never inside one; its chapter
  starts with its first chunk;
- a chunk counts as cut short above 18.6 characters per second, 1.5 times the measured 12.4 (the
  spike measured 10.5 to 13.6), and as silent below −45 dB of mean volume. A bad chunk is
  requested once more, and a second failure fails the stage;
- scores become "89 to 82" just before the voice request;
- for development and tests, a tone voice generates, with ffmpeg, a tone as long as the speech
  would be, at no cost. Its model name is part of the cache key, so development audio is never
  served as real audio;
- tests with ffmpeg cover the cache, a cut-short chunk, a silent chunk, the final loudness and the
  chapter times.

---

## D7 · Check the script before paying for voice

**Status:** Accepted · **Date:** 2026-09-26 · **Revised:** 2026-09-27, 2026-09-28 (Step 5)

**Context.** The worst failure for a news podcast is a made-up fact: a score, a statistic, a
claim that no source supports, or a rumour told as a fact.

**Decision.** Two checks run before the voice stage.
- **In code (deterministic):**
  - every number in a turn appears in a source that the turn cites. Scores are compared as ordered
    pairs, so a reversed score is also caught. Numbers are normalised by the source's language, so
    a Spanish "81,5" matches an English "81.5";
  - every cited `source_id` exists among this episode's sources;
  - numbers written as words ("twenty points") are rejected, so the number check cannot be
    bypassed;
  - the text is clean for the voice: only the allowed audio tags, and no URLs, markdown or emojis,
    which v3 would read aloud;
  - each segment fits in one voice request (2,000 characters), and the script is not longer than
    its target.
- **An LLM judge (`gpt-6-luna`)** reads every turn with the sources it cites, each labelled with
  its publication date:
  - a turn without sources may only hold an opinion or a transition, so leaving `source_ids`
    empty does not skip the check;
  - a factual turn must be supported by its sources: not contradicted and not missing from them,
    with the right team or player, the right timing, and no more certainty than the source has
    ("reportedly" stays "reportedly").

If a check fails, the script is rewritten once with the reasons; a second failure marks the
episode `failed`, before any voice is paid for. Numbers are kept as digits in the script so they
can be checked, and are formatted for speech right before the voice stage. How the checks
themselves are tested is in D20.

**Alternatives considered.**
- *An LLM judge only:* it is non-deterministic and can miss what code catches for free, so it
  complements the code check instead of replacing it.
- *The code check only:* free, but an invented claim without numbers would reach the audio.
- *Token `logprobs` as a confidence signal:* `gpt-6-luna` rejects the parameter
  (`unsupported_parameter`).
- *HHEM, a local hallucination model:* it would add PyTorch to the image.
- *WER on the generated audio:* extra cost and time; the audio is checked by ear.

**Trade-offs.** The judge adds one model call, about $0.001 per episode at `gpt-6-luna` prices,
and it can be wrong. A false "not in the source" costs a rewrite, not wrong audio, and the sabotage
tests and the sample episode show how often it happens.

**Evidence.** In a previous project, an LLM agent evaluation suite, a deliberate sabotage of the
mock showed that a pricing grader was anchored on the `$` symbol, so it measured format, not
value. Sabotage tests are how I check that a check can actually fail.

Revised on 2026-09-27: the judge moved from an optional extra to a required check. Claims without
numbers were the one gap in the deterministic check, and closing it costs about $0.001 per episode.
A review of every check the same day found three more ways an unchecked claim could get through,
and closed them. A turn could leave `source_ids` empty, a number could be written as words, and a
rumour could lose its hedge. Headlines measured that day used "reportedly" and "Sources:". The
final review found that the ACB's Spanish reports write "81,5" and "1.706", so numbers are
normalised by language.

In the Step 3 spike, v3 read both "89–82" and "89 to 82" correctly in a single test. Scores
are still rewritten as "89 to 82": the result does not depend on the model's text
normalisation, and it costs 3 characters per score.

**Revised on 2026-09-28, when the checks were built (Step 5) and run on real episodes.**
- *Scores.* Outlets write home team first, so a score in the script must be written winner
  first (89–82, never 82–89) and the pair must appear in a cited source in either order. Who beat
  whom is left to the judge.
- *Numbers as words.* In the script, a number word is rejected only when it counts a statistic
  ("twenty points", "three straight wins"), so "the two teams" and "a three-pointer" pass. In a
  source, number words count as digits ("nueve rebotes" supports "9 rebounds"), except "one",
  "uno", "un" and "una", which are usually articles.
- *Structure and form.* Each segment cites only its own block's sources (the intro and the closing
  may cite any); the intro must cite the lead story; every planned story must be covered; turns
  stay under 500 characters; at most 6 audio tags from the allowed list; the script may not exceed
  the plan by more than 25%.
- *Order* (revised in Step 7). In the first round the code checks and the judge both run, so the
  single rewrite fixes every problem at once. In the second round the judge runs only if the code
  checks pass, because a failed code check fails the episode anyway. Until Step 7 the judge ran
  only after the code checks passed, to save its cost (about $0.002). In a sample test run
  (episode 13) that meant its findings arrived in the second round, with no rewrite left, and an
  episode worth about $0.08 failed.
- *The judge.* Every turn must get a verdict, and a missing one is a problem. Talk about the
  episode itself (the welcome, what it covers) counts as a transition. The episode context lists
  the date of every day from a week before to a week after, so nobody has to work out which date
  "Sunday" is.
- *Spanish sources.* The writer and the judge get the same glossary of the Liga ACB reports'
  terms: "val" is the valuation, not points; a "triple" is a three-pointer, not a triple-double,
  but "triple campeón" is a three-time champion; a "parcial" is a scoring run, not a final score.
- *Writing.* People are introduced by their team ("Barça's Kevin Punter"), or by a role only when a
  source states it, and games and fixtures are given with the weekday and the date.

Evidence from the real runs on 2026-09-28:
- In the 18 stored ACB reports, "val"/"valoración" appeared 24 times, "triple" 49 and "parcial" 18.
  A "23 val" told as "23 points" would pass the number check, since 23 is in the source: only the
  glossary and the judge prevent it.
- The first real episode failed in the check stage before any voice was paid for. The judge
  rightly flagged player positions that the writer had invented, which an instruction to put "the
  role before the name" had invited. It also raised two false alarms: the intro describing the
  episode, and a fixture "on Sunday" whose date it got wrong. Both were fixed with the changes
  above.
- The second real episode completed. The code checks caught one unsupported number, the rewrite
  fixed it, and the judge passed all 26 turns. Labelled by hand, turn by turn, by the author (a
  native Spanish speaker) against their sources, including the Spanish originals, all 26 were
  correct.
- One official ACB report contradicts itself: 8 rebounds and a valuation of 29 in its summary,
  "nueve rebotes" and 30 in its body. No check can settle which figure is right. The script may
  use either figure the official source states, and nothing outside it.

**Note on untrusted text (Step 10 review, 2026-09-30).** Source text is written by third parties
and goes into the prompts, so it could carry instructions (prompt injection). What limits it:
sources come from a fixed catalogue, never from a URL a listener provides; the rules go in the
model's `instructions` and the sources in its input, labelled as data (`[S3] …`); the models have
no tools and must answer in a JSON schema; and every factual turn is checked against its cited
sources, by code and by the judge. The listener's own texts (host names and personalities) go in
the instructions, but they only shape that listener's show. There is no dedicated test: an
injection test set and an explicit "sources are data" rule are future work.

---

## D8 · Internal dashboard: product and operations

**Status:** Accepted · **Date:** 2026-09-26 · **Revised:** 2026-09-29 (Step 8)

**Context.** The brief asks for "an internal dashboard that shows usage metrics to understand the
product's success", and allows mocked data.

**Decision.** Two tabs:
- **Product**, built around a North Star metric, *engaged listens per week*, plus its input
  metrics (breadth, depth, frequency, efficiency). Listening events are `play` plus a
  `heartbeat` every 15 s, and listening time counts distinct 15-second slots. The funnel is:
  generated → play → stream (≥ 60 s, Spotify's definition) → engaged (≥ 40 % of the episode,
  Apple's definition).
- **Operations**: cost per episode, pipeline success rate, latency per stage and ElevenLabs
  characters spent.

The data is synthetic and flagged as such. Real player events use the same tables.

**Alternatives considered.**
- *A flat list of charts with no hierarchy.*
- *Self-invented metric definitions:* harder to defend than industry ones.
- *An external BI tool (Metabase, Grafana):* one more service, and less of the product's own
  story.

**Trade-offs.** The product numbers are simulated, as the brief allows.

**Evidence.**
[Apple Podcasts listener analytics](https://podcasters.apple.com/support/5392-listener-analytics)
("engaged listeners": at least 20 minutes or 40 %). Spotify for Creators, "How we count
engagement metrics" (a stream is 60 seconds or more).
[Amplitude on North Star metrics](https://amplitude.com/blog/product-north-star-metric).

**Refined on 2026-09-29 (Step 8).** The listening events are defined in D52: one heartbeat per
15-second slot actually played, and simulated data marked on the user rather than on each event.

**Built on 2026-09-30 (Step 9)** as D54 (metrics), D55 (simulated data) and D56 (API and page).
Three changes from the Step 1 list, agreed with the owner:
- **Topics** are measured as section completion (of the played episodes that reached a section,
  how many heard it to the end) instead of engaged listens per topic: an episode covers several
  topics, so one engaged listen would add one to each, and the count would mostly reflect how many
  people follow each topic.
- **The voice budget** is the worker's daily dollar cap (D48) plus the month's billed and
  cache-reused ElevenLabs characters. The provider's quota for these keys is not known, so a
  "characters left" figure would be invented.
- **Cohorts** count only listeners who have lived the whole week being measured, and the funnel
  ends 24 hours ago, so recent episodes do not look unheard just because they are new.

---

## D9 · Frontend: a single-page app served by FastAPI

**Status:** Accepted · **Date:** 2026-09-26 · **Revised:** 2026-09-29 (Step 8)

**Context.** There are two audiences: listeners, who use the app, and the internal team, who use
the dashboard.

**Decision.** One SPA with two areas, `/` for users and `/internal` for the dashboard. In Docker,
FastAPI serves the built SPA, so there is one origin and no CORS. In development, the Vite dev
server proxies `/api` to FastAPI. TypeScript types are generated from FastAPI's OpenAPI document
with a one-off `npx openapi-typescript@7` run.

**Alternatives considered.**
- *Next.js:* server-side rendering is not needed.
- *A separate Vite container:* that would be a dev server running in production mode.
- *Hand-written types:* they drift silently when the API changes.

**Trade-offs.** No hot reload inside Docker; it is available with the Vite dev server.

**Evidence.** Vite and FastAPI documentation. `openapi-typescript` 7 declares a TypeScript 5 peer
dependency, while the Vite template uses TypeScript 6, so a one-off `npx` run avoids an install
conflict.

**Built on 2026-09-29 (Step 8), see D49.** FastAPI serves the build with `app.frontend()`, which
falls back to `index.html` only for browser navigations, and the image is built from the
repository root with an allowlist `.dockerignore`.

---

## D10 · Runs locally with Docker Compose, including without API keys

**Status:** Accepted · **Date:** 2026-09-26 · **Revised:** 2026-09-29 (Step 6)

**Context.** Reviewers must be able to run the project with one command, and the API keys are
private.

**Decision.** `docker compose up` starts the database, a one-off `prestart` job (migrations and the
demo user, D26) and the API. The worker is optional: it only starts with `--profile worker`,
because it spends provider credits (D47). The `.env` file is optional (`required: false`).
Without keys the app still loads with the sample episode, the simulated dashboard and the full UI.
Only "Generate" needs keys: `OPENAI_API_KEY`, plus `ELEVENLABS_API_KEY` when the worker uses the
real voice (D48). The API answers 503 and names the missing variables. The database port is not
published, and the API is published on `127.0.0.1` only, because it has no authentication and can
spend provider credits.

**Alternatives considered.** *A public deployment:* a public URL could spend the provider credits
without control.

**Trade-offs.** No URL to try the app without Docker. Deployment and authentication are future
work.

**Evidence.** Docker Compose documentation: since Compose 2.24.0, an `env_file` entry with
`required: false` is ignored when the file is missing. Revised in Step 4: the migration job became
`prestart`, and the API port is bound to localhost. Revised in Step 6: the worker moved behind a
Compose profile, and the voice key is only required for the real voice.

---

## D11 · Cost-aware development

**Status:** Accepted · **Date:** 2026-09-26 · **Revised:** 2026-09-28 (Step 5)

**Context.** The balance of the provided keys is not visible. The OpenAI costs endpoint returns
403, and the ElevenLabs key lacks the permission to read its quota.

**Decision.**
- Every provider call is recorded in `provider_calls`: model, tokens or characters, cost and
  latency. Cost comes from OpenAI's `usage` and ElevenLabs' `character-cost` response header.
- Tests use fake providers.
- Generated audio is cached by the hash of its text.

**Alternatives considered.** *Checking the providers' dashboards:* not possible with these keys.

**Trade-offs.** A few lines per provider call.

**Evidence.** Free, read-only checks on 2026-09-26. The same data also feeds the Operations tab
(D8).

Built in Step 5 (2026-09-28): every paid call is stored with its stage, including the calls of a
stage that then failed, since they were paid anyway. The cache key includes the voice model, so
free development audio is never served as real audio. Every paid run was estimated first with a
dry run on the real prompts. The text of a 5-minute episode was estimated at about $0.05 when the
script passes at once; the two real episodes, text only, needed one rewrite each and cost $0.082
and $0.084. The voice for 5 minutes adds about $0.37 (D21). The whole of Step 5 cost $0.17 in
OpenAI credits and nothing in ElevenLabs credits.

Extended in Step 6 (2026-09-29): the same `provider_calls` table sets the worker's spending cap
(D48), and the worker uses the free tone voice unless the real voice is enabled.

---

## D12 · Consistent REST conventions

**Status:** Accepted · **Date:** 2026-09-26

**Context.** Anyone who integrates with the API should find it predictable: one prefix, one way to
page through lists and one style of status values.

**Decision.**
- `/api/v1/` prefix and `GET /api/v1/health`, so a breaking change can ship as `/api/v2/`.
- `page` + `limit` pagination: `page` starts at 0, and a list answers
  `{"episodes": [...], "page_count": …, "next_page": … | null}`, so a client knows whether there
  is more to fetch.
- An endpoint to retry a failed episode.
- Episode status values `queued`, `in_progress`, `completed`, `failed` and `skipped`, in one
  consistent style. This is the job lifecycle of GitHub's Checks API (`queued`, `in_progress`,
  `completed`) plus `failed`, and `skipped`, which is one of that API's conclusions.

**Alternatives considered.**
- *Status values in other styles* (`In Progress`, `IN_PROGRESS`): common in public APIs, but one
  lowercase snake_case style matches the JSON field names and is easier to consume.
- *`page_size` instead of `limit`:* equally common; what matters is using one name everywhere.

**Trade-offs.** Offset pagination gets slower on deep pages. With tens of episodes per user this
does not matter; keyset pagination is the next step if lists grow.

**Evidence.** [GitHub Checks API](https://docs.github.com/en/rest/checks/runs): `status` is
`queued`, `in_progress` or `completed`.

---

## D13 · Two fixed, configurable hosts

**Status:** Accepted · **Date:** 2026-09-26

**Context.** Every podcast format and every voice has to be tested by ear, and each test spends
ElevenLabs characters.

**Decision.** Two hosts: a presenter, who drives the episode and gives the facts, and an analyst,
who adds context, opinion and questions. Users can change each host's name and personality. The
voices are George and Sarah, and their IDs are settings (D16).

**Alternatives considered.** *One to three hosts, chosen by the user:* each extra format needs its
own listening tests.

**Trade-offs.** Fewer choices for the user. Hosts are stored as a list, so more formats can be
added later.

**Evidence.** A voice test on 2026-09-26. The
[ElevenLabs voices documentation](https://elevenlabs.io/docs/overview/capabilities/voices) states
that default voices "will expire on December 31, 2026", which is why the voice IDs are
configuration and not code.

---

## D14 · Record the sample episode before building the web app

**Status:** Accepted · **Date:** 2026-09-26 · **Revised:** 2026-09-27, 2026-09-29 (Step 7)

**Context.** `sample.mp3` is the only deliverable that depends on something outside our control:
the ElevenLabs quota of a shared account whose limit is not visible.

**Decision.** Produce the sample in a single take in Step 7, once audio quality is right and
before the user app (Step 8) and the dashboard (Step 9).

The sample is a 5-minute episode (D21) built on my own interests: FC Barcelona first (football
and basketball), then the EuroLeague, the Liga ACB and the NBA (D22). As the listener's first
episode, it is a catch-up (D23), so it does not depend on the day it is recorded. It is recorded as
soon as Step 7 is ready, before the delivery in the week of 28 September, ideally on Thursday 1
October, the morning after EuroLeague round 2. The worker's ingest (D24) runs for at least a day
before the recording, so the store holds the latest news of every source.

**Alternatives considered.**
- *Record it at the end:* risks finding the quota exhausted.
- *Record several takes "just in case":* spends the quota for nothing.
- *Waiting for a particular round:* it would tie the delivery to the calendar. With the catch-up
  rule (D23), any day has enough material.
- *LaLiga and the Champions League as topics of the sample:* club football pauses for an
  international window until 6 October, and the next Champions League matchday is on 13/14
  October. Barça's football news still reaches the sample through the club's official site.

**Trade-offs.** None in the result; only the order of the steps changes.

**Evidence.** The key's character statistics endpoint shows other activity on the same account.
Revised on 2026-09-27 with the sample's content and date. The date moved into the delivery
week, once the catch-up rule removed the dependency on a round. Calendars used: the
EuroLeague API, the [Liga Endesa 2026-27 calendar](https://acb.com/docs/calendario/calendarioLigaEndesa202627.pdf)
and [UEFA's 2026/27 dates](https://www.uefa.com/uefachampionsleague/news/02a6-20d57cfcd03e-407c22a7f465-1000--2026-27-champions-league-teams-dates-draws-format-final/).

**Revised on 2026-09-29 (Step 7): what happened.** The sample was voiced on 29 September, as soon
as its text was right, not on 1 October: with the catch-up rule and `--as-of` (D41), every version
was generated as of the same moment, Monday 28 September at 23:32 in Madrid, so the recording day
no longer mattered. The ingest had been storing sources since 24 September. The order held: the
sample came before the web app. See D45.

---

## D15 · Repository layout, Python version and tooling

**Status:** Accepted · **Date:** 2026-09-27

**Context.** Reviewers should recognise the layout at a glance, and installs should be
repeatable on any machine.

**Decision.**
- **Layout:** `backend/` (`app/`, `tests/`, `pyproject.toml`) and `frontend/` (Step 8), with
  `compose.yaml`, `.env.example` and `docs/` at the root. This mirrors FastAPI's official
  full-stack template.
- **Python 3.14**, the same version locally and in the Docker image.
- **`pyproject.toml`** (PEP 621) built with hatchling.
- **Dependencies:**
  - direct dependencies are pinned exactly, and each one is added in the step whose code first
    uses it;
  - development tools (pytest, Ruff) live in a PEP 735 dependency group, not in an "extra".
- **Linting:** Ruff with its default rules plus import sorting (`I`), pyupgrade (`UP`) and
  bugbear (`B`).

**Alternatives considered.**
- *Flat layout at the root:* Python and Node files mixed together.
- *`requirements.txt`:* no single place for metadata and tool configuration.
- *uv with a lock file, or Poetry:* one more tool to install and explain.
- *Python 3.11 (already installed) or 3.13:* 3.11 only receives security fixes. 3.14 is what the
  official template requires, and the compiled dependencies we plan to use ship wheels for it.

**Trade-offs.** Transitive dependencies are not locked. A lock file is the next step if builds
must be bit-for-bit reproducible.

**Evidence.**
- [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template):
  `backend/` + `frontend/`, hatchling, `[dependency-groups]`, `requires-python >= 3.14`.
- PyPI: cp314 wheels for Windows, Linux x86-64 and Linux ARM64 exist for psycopg-binary, lxml,
  pydantic-core and rapidfuzz.
- [PEP 735](https://peps.python.org/pep-0735/).

---

## D16 · Configuration and secrets

**Status:** Accepted · **Date:** 2026-09-27 · **Revised:** 2026-09-27 (Step 4)

**Context.** The app must run without any API keys (D10), keys must never leak, and reviewers
need to know every setting that exists.

**Decision.**
- **One source of configuration:** a single `Settings` class (pydantic-settings) reads
  environment variables and the optional repo-level `.env`. Nothing else reads `os.environ`.
- **Keys:** they are optional and typed as `SecretStr`, which prints as `**********`.
- **Empty values count as missing** (`env_ignore_empty`), so a copied `.env.example` means "no
  key" instead of an empty key that fails with a 401.
- **Paths:** the `.env` path is resolved from the module file, so the result does not depend on
  the working directory.
- **Documented settings:** `.env.example` lists every setting with its default, and a test fails
  if the two drift apart.
- **What is configurable:** model names and voice IDs. The TTS model is not, because
  text-to-dialogue only exists on v3.
- **Database URL** (Step 4): also a `SecretStr`, because it contains a password. Its default is
  the development database on `127.0.0.1:5433` (D17); Compose sets the in-network URL for the
  containers.

**Alternatives considered.**
- *Reading `os.environ` wherever a value is needed:* scattered settings, and no types or
  validation.
- *Required keys that fail fast at startup:* this would break the no-keys demo mode.
- *A secrets manager:* only relevant once the app is deployed.

**Trade-offs.** A missing key surfaces when an episode is generated, not at startup. This is
intentional.

**Evidence.**
- [FastAPI settings guide](https://fastapi.tiangolo.com/advanced/settings/): pydantic-settings
  and an `lru_cache`d getter.
- The official template reads `../.env` with `env_ignore_empty=True`.
- `backend/tests/test_config.py`: each test was checked to fail when the behaviour it guards is
  broken on purpose.

---

## D17 · PostgreSQL 18 in Compose

**Status:** Accepted · **Date:** 2026-09-27 · **Revised:** 2026-09-27 (Step 4)

**Context.** The database must keep its data across restarts on any reviewer machine, and it must
not clash with a PostgreSQL the reviewer already runs.

**Decision.**
- **File:** `compose.yaml`, with no `version:` key.
- **Image:** `postgres:18`, pinned to the major version.
- **Data:** a named volume mounted at `/var/lib/postgresql`.
- **Health:** a `pg_isready` healthcheck, so that later services can wait with
  `depends_on: condition: service_healthy`.
- **Network:** the port is not published, and the credentials in the file are for local use only.

**Alternatives considered.**
- *`docker-compose.yml`:* supported only for backwards compatibility.
- *Mounting `/var/lib/postgresql/data`:* the usual path up to version 17. On 18 it leaves the data
  in an anonymous volume, so it is lost when the container is recreated.
- *Publishing 5432:* conflicts with a local PostgreSQL.
- *Required credentials from `.env`, as in the official template:* `docker compose up` would
  then fail without a `.env` file.

**Development access (Step 4).** `compose.dev.yaml` publishes the port on `127.0.0.1:5433`, only
when asked for: `docker compose -f compose.yaml -f compose.dev.yaml up -d`. A plain
`docker compose up` still publishes nothing. Port 5433 avoids a local PostgreSQL on 5432, and
`127.0.0.1` keeps it off the local network. The default URL uses `127.0.0.1`, not `localhost`: on
Windows, `localhost` tries IPv6 first, where the port is not published.
- *A `compose.override.yml`*, the official template's choice, was rejected: Compose loads it
  automatically, so reviewers would publish the port too.
- *Tests inside a container* were rejected: every change would need an image rebuild, and Alembic
  could not autogenerate from the host.

**Trade-offs.** Developers type two `-f` flags.

**Evidence.**
- Compose docs: `compose.yaml` is the preferred filename, and the `version` element is
  "obsolete".
- [PostgreSQL image docs](https://hub.docker.com/_/postgres): from 18, `PGDATA` is
  `/var/lib/postgresql/18/docker` and the volume is `/var/lib/postgresql`.
- Local check on 2026-09-27: `data_directory` is `/var/lib/postgresql/18/docker`, there is no
  anonymous volume, and a row survives `docker compose down` followed by `up`.
- Step 4 measurement: a connection to `localhost:5433` took 5.07 s and one to `127.0.0.1:5433`
  took 0.04 s.

---

## D18 · Measure with a throwaway spike before building the pipeline

**Status:** Accepted · **Date:** 2026-09-27

**Context.** Several design choices rested on estimates: how many characters a minute of v3
dialogue takes, whether the joins between voice requests can be heard, how v3 reads scores, and
what each provider call costs and how long it takes. Voice characters come from a quota whose
limit is not visible.

**Decision.** One script, [`backend/scripts/spike.py`](../backend/scripts/spike.py), ran the whole
path once with real data: fetch, write, voice and master. Each stage saves its output and runs
separately, and the two paid stages have a `--dry-run` option that prints the texts and the
estimated cost first. The results are in [docs/spike.md](spike.md). The script is throwaway code,
kept as the record of how the numbers were obtained.

**Alternatives considered.**
- *Build the pipeline on the estimates:* a wrong estimate would show up in the sample, the most
  expensive audio of the project.
- *Test only with fakes:* free, but a fake cannot say how v3 sounds or what it bills.
- *A private notebook:* reviewers could not see or rerun the measurements.

**Trade-offs.** One run is a small sample, and v3 is not deterministic: the full-length test is
the sample in Step 7. The spike cost about $0.0074 of OpenAI and 663 ElevenLabs characters.

**Evidence.** [docs/spike.md](spike.md). The main correction: v3 dialogue averaged 12.4
characters per second, not the 20 suggested by an earlier 71-character test. A 5-minute episode
therefore needs about 3,700 characters, and script length is planned from this figure.

---

## D19 · An episode is shorter rather than padded

**Status:** Accepted · **Date:** 2026-09-27 · **Revised:** 2026-09-27 (Step 4), 2026-09-28 (Step 5), 2026-09-29 (Step 8)

**Context.** The user chooses an episode length, but some days bring little news for an interest.
A model asked to fill a fixed length with thin material pads it out: it repeats itself or adds
claims that no source supports.

**Decision.** The chosen length is a target, not a quota.
- The episode plan gives each interest a share of the length by weight, capped by the fresh
  material it has.
- An interest with no fresh material is left out of that day's episode.
- If no interest has fresh material, the episode is not generated, and the reason is recorded
  without spending on voice. It ends as `skipped`, with the reason in `status_reason` (Step 4),
  so it does not count as a failure and is not offered for retry.

**Alternatives considered.**
- *A fixed length:* it invites padding, which D7 would then reject in a rewrite loop that cannot
  succeed with the same material.
- *Filling with background content:* it is not news, and it cannot be checked against a fresh
  source.

**Trade-offs.** Episode length varies from day to day, and a quiet day can mean no episode. The
reason is shown to the user.

**Evidence.** Every claim must come from a source (D7), so the material, not the target length,
limits what can be said. The Step 3 spike measured about 12.4 characters of dialogue per second,
which turns a share of the length into a character budget per block.

**Revised on 2026-09-28, when selection was built (Step 5).** How the length is shared:
- *Budget:* the length times 12.4 characters per second, minus about 300 characters for the intro
  and 250 for the closing, in stories of about 380 characters (roughly 30 seconds: the fact and a
  reaction). That gives 4, 8 and 12 stories for 3, 5 and 7 minutes, in line with the definition's
  estimate of about 5, 8 and 11.
- *Sharing:* first one story for each interest block that has material, in weight order, so no
  interest is left out while there is room; then the rest one at a time by the D'Hondt method
  (the one used to share parliamentary seats), with weights of 3, 2 and 1 points. The quotient is
  counted per interest, so a team split into two sports blocks (D22) does not weigh double; within
  it, the block with fewer stories gets the slot. A block with no more material leaves its slot to
  the others.
- *Roundups:* up to 4 lesser results of the same round can form one roundup story, told in one
  sentence each.

On the real data of 2026-09-28, a 5-minute catch-up for the sample's interests shared its 8
stories as 2 for Barça's football, 1 for Barça's basketball, 2 for the EuroLeague, 2 for the Liga
ACB and 1 for the NBA, with 5 to 31 candidates per block. Before counting per interest, the split
Barça took 5 of the 8. Without roundups, a catch-up told only 2 of the EuroLeague's 9 games. The
limit was time, not material. The first real script came out at 2,956 of the 3,590 planned
characters, about 4 of the 5 minutes: the writer reads "never pad" as leave to be short, which is
tuned with the sample (Step 7).

**Revised on 2026-09-29 (Step 8).** Barça football and basketball became two sections (D51), each
with its own weight, so the quotient is now counted per block, with the same tie-break. With the
sample's weights and news in all seven sections, the 5-minute allocation is unchanged (a test
proves it).

**Revised on 2026-09-30 (Step 10): the length is approximate.** Two things move it: the script is
kept within 10% of a character target (D40), and the voice's pace varies around the spike's 12.4
characters per second. The sample, a 5-minute episode, runs 293.6 seconds. The last real-voice run
before delivery was trimmed from 4,277 to 3,386 characters (91% of the 3,720 target), and
ElevenLabs spoke them at 13.8 per second: 248 seconds. Making the audio hit the minute
(regenerating the voice, or stretching it) would cost voice credits or sound quality for a length
the product presents as a target. The cheaper improvement is to budget with the pace the master
already measures for each episode.

---

## D20 · Every check is proven by a sabotage test, and the judge is measured

**Status:** Accepted, measured in Step 5 · **Date:** 2026-09-27 · **Revised:** 2026-09-28

**Context.** A check that never fails proves nothing, and an LLM judge can be wrong in both
directions.

**Decision.**
- Every check has a sabotage test, run with fakes in the test suite at no cost. Each of these must
  be caught:
  - an invented number, a reversed score and a source id that does not exist;
  - a number written as words, and an audio tag that is not allowed;
  - an invented claim without numbers, a factual turn without sources, and a rumour told as a fact;
  - a truncated audio chunk.

  For the judge's cases, the fake judge tests the wiring: a flagged turn must lead to a rewrite
  and then to `failed`.
- The real judge is measured once, on about 20 claims labelled by hand from real sources:
  supported, contradicted, not in the source, and overstated. The result records how many it gets
  right and in which direction it errs.

**Alternatives considered.**
- *Trusting the judge without measuring it:* its errors would only show up in production.
- *A large benchmark or a local hallucination model (HHEM):* more rigorous, but out of scope for
  now; it is future work.

**Trade-offs.** About 20 claims is a small sample: it reveals gross errors, not a precise accuracy.
Measuring it costs under $0.01.

**Evidence.** The sabotage practice comes from a previous project (D7). The measurement is
recorded when the judge is built (Step 5) and on the sample episode (Step 7).

**Measured on 2026-09-28 (Step 5).**
- *Sabotage tests:* each code check has its own, and each one asserts the exact reason reported.
  They cover an invented number, a score written loser first, a score made of two real numbers
  that do not go together, a number word, a tag outside the list, a URL, markdown, an emoji, a
  source id read aloud, an over-long turn, an unknown source id, a number without sources, the
  intro skipping the lead story, a skipped story, the wrong segment order, too many tags and an
  over-long script. The judge's wiring is tested with a fake judge for each failing verdict, and
  the audio checks with a cut-short chunk and a silent one.
- *The real judge, on hand-labelled claims:* 28 claims about 7 real sources, 14 of them about
  Liga ACB reports in Spanish, with the traps found in those reports (a valuation told as points,
  "triple" told as triple-doubles, a narrow win told as an easy one). It called all 28 correctly as
  pass or fail, with no false alarm and no miss; 25 got the exact expected label, and the other 3
  were flagged under a neighbouring label. One `gpt-6-luna` call, $0.0015, 13 seconds
  ([`backend/scripts/measure_judge.py`](../backend/scripts/measure_judge.py) holds the claims and
  labels; the source texts are read from the database, not stored in the repository).
- *The real judge, on a real script:* all 26 turns of the second real episode passed, and all 26
  were labelled correct by hand (D7).

Both samples are small. The claims were written and labelled by the AI assistant that built the
checks, and the script's turns by the author, so they rule out gross errors rather than give an
accuracy figure. The sample episode will be checked the same way.

**Done in Step 7 (2026-09-29).** Every fact of the sample's final candidates was checked against its
sources, sentence by sentence, before the voice was paid for (D45).

---

## D21 · Episodes of 3, 5 or 7 minutes, and a 5-minute sample

**Status:** Accepted · **Date:** 2026-09-27

**Context.** A personal news briefing competes for a few minutes of the listener's day. Each
minute of audio costs about $0.075 of voice, and the quota of the provided key is not visible.
The sample is the one episode the reviewers will listen to.

**Decision.** The user picks 3, 5 or 7 minutes, as a target (D19). The sample is 5 minutes.

**Alternatives considered.**
- *3, 5 or 10 minutes:* 10 minutes is the longer analysis format. It needs about 16 stories, which
  a quiet day may not have, and it costs about $0.74 of voice per episode.
- *A free-form length:* it makes the segment and cost budgets harder to plan.

**Trade-offs.** There is no long-form option, such as a 15- to 30-minute show.

**Evidence.**
- Google's Daily Listen, a personalised podcast with two AI hosts, runs
  ["up to five minutes"](https://9to5google.com/2025/01/08/google-discover-daily-listen/).
- NPR's [News Now](https://www.npr.org/podcasts/500005/npr-news-now) gives "the latest news in
  five minutes", and [Up First](https://www.npr.org/podcasts/510318/up-first) takes 10 minutes.
- The Step 3 spike measured 12.4 characters per second, so 3, 5 and 7 minutes need about 2,200,
  3,700 and 5,200 characters. On 2026-09-27 the sources had 29 fresh stories from the last 48 hours,
  before counting a round's games.

---

## D22 · The episode follows the listener's priorities

**Status:** Accepted · **Date:** 2026-09-27 · **Revised:** 2026-09-28 (Step 5), 2026-09-29 (Step 8)

**Context.** The listener's main interest can be a team, such as FC Barcelona, that plays in
competitions covered by other interests: the EuroLeague, the Liga ACB and LaLiga. Without a rule,
a Barça game could be told twice, once as Barça news and again in its league's round. In the Step
3 spike, a model left to organise the episode skipped the strongest story.

**Decision.**
- Code builds the episode plan: an introduction, one block per interest in order of weight, and a
  closing. The model writes each block.
- Each story or game is told once, in the block of the highest-weighted interest it belongs to.
- A team interest spans sports: its club's official site, plus the league stories whose headline
  names the team, and the team's games in the structured data.
- For the sample, that gives FC Barcelona (football and basketball), then the EuroLeague, the Liga
  ACB and the NBA.

**Alternatives considered.**
- *Letting the model structure the episode:* it skipped the strongest story in the spike.
- *Fixed sections by sport or league:* simpler, but not personal, and the team would be split
  across sections.
- *Allowing the same story in several blocks:* it spends the time budget (D19, D21) twice.

**Trade-offs.** A Barça game appears only in the Barça block, so the EuroLeague and ACB blocks
cover the rest of their rounds.

**Evidence.** fcbarcelona.com publishes an English articles sitemap that covers football and
basketball: 10 articles from the last 24 hours on 2026-09-27, including the report of "Barça
119-101 Leyma Coruña". The Step 3 spike showed the model skipping the strongest story
([docs/spike.md](spike.md)). On the same day, 5 of 20 Eurohoops articles named Barcelona only in
passing, in the body, which is why the filter uses the headline.

**Revised on 2026-09-28 (Step 5): the episode goes sport by sport.** After hearing the first real
script, which mixed Barça's football and basketball in one block, the author asked for football
first and basketball after, so the listener always knows which Barça is meant.
- A team that plays several sports gets one block per sport: FC Barcelona's football (its club
  news, and its LaLiga and Champions League games and tables) and FC Barcelona's basketball (its
  club news, and its EuroLeague and Liga ACB games and tables). The club's sitemap gives the sport
  in each URL; league sources take their competition's sport.
- Blocks are grouped by sport. Each sport goes in the order of its highest-weighted block; on a
  tie, football goes first (the club's main sport), then basketball, then topics without a sport.
  Within a sport, blocks keep their weight order. For the sample: Barça's football, Barça's
  basketball, the EuroLeague, the Liga ACB and the NBA.
- The writer is told to say when the episode moves to another sport and which of the club's teams
  it means. Time is still shared per interest (D19), so splitting a team does not give it more.
- Data is matched to a team by exact official names, never as text: UEFA names the club
  "Barcelona", and "Barcelona" must not match "RCD Espanyol de Barcelona".

**Revised on 2026-09-29 (Step 8).** A team is followed per sport (D51): each catalogue topic has
one sport. The order is still derived from the weights and the order the sections were added,
grouped by sport, and the app shows it as the pipeline computes it.

---

## D23 · What an episode covers: what is new, or a catch-up the first time

**Status:** Accepted · **Date:** 2026-09-27 · **Revised:** 2026-09-28 (Step 5)

**Context.** A fixed time window cannot serve both a new listener and a daily one. With a 48-hour
window, an episode on a Monday would miss a round played on the Thursday and Friday before, and a
new listener gets no context. The sample also must not depend on the day it is recorded.

**Decision.**
- **The first episode is a catch-up.** For each competition it covers the latest round played
  (even one still in progress), with its results and best players, and the standings where an
  official source has them (the EuroLeague API). It adds what comes next and the news of the last
  three days.
- **Every later episode covers what is new since the previous one:** the games played and the news
  published since then, with at most three days of news, and nothing that was already told.
- Each block ends with what comes next, when there is a fixture.

**Alternatives considered.**
- *A fixed 48-hour window:* it misses rounds played before a weekend, and a new listener gets no
  context.
- *A fixed 7-day window:* it repeats stories to daily listeners.

**Trade-offs.** The first episode reuses results that may be a few days old. Standings are told
only where an official structured source exists; for the Liga ACB and LaLiga they come only from
official news.

**Evidence.** On Monday 5 October at 07:00, EuroLeague round 3 would be 60 to 87 hours old
(EuroLeague API). On 2026-09-27, a quiet Sunday, the sources had 29 stories from the last 48 hours,
10 official Barça articles from the last 24 hours and 17 official ACB news items from the last 48
hours, besides the latest round of each league.

**Revised on 2026-09-28, when selection was built (Step 5).**
- *"New" means first seen by us after the previous episode chose its stories,* not published or
  played after it. A game that started before the previous episode and ended after it would
  otherwise never be told. The previous episode's plan stores the moment it chose (`selected_at`);
  its start time is not used, because a retry changes it.
- *"Already told"* is every source a completed episode of the listener used. The standings are
  told again only when they change; what comes next may repeat, since it is still next.
- *In a catch-up,* a team's block takes the team's latest game in each competition, and a
  competition's block takes its latest round.
- *Standings* now come from official structured data for the EuroLeague, LaLiga and the Champions
  League (D31, D4). For the Liga ACB, only its official news mention them.

**Revised on 2026-09-30 (Step 10): every completed episode moves the line, a manual one
included.** The previous episode is the listener's last completed one, scheduled or from
"Generate now". Three test episodes on the same day left the third with 2 hours 44 minutes of new
material: 12 candidates for the Liga ACB, the EuroLeague and the NBA, and none for Barça, whose
items were all seen earlier or already told. The two high-weight Barça sections were left out
(D19), and a EuroLeague injury report led the episode. The rule did its job, since nothing was
repeated; the cost is that a second episode on the same day can be thin, and nothing tells the
listener why. Future: say before "Generate now" how little is new, say in the episode that a
followed section has nothing new, or let an on-demand episode leave the scheduled one's line where
it was.

---

## D24 · Sources are ingested on a schedule and stored

**Status:** Accepted, built in Step 5 · **Date:** 2026-09-27 · **Revised:** 2026-09-28

**Context.** Official news lists only show the latest items. On 2026-09-27, acb.com's recent-news
sitemap and news listing showed reports for all 9 games of round 1 in the afternoon, and only 6
of them five hours later. The listing has no further pages. A catch-up episode (D23) must still
reach the latest round days later, and each source should be downloaded once for all listeners.

**Decision.** The worker ingests every catalogue source every three hours and stores what it finds
in the shared `articles` table, deduplicated by URL. An episode's fetch stage reads from that
store, after one fresh ingest right before generating. Stored sources are kept for 30 days.

**Alternatives considered.**
- *Fetching per episode:* it loses stories that have scrolled off a list, and it downloads the
  same source once per listener.
- *Relying on each site's archive:* fcbarcelona.com has one, but acb.com does not.

**Trade-offs.** The worker makes requests even when no episode is due: a few per source every
three hours, with the honest User-Agent and respecting `robots.txt`. The store grows, which the
30-day limit bounds.

**Evidence.** On 2026-09-27, acb.com's round-1 reports went from 9 to 6 visible in about five
hours. Its recent-news sitemap held 17 to 19 items, about a day and a half of news, so three hours
leaves a wide margin. Its news listing ignores page parameters, while fcbarcelona.com publishes an
index of article sitemaps.

**Built in Step 5 (2026-09-28).**
- One ingest runs every source, and a source that fails, while downloading or while saving,
  never stops the others: its transaction is rolled back and the ingest report carries a one-line
  error (a database error's full statement, which holds article text, goes only to the log).
- A news article is never overwritten, so the text an episode was checked against stays the same.
  A data item (fixtures, a table) is updated when its text or its structured fields change.
- A batch is deduplicated by URL before it is saved: uefa.com's sitemap once listed an article
  twice, and PostgreSQL refuses to update the same row twice in one statement.
- Only articles from the last 4 days are downloaded, and an article already stored is not
  downloaded again.
- It can be run by hand with `python -m app.sources.ingest`. The first full real ingest, of 12
  sources, took 27 seconds.

---

## D25 · The data model grows step by step, and PostgreSQL enforces it

**Status:** Accepted · **Date:** 2026-09-27 · **Revised:** 2026-09-28 (Step 5)

**Context.** The definition sketched nine tables, but most of them belong to code that does not
exist yet. The database is written by the API, and later by the worker and by scripts.

**Decision.**
- **One migration per step.** Each table arrives with the step whose code uses it:
  - Step 4 adds `users`, `podcast_settings`, `interests` and `episodes`;
  - Step 5 adds the pipeline tables (`articles`, `episode_articles`, `stage_runs` and
    `provider_calls`) and the episode's result columns (title, script, audio and duration);
  - Step 8 adds `listen_events`.
- **Keys:** `bigint GENERATED ALWAYS AS IDENTITY`.
- **Types:**
  - `text`, and `timestamptz` for every point in time;
  - `jsonb` for the list of hosts;
  - PostgreSQL arrays for keywords and schedule days. Days are ISO weekdays, where 1 is Monday,
    as in Python's `isoweekday()` and PostgreSQL's `isodow`.
- **Enumerated values** (status, trigger, tone, weight, length and interest kind) are `text` with a
  `CHECK` constraint. The constraint is generated from the same `Literal` type that the API
  validates.
- **Rules the database enforces:**
  - unique `(user_id, topic)` and unique `(user_id, scheduled_for)`;
  - a partial unique index on `episodes (user_id) WHERE status IN ('queued', 'in_progress')`, so a
    user has at most one episode in flight;
  - `ON DELETE CASCADE` from `users`.
- **Constraint names:** a naming convention gives every constraint a predictable name.
- **Settings table:** podcast settings are a separate one-to-one table (who the user is, versus how
  they want their podcast).
- **Topic catalogue:** it lives in code, because each topic needs code for its sources.

**Alternatives considered.**
- *All nine tables now:* five tables would have no code or tests until Step 5, and would likely
  change.
- *Native PostgreSQL enums:* adding a value needs `ALTER TYPE`, and Alembic's autogenerate does not
  track enum values.
- *`serial` or UUID keys:* `serial` is the legacy form of identity columns. Random UUIDv4 keys
  scatter index inserts, and nothing here needs globally unique IDs.
- *Validating only in the API:* the worker and scripts write too.

**Trade-offs.**
- Alembic's autogenerate does not compare `CHECK` constraints, so changing an allowed value means
  writing that migration by hand.
- There will be one migration per step instead of one in total.

**Evidence.**
- Supabase's PostgreSQL best practices: identity keys and UUIDv4 fragmentation; `text` and
  `timestamptz`; text plus `CHECK` for enumerations; indexing foreign keys. Here the unique indexes
  that start with `user_id` serve that purpose.
- The SQLAlchemy and Alembic documentation on constraint naming conventions.
- `backend/tests/test_models.py` writes a bad value into each constraint, bypassing the API, and
  checks that PostgreSQL rejects it.

**Step 5 (2026-09-28), migration `e3d606ed94cd`.**
- `articles`: the stored sources, shared by all listeners, with a unique URL, the source's name,
  kind (article or data), whether it is official, its language, the publication date, the body
  and `jsonb` metadata (competition, round, type and teams of a data item).
- `episode_articles`: the sources each episode uses, with the short id the script cites (`S1`…),
  the block and the rank. Its foreign key to `articles` has no cascade, so a source that an
  episode cites can never be deleted.
- `stage_runs` (one row per stage and attempt, with its details in `jsonb`) and `provider_calls`
  (one row per paid call). A `CHECK` ties the usage to the provider: OpenAI rows carry tokens and
  no characters, ElevenLabs rows the reverse. Cost is `numeric(10, 6)`, never a float.
- `episodes` gains its results: title, plan, script, audio path, duration and chapters.
- Two coherence rules on `episodes`: a `completed` episode has audio and only it does, and a
  `failed` or `skipped` episode has a reason and only they do. Alembic's autogenerate does not
  detect new `CHECK` constraints on an existing table, so both were added to the migration by
  hand; a test fails if either is missing.
- The article's text column is `body`, not `text`: inside the model class, a `text` attribute
  would hide SQLAlchemy's `text()` function, which the same class uses.

---

## D26 · Migrations with Alembic, applied by a prestart job

**Status:** Accepted · **Date:** 2026-09-27

**Context.** The schema must be versioned and reviewable. `docker compose up` must also apply it,
without shell scripts in the containers.

**Decision.**
- **Configuration:** Alembic is configured in `pyproject.toml` (`[tool.alembic]`, Alembic 1.16+),
  with no `alembic.ini`. `migrations/env.py` takes the database URL from the settings (D16).
- **Writing migrations:** they are autogenerated from the models and reviewed line by line, and
  post-write hooks run Ruff on them.
- **Folder name:** `migrations/`. With a folder named `alembic/`, Ruff's import sorter treats the
  library as local code.
- **Applying them:** a one-off `prestart` Compose service runs `python -m app.prestart`. It applies
  `upgrade head`, then creates the demo user if it does not exist, so it can run on every start.
  The API waits for it with `condition: service_completed_successfully`.
- **Tests:**
  - `alembic check` fails when the models and the migrations drift apart, and a sabotage test
    proves it catches drift;
  - a round trip, from a downgrade to `base` back to `head`, proves every downgrade works.

**Alternatives considered.**
- *`create_all()` at startup:* no history, and it cannot alter existing tables.
- *The demo user in a data migration:* demo data would live in the schema history, and the Step 9
  synthetic data needs a seed step anyway.
- *Migrating when the API starts:* several API replicas would race each other.
- *An explicit step before `up` (`docker compose run --rm … prestart`):* what the official
  template does since August 2026. It is the right model for a production deployment, where
  migrating is a deliberate step, but here reviewers must start everything with one command (D10).
- *A shell entrypoint:* shell scripts in the containers are avoided on purpose, because Windows
  checkouts can change their line endings.

**Trade-offs.**
- One more Compose service, which exits after running.
- Every `up` applies pending migrations automatically. That is right for a local demo, but a
  production deployment would run them as an explicit step (future work).

**Evidence.**
- The official
  [full-stack FastAPI template](https://github.com/fastapi/full-stack-fastapi-template) ran this
  job, migrations plus initial data, as its own `prestart` container from PR #1350 (2024). In
  PR #2426 (release 0.11.0, 2026-08-11) it moved to an explicit command before startup (checked on
  2026-09-27).
- Docker's
  [startup order guide](https://docs.docker.com/compose/how-tos/startup-order/) documents
  `condition: service_completed_successfully`.
- Alembic's documentation on `pyproject.toml` configuration, and its cookbook recipe for sharing a
  connection, which the tests use.
- `backend/tests/test_migrations.py`.

---

## D27 · API without login: one current-user dependency, and the database as the guard

**Status:** Accepted · **Date:** 2026-09-27 · **Revised:** 2026-09-29 (Step 8)

**Context.** Authentication is future work, but the data model already has users. The web app
(Step 8) needs a predictable API, and a double click must never pay for voice twice.

**Decision.**
- **Endpoints**, all under `/api/v1`:
  - `health`;
  - `catalog`;
  - `settings`: `GET` and `PUT`;
  - `interests`: `GET`, `POST`, `PATCH` (the weight) and `DELETE`;
  - `episodes`: a paginated list, one episode, `POST` for "generate now", and `POST /{id}/retry`.
- **The current user:** every request acts as the demo user through one `CurrentUser` dependency,
  and routes carry no user id. Adding authentication changes that dependency only.
- **Generation:** the API never generates. `POST /episodes` queues an episode and answers
  `202 Accepted`, and the worker does the work (D2).
- **Status codes:**
  - `422` for invalid input;
  - `404` for another user's rows, so the API does not reveal that they exist;
  - `409` for a conflict with the current state: a duplicate interest, a seventh interest, no
    interest to talk about, an episode already in flight, or a retry of an episode that did not
    fail;
  - `503` when the generation keys are missing, naming the variables (D10).
- **The in-flight rule:** "generate now" relies on the partial unique index (D25), not on a prior
  `SELECT`, so two simultaneous clicks queue one episode. Only that index maps to `409`; any other
  integrity error surfaces as a `500`.
- **At most six interests** (revised in Step 7; it was five): the whole catalog fits, and the
  sample uses it. Five was chosen so that a 3-minute episode left about 30 seconds per block, but
  since Step 5 the selection stage guarantees that: it never plans more stories than the length
  allows, and in 3 minutes the lowest-weighted interests are left out (D19). The cap now only
  bounds the selection prompt and what the user manages. Bounding per-user resources that cost
  money follows [OWASP API4:2023, Unrestricted Resource Consumption](https://api-security.owasp.org/editions/2023/en/0xa4-unrestricted-resource-consumption);
  the number six is a product choice, not a standard.
- **Settings:** `PUT` replaces all the settings, because the form always sends every field.
- **Style:** synchronous `def` endpoints with one session per request, `Annotated` dependency
  aliases and return types, as FastAPI's official skill recommends.
- **Documented errors:** each route declares its 404, 409 and 503 responses (`responses=`), so the
  OpenAPI document and `/docs` show every outcome, not only the success response and the 422 that
  FastAPI adds on its own.

**Alternatives considered.**
- *`/users/{id}/…` routes:* authentication would then need an ownership check on every route.
- *Check, then insert:* two concurrent requests both pass the check.
- *`403` for another user's rows:* it reveals that the row exists.

**Trade-offs.**
- Without authentication, the API only listens on `127.0.0.1` (D10).
- The five-interest cap is checked in the API, not in the database, so two concurrent requests
  could exceed it. For one user this is harmless.

**Evidence.** `backend/tests/test_api_*.py` and `test_openapi.py`. Each guard was broken on
purpose, and its test failed: the key check, the time zone check, the ownership filter, the
one-in-flight index and the documented error responses.

**Revised on 2026-09-29 (Step 8).** The cap is now eight interests: the seven catalogue sections plus
one of the listener's own (D51). The trade-off above applies to this cap: it is checked in the API,
not in the database.

**Revised on 2026-09-30 (Step 10).** The web app disables "Generate now" only while its request is
in flight. Once the API answers `202`, the button is enabled again although the episode is still
queued or running, and a second press gets the `409`, shown as an error. The index still allows
one episode in flight, so a listener can never pay for two at once. Keeping the button disabled,
with the episode's state, while one is in flight is a small future improvement.

---

## D28 · Tests run against a real PostgreSQL

**Status:** Accepted · **Date:** 2026-09-27

**Context.** The model relies on PostgreSQL features: `CHECK` constraints, `jsonb`, arrays and a
partial unique index. Step 6 adds `SKIP LOCKED`.

**Decision.**
- **Database:** tests use the development PostgreSQL (`compose.dev.yaml`) with a separate
  `podcast_test` database. It is recreated on each run and built with the Alembic migrations, so
  every run also tests them.
- **Isolation:** each test runs inside a transaction that is rolled back at the end. The
  application's commits become savepoints, as in SQLAlchemy's recipe for joining a session into an
  external transaction.
- **Dependency overrides:** FastAPI's overrides give the API the test session, and settings
  without keys whatever the machine's `.env` holds.
- **Sabotage tests:** every guard has one (D20).

**Alternatives considered.**
- *SQLite:* faster, but it would not exercise the same constraints and types.
- *Testcontainers:* it starts its own PostgreSQL, at the cost of one more dependency and slower runs.
- *Truncating tables between tests:* slower, and tests could depend on each other.

**Trade-offs.** Tests need PostgreSQL running in Docker. When it is not running, the error gives
the command to start it.

**Evidence.** SQLAlchemy's documentation on joining a session into an external transaction. At the
end of Step 4, the 52 tests took about 2.5 seconds.

---

## D29 · One backend Dockerfile with a cached dependency layer and two targets

**Status:** Accepted · **Date:** 2026-09-27 · **Revised:** 2026-09-29 (Step 6), 2026-09-29 (Step 8)

**Context.** `prestart`, the API and the worker share code. Rebuilds must be fast while developing,
and reviewers only need Docker.

**Decision.**
- **Base image:** `python:3.14-slim`, the same Python as locally (D15).
- **Dependency layer:** the dependencies are installed in their own layer. They are read from
  `pyproject.toml` with `tomllib`, because pip cannot install only a project's dependencies. The
  code is copied afterwards, so a change to the code does not reinstall anything.
- **Contents and user:** only `app/` and `migrations/` go into the image, with no tests or spike.
  The container runs as an unprivileged user.
- **In Compose:**
  - the `api` image is built once (`image: podcast-backend`) for `prestart` and the API, and each
    service sets its own command; the worker builds its own target (Step 6, below);
  - a YAML fragment (`x-backend`) holds what they share: the build, the optional `.env`, the
    in-network database URL and, since Step 6, the audio volume mounted at `/data`.

**Alternatives considered.**
- *`pip install .`:* every change to the code reinstalls every dependency, and a second copy of
  the code ends up in `site-packages`.
- *uv with `--no-install-project`:* the same idea with a lock file, at the cost of one more tool
  (D15).
- *`fastapi[standard]` with `fastapi run`:* more dependencies than uvicorn alone.

**Trade-offs.** The API image is 445 MB, mostly lxml and the provider SDKs. Nothing is compiled;
since Step 6 the stages only separate what each service needs (below).

**Evidence.** Measured on 2026-09-27:
- the first build took about 1.5 minutes, and a rebuild after a change to the code took 3 seconds,
  with the dependency layer reported as `CACHED`;
- `id` inside the container reports uid 999 (`podcast`).

**Revised in Step 6 (2026-09-29): two build targets.** The worker needs ffmpeg (mastering, audio
checks and the tone voice), and Debian's `ffmpeg` package adds 457 MB. The Dockerfile now has a
shared `base` stage (Python, dependencies, user, `/data` owned by that user) and two targets:
- `api` (`podcast-backend`, used by `prestart` and the API): base plus the code, still 445 MB, with
  no ffmpeg;
- `worker` (`podcast-worker`): base plus ffmpeg, installed *before* the code is copied so a code
  change does not reinstall it, plus the code (without the migrations, which `prestart` applies):
  1.07 GB.

*Why:* the API, the service exposed to the network, does not carry media codecs it never uses (a
smaller attack surface), and a reviewer who only runs `docker compose up` never builds ffmpeg.
*Alternatives:* one image for everything (simplest, but the API doubles in size for nothing); a
static ffmpeg binary copied from a third-party image (about a third of the size, but an unsigned
binary from outside the distribution instead of Debian's signed, patched package). *Trade-off:* a
few more lines of Dockerfile and two image names. Measured: `ffmpeg -version` in the worker image
reports 7.1.5 from Debian 13, and an episode mastered with it measured −16.5 LUFS (target −16 ± 1).

**Revised on 2026-09-29 (Step 8).** The build context is the repository root, with an allowlist
`.dockerignore`; a `node:24-slim` stage builds the web app; and the image keeps the repository
layout under `/app` (D49). The `api` image is 456 MB.

---

## D30 · Sources are downloaded like a responsible crawler

**Status:** Accepted · **Date:** 2026-09-28

**Context.** Most sources are web pages, feeds and sitemaps that we do not own. Each site states
in its `robots.txt` what automated clients may fetch, often with wildcard rules.

**Decision.** Every download goes through one fetcher:
- an honest User-Agent that links to this repository, so a site can see who we are and block us
  by name;
- `robots.txt` read once per site and ingest, and applied as RFC 9309 defines it, with Protego
  (the parser Scrapy uses). A `robots.txt` that returns 4xx allows everything; a 5xx or a network
  error disallows the whole site until the next ingest;
- a 20-second timeout per request;
- the Guardian key goes in the `api-key` header, never in the URL, so it cannot appear in an error
  message or a log;
- a failing page skips only that article, and a failing source is reported in the ingest result
  without stopping the other sources.

**Alternatives considered.**
- *Python's `urllib.robotparser`:* it ignores `*` and `$` in rules, so it allowed URLs that sites
  disallow.
- *A hand-written matcher:* the standard has edge cases (longest match, ties, `$`), and Protego is
  small and maintained.
- *Not checking `robots.txt`, as in the Step 3 spike:* acceptable for a one-off measurement, not
  for a scheduled product.

**Trade-offs.** One more dependency (Protego 0.7.0, BSD-3, with no dependencies of its own). A site
whose `robots.txt` fails with a server error is skipped for that ingest, three hours at most.

**Evidence.** Measured on 2026-09-28 against the live `robots.txt` files, comparing both parsers:
`urllib.robotparser` allowed ESPN's `/nba/boxscore?…`, laliga.com's `/es-ES/noticias/` and its
PDF files, CBS Sports' `?sortdir=` pages and the Guardian's `/print` pages, which their wildcard
rules disallow; Protego did not. Every path the providers use is allowed. The robots files of the
EuroLeague API and its standings host returned 404, and the Guardian API's returned 401. The
Guardian API accepted the key in a header (HTTP 200). See [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309).

**Revised on 2026-09-29 (Step 7): a pause between requests to the same site.** The fetcher waits
at least one second between two requests to the same site, or longer if the site's `robots.txt`
asks for it with `Crawl-delay`. The first request to a site does not wait, and the tests, which
use a fake network, do not wait either, except the test that checks the waits. Evidence: on
2026-09-29 a test that read fcbarcelona.com's news listing sent about 40 requests in a row and got
`429 Too Many Requests`. Trade-off: an ingest that reads many pages from one site takes longer,
about one second per page.

---

## D31 · Official data is read from the data inside official pages

**Status:** Accepted · **Date:** 2026-09-28

**Context.** The source rule (D4) takes data from official sources. The EuroLeague has a public
API, but LaLiga and the Liga ACB do not document one. Their websites are built with Next.js, which
embeds each page's data in the HTML that any browser receives.

**Decision.**
- **laliga.com (English pages):** the JSON in `<script id="__NEXT_DATA__">` gives the standings,
  the results of the current and previous matchdays, and the fixtures of the next one.
- **acb.com's calendar:** the React Server Components data in the page gives the teams and the 34
  rounds with their scores, dates and status, so it provides the latest results and the next
  round.
- Like the EuroLeague API, each result, standings table and set of fixtures becomes a plain-text
  source with its own id (D4). Results are written winner first; records are written in words
  ("1 win and 0 losses"), so they are never mistaken for scores; fixtures give the day and never
  a time, since the time depends on the listener.
- If a page stops carrying the data, the source fails with a clear error, the ingest reports it,
  and episodes go on with the other sources. Nothing is invented to fill the gap.

**Alternatives considered.**
- *The internal APIs these pages call:* undocumented, and not meant for third parties.
- *Standings and fixtures from news stories only:* not structured, and often missing.
- *The ACB's official calendar PDF:* parsing a PDF is more fragile than the page's data.
- *A commercial football data API:* it needs a key and is not an official source.

**Trade-offs.** These are not stable, documented APIs: a redesign can break a provider, which the
ingest report shows at once. The ACB format is the more fragile of the two. The tests use small
pages with the same data shape, written for the tests, and no third-party content.

**Evidence.** Measured on 2026-09-28: laliga.com's standings page embedded 20 rows (`position`,
`points`, `played`, `won`, `drawn`, `lost`), its current matchday was 8 (9 to 12 October) and
matchday 7 was complete, with Sevilla 1–3 FC Barcelona. acb.com's calendar held 306 games (34
rounds of 9), with all 9 round-1 results and the round-2 fixtures for 3 and 4 October. Two teams
had played one game fewer (a postponed game), so the table says "after Matchday 7" when the
current matchday has not started, and each row gives the games played.

---

## D32 · The pipeline runs as recorded stages, behind small provider interfaces

**Status:** Accepted · **Date:** 2026-09-28

**Context.** D3 defines six stages with checkpoints. An episode involves network sources, two paid
providers and ffmpeg, and it must be testable at no cost, resumable after a failure, and
explainable from the database afterwards.

**Decision.**
- **Two packages:** `app/sources` downloads and stores sources (D24, D30), and `app/pipeline`
  generates an episode. Each stage is a function that receives one `Run` object (the database
  session, the episode, the listener's settings and interests, the providers and "now") and
  returns its details.
- **Small provider interfaces:** one `Llm` interface for the three model calls (select, write and
  judge), so cost is computed in one place; one `Voice` interface. The real implementations wrap
  the OpenAI and ElevenLabs SDKs. The tests use a fake model, and development can use a tone voice
  (D6), so the whole pipeline runs at no cost.
- **Recorded stages:** before a stage runs, its `stage_runs` row is committed as `in_progress`, so a
  crash leaves visible which stage was running. Whatever happens, it is then closed with its
  status, error, details and finish time (taken from Python: PostgreSQL's `now()` is the start of
  the transaction), and the stage's paid calls are saved, even when the stage failed. That commit
  also stores the stage's output: the checkpoint.
- **Resuming:** fetch always runs (it is free and brings the latest news); select runs if the
  episode has no plan, write if it has no script, and check if it has not passed yet; voice always
  runs, but its cache means nothing is paid twice; master always runs, since it is free.
- **Endings:** "nothing new" ends as `skipped` (D19); a known failure (a check failing twice, bad
  audio) ends as `failed` with its reason; an unexpected error rolls the transaction back first,
  because PostgreSQL accepts nothing more in a failed transaction, and then ends as `failed` with a
  one-line reason. A completed episode's status and audio are written together, as the database
  requires (D25).
- **By hand:** `python -m app.pipeline.runner <id>` or `--new`, with `--tone-voice` for free
  audio. It checks the keys before doing anything.

**Alternatives considered.**
- *A workflow framework (Celery, Prefect, LangGraph):* retries and state for six linear stages
  that already have checkpoints in PostgreSQL; one more system to run and explain.
- *One function per episode, without stage records:* a failure would repeat paid work and leave
  nothing to inspect.
- *Mocking the SDKs in tests:* the tests would depend on each SDK's internals instead of on our
  own interface.

**Trade-offs.**
- The runner marks the episode `in_progress` itself. In Step 6 the worker will claim episodes
  with `SKIP LOCKED`, and that step decides where the claim lives. *Resolved in Step 6 (D47):* the
  worker claims the episode with `SELECT … FOR UPDATE SKIP LOCKED`, and the runner's first commit,
  which marks it `in_progress`, releases the lock; the runner stays the only place that sets it.
- An episode is generated synchronously, one at a time per process: about 1.5 minutes of text
  stages when measured, plus the voice.

**Evidence.** End-to-end tests with the fakes and real ffmpeg: a full episode, a retry that
resumes without repeating paid calls, a skipped episode, an unexpected error and a database error.
The last test comes from a real incident on 2026-09-28: a duplicated URL in a source made the
save fail, and the first version of the runner, reading the episode before rolling back, left the
episode stuck `in_progress`. After the fix, the same episode was retried: its stage history shows
the failed first attempt, and the second completed with all six stages. Its text stages took
about 80 seconds: fetch 4, select 9, write 27 and check 34.

---

## D33 · Official results carry the players, and code computes the gaps

**Status:** Accepted · **Date:** 2026-09-29

**Context.** After reading the episode 14 script, the author found it sounded like a news wire:
"Barça won 3–1 at Sevilla" with no names. Fans talk about who decided a game. The football
results came from official data that only held the score, while the basketball data already
named the best player of each team. The writer is also told never to compute numbers (D7), so it
could not say "five points clear" unless a source said so.

**Decision.**
- **Scorers in official football results.** A UEFA result lists the goals by team (player and
  minute, marking penalties, with own goals apart) and the player of the match; the match list
  the source already reads carries them. A LaLiga result lists the goals with their assists, read
  from the data inside each match page on laliga.com (D31): one more request per new result, about
  ten per matchday. If that page fails, the result is saved without goals.
- **Gaps computed by code.** Each row of the LaLiga and Champions League tables says how far it is
  from the leader ("5 points behind the leader", or "level on points with the leader"). The
  writer can then say "five points clear" and cite the official table; the model still never
  computes.
- **Refreshing stored data.** `python -m app.sources.ingest --refresh --source KEY` reads stored
  items again, so data already saved picks up an improved reader. News is never overwritten.

**Alternatives considered.**
- *Match reports from fcbarcelona.com:* they arrive through the club's news sitemap, like the
  basketball reports, but only for recent games. The report of the game at Sevilla (19 September)
  predates the first ingest (24 September), and news older than four days is not stored (D24). The
  club's news listing links to it, next to player pages and other non-news links. Reading reports
  from the listing is left as a future improvement.
- *Letting the model compute gaps:* it would weaken the number check (D7), because a computed
  number cannot be found in any source.

**Trade-offs.** One request per new LaLiga result, to an undocumented page format (D31). A refresh
counts a changed data item as seen again, so it is a maintenance tool, not part of the schedule.

**Revised on 2026-09-29: code writes the totals.** Each scorer carries his number of goals and
each team lists its assists with their number ("Raphinha 3 (22', 52', 69'). Assists: Christensen
1, Lamine Yamal 2"). In the first regeneration of episode 14 the writer counted them itself
("scored 3", "assisted the next 2"), and the number check rejected it, rightly: those totals were
not in any source.

**Evidence.** Measured on 2026-09-29: the UEFA match list had `playerEvents.scorers` and
`playerOfTheMatch` for all 18 finished games, with goal types `SCORED`, `PENALTY` and `OWN`. The
laliga.com page of Sevilla 1–3 FC Barcelona listed four goals: Fofana (19'), and Raphinha (22',
52', 69'), with assists from Christensen and twice from Lamine Yamal. The results listing itself
had only `home_score` and `away_score`.

---

## D34 · Days are spoken relative to the episode, and code writes the labels

**Status:** Accepted · **Date:** 2026-09-29 · **Revises:** D7 (dates)

**Context.** D7 asked for the weekday and the date on every game ("on Sunday 4 October"), so the
judge could check the day. In audio, full dates on every result sound like a news wire, and
models get weekdays wrong: in Step 5 the judge miscounted which date "Sunday" was.

**Decision.**
- Code labels each date in the sources with how to say it, relative to the episode's day in the
  listener's time zone: "today", "yesterday", "tomorrow", "last Saturday" (2 to 6 days before),
  "this Sunday" (2 to 6 days after), or "Saturday the 10th" further away. A source reads
  "Saturday 26 September 2026 [say: last Saturday]".
- The writer and the judge read the same labelled sources, so the judge checks days against the
  labels. The ±7-day calendar in the episode context goes away.
- The intro says which day it is ("It's Monday"), so the labels still make sense when an episode
  is played later.

**Alternatives considered.**
- *Full dates:* checkable, but they sound like a wire service.
- *The model working out relative days:* the error seen in Step 5.

**Trade-offs.** An episode played on a later day still says "tomorrow" for the day after it was
made; the weekday in the intro anchors it. Labels are English only, like the scripts.

**Evidence.** The episode 14 script gave a full date on almost every result. Unit tests cover each
rule with the sample's own dates, including the 11th to 13th.

---

## D35 · Speech normalisation before the voice, with a pronunciation dictionary

**Status:** Accepted · **Date:** 2026-09-29 · **Revises:** D7 (scores)

**Context.** The script keeps digits so the number check can compare them with the sources (D7).
A broadcaster does not read "3–1" as "3 to 1", and some names break the voice: "Bodø/Glimt" with
its slash, and sponsor names such as "iLERNA Lleida".

**Decision.** Just before the voice, code rewrites the text, for every episode:
- football scores (both numbers 15 or less, which never happens in basketball) in words, British
  style: "three-one", "five-nil", "one-all", "nil-nil"; basketball scores as "89 to 82";
- seasons as "2013-14", never "2013 to 14";
- a slash between two words becomes a space; a spaced dash becomes a comma and a spaced "&"
  becomes "and" ("Barça & Beyond" is said "Barça and Beyond");
- a pronunciation dictionary in code for names the voice gets wrong, the longest match first. It
  starts with "Bodø/Glimt" → "Bodo Glimt" and "iLERNA Lleida" → "Lleida", as fans say it. It
  grows when a name is heard wrong, and it applies to every episode, never to one.

**Alternatives considered.**
- *Scores in words in the script:* the number check could no longer compare them with the sources.
- *ElevenLabs pronunciation dictionaries:* they live in the provider's account and are managed
  through its API. A local dictionary is versioned, tested and free.

**Trade-offs.** The dictionary is hand-kept. The "15 or less" rule is a heuristic that only fails
for a basketball score of 15 or less, which does not happen.

**Evidence.** The episode 14 script contained "Bodø/Glimt", "2013/14" and "iLERNA Lleida". Unit
tests cover every rule.

---

## D36 · The same story under two URLs is one source

**Status:** Accepted · **Date:** 2026-09-29

**Context.** In episode 14, sources S3 and S4 were the same fcbarcelona.com article: the club
fixed a typo in the address of a published story ("beat" → "best"), and the ingest stored the
new URL as a new article.

**Decision.** Selection groups a source's stored pieces by a hash of their text, with whitespace
normalised, and keeps the one seen last, which is the corrected URL. If any copy was already told
in an earlier episode, the kept one counts as told.

**Alternatives considered.**
- *Deduplicating by the numeric id in the club's URLs:* specific to one site.
- *Deduplicating at ingest:* the typo URL would be kept, and it may stop working.

**Trade-offs.** Two copies whose text differs, even slightly, are still two sources. The same text
from two different outlets is not merged here: that is the editor's job (grouping), as before.

**Evidence.** Episode 14's S3 and S4 shared article id 4581481 and the same body. A unit test
covers the typo case, the "already told" case and the cross-outlet case.

---

## D37 · An editorial plan before writing

**Status:** Accepted · **Date:** 2026-09-29 · **Revises:** D19 (how the length is shared), D22
(which story leads)

**Context.** The episode 14 script was accurate but read like a news wire. The writer received a
list of stories per block and told every one of them, result by result, with equal weight. The
author asked for fewer stories, only the impactful ones, discussed in depth.

**Decision.** Generation becomes "plan, then write". After select picks the candidate stories,
an editor (`gpt-6-sol`, the writing model, since editorial judgement is what had to improve)
returns a plan in a validated schema:
- per section: the lead story (told in depth), why it matters to this listener, one to five key
  facts with their source ids (player detail preferred), at most three other results for one
  roundup line, the next game, and two flags: `brief` (nothing impactful: one line) and `major`
  (clearly bigger than a normal day);
- for the episode: the cold-open hook (fresh and relevant, preferring the last 72 hours or the
  next 48) and up to three threads that link sections.
- "Impactful" is defined in the instructions: the listener's team, records and streaks, upsets,
  big or dramatic margins, results that move the table, standout players. Competition sections
  look through the eyes of a fan of the listener's team; a competition the team does not play
  in is covered on its own terms.

Code keeps what code does best:
- it validates the plan (only ids that exist, each in its own section; the roundup never repeats
  the lead), asks once more with the problems if needed, and otherwise falls back to a simple
  plan of its own, marked in the episode, so an episode never depends on the model's format;
- it shares the length: the total the listener chose minus the intro and the closing, split by
  the weight of each section (3, 2, 1), a `major` section counting 1.5 times, a `brief` one
  getting one line. The largest-remainder method makes the shares add up exactly;
- select still groups a club's latest result in each competition into one story (D22), but no
  longer puts it first: the plan decides what leads. Code guarantees that grouping: if the
  selection model leaves out one of those results, code adds it to the club's results story. In
  test episodes 10 to 12 the model left out the 5–1 against Feyenoord, then the 89–82 against Efes,
  even with the rule written as mandatory.

The plan runs inside the select stage: select decides what is told, the plan how. The six stages
of D3 and their database constraint stay as they are.

**Alternatives considered.**
- *Only rewriting the writer's prompt:* the writer would still receive every selected story as
  something to tell.
- *The plan inside the writer's call:* cheaper, but the plan could not be validated before
  writing.
- *The model sharing the length:* models do not add up characters reliably.
- *A new "plan" stage:* clearer in the stage history, but it needs a migration of the stage
  constraint for no gain in behaviour.

**Trade-offs.** One more paid call per episode: about $0.04 to $0.045 with `gpt-6-sol`, measured
(about 10,400 input tokens). The fallback plan is plainer than the model's. Updated after episodes
20 to 23: with one extra candidate per section the plan's prompt is 13,000 to 17,500 tokens, about
$0.05 to $0.06 per call, and in those runs the first answer often failed validation (a fact with
more than two numbers), so the plan cost about $0.10 to $0.12. A text-only episode costs $0.19 to
$0.24 in all. Trimming what the plan reads is a future improvement.

**Revised on 2026-09-29, after the first regeneration of episode 14 failed.**
- The lead is given as source ids, not as a story number. Select sometimes groups several
  results into one story; with a number, the editor could not take one result as the lead and put
  the others in the roundup, every answer was invalid, and two paid calls ended in the fallback.
- The fallback plan now gives the titles of the lead's sources and of the section's context
  (standings, fixtures) as key facts, and splits a grouped story into lead and roundup. Before, it
  gave the section's name, and the writer had no table to talk about.

**Evidence.** The episode 14 script had 41 turns, with four-result roundups in the ACB, the
Champions League and LaLiga, and every selected story told. Unit tests cover the shares (exact
sum, brief, major), one sabotage per plan rule, and the retry and fallback path.

---

## D38 · The show's format comes from the listener's interests

**Status:** Accepted · **Date:** 2026-09-29 · **Confirms:** D22

**Context.** The author described the sample's format: the Barça sections first, each followed by
its competitions, national league before Europe (Barça football, LaLiga, Champions League, Barça
basketball, Liga ACB, EuroLeague), then the NBA. The product must stay generic.

**Decision.**
- The engine stays generic (D22): each interest is a section, a team with several sports gives
  one section per sport, and each section's weight is its interest's weight. The sections follow
  sport, then weight, then the order in which the listener added the interests. The show's name
  comes from the settings. The rules in the prompts speak of "the listener's team"; Barça only
  appears in their examples.
- The sample's format is the demo listener's configuration: FC Barcelona (high), then LaLiga,
  the Champions League, the Liga ACB and the EuroLeague (medium), and the NBA (low), added in
  that order. The show is "Barça & Beyond", 5 minutes.
- The catalog offers the Barça universe because those are the competitions with reliable
  official sources and player-level detail. Another club would mean adding its interests and
  sources to the catalog.

**Alternatives considered.**
- *A fixed Barça format in configuration, with a flag and a weight per section:* it would
  duplicate the interests and make the product Barça-only.

**Trade-offs.** A team's two sports cannot yet be chosen separately (for example, Barça football
without Barça basketball). That needs a data-model change and belongs to the web app step.
*Resolved in Step 8 (D51):* Barça football and Barça basketball are two catalogue sections, each
with its own switch and weight.

**Evidence.** The demo listener's interests were re-created in this order on 2026-09-29 through
the API. On 2026-09-28 the author had chosen the Champions League before LaLiga; he changed it so
both sports follow the same pattern.

---

## D39 · The writer turns the plan into a conversation between two fans

**Status:** Accepted · **Date:** 2026-09-29 · **Revises:** D7 (the writer's instructions) ·
**Revised:** 2026-09-30 (Step 10)

**Context.** The writer's instructions had grown one rule at a time during the sample test runs,
and together they produced a news wire: "Now, basketball.", a full date on every result, an
intro that listed every section, "one short sentence per result", and the team's full name on
every mention.

**Decision.** The style and structure part of the writer's prompt was rewritten, not extended:
- **Roles:** the host drives the show and asks the analyst real questions; the analyst explains
  why it matters and never reads out lists of results.
- **Structure from the plan (D37):** each section tells its lead story in three to five turns,
  then one roundup line and what comes next; a brief section gets one line. The intro opens with
  the hook, says which day it is, welcomes the listener and introduces both hosts by name, and
  teases two or three stories. Sections are bridged with the plan's threads or a short handoff.
  The closing starts with the listener's team's next game.
- **Conversation:** every turn answers, builds on or pushes back on the previous one; short
  reactions mixed with explanations; at most two numbers per turn; a genuine question from the
  host in each section; one or two mild disagreements; limits on stock openers and spoken
  markers; the names fans use; players named whenever the sources name them.
- **Kept as they were:** facts only from cited sources, "never compute numbers", the number
  format, the Spanish glossary and the audio tag format. Two rules were tightened: a description
  of how a game went counts as a fact for the judge too, and days are said with their labels
  (D34). Tags: about one every four or five turns, so the cap rises from 6 to 8.
- The writer only receives the sources the plan cites, and the structure checks follow the
  plan: the intro cites the hook, and each section cites its lead story and every roundup result.
- A turn may cite any source of the episode, not only its own section's, so it can refer back to
  what an earlier section told. Numbers, scores and the judge are still checked against what each
  turn cites. In the first regeneration of episode 14, the old per-section rule rejected eight
  correct turns.

**Alternatives considered.**
- *Adding rules on top of the old ones:* several old rules produced the wire style, so they had
  to go, not be counterweighted.
- *Giving the writer every source:* it would drift back to telling everything the sources say.

**Trade-offs.** Conversational rules (turns that respond, genuine questions) cannot all be
checked by code; the deterministic ones are linted (D40), the rest are reviewed by reading the
script.

**Evidence.** The episode 14 script, reviewed by the author on 2026-09-29. Unit tests check what
the writer receives (plan, only the cited sources) and each structure check with a sabotage.

**Revised on 2026-09-30 (Step 10): the day in the intro comes from code.** A manual run from the web
app on a Wednesday (episode 2438) showed that the intro rule's example, "It's Monday", was written by
hand. The writer copied it literally, and the judge rightly rejected the turn as the wrong day. The
check records show the same on a Tuesday (episode 24) and in that morning's end-to-end run (episode
2437); the sample was generated as of a Monday, so it matched by chance. Each time it cost a rewrite.
In episode 2438 the rewrite repeated it, the repaired turn failed the judge for another reason and
was removed, so the episode opened without its welcome. The example now carries the episode's
weekday, written by code with the same `episode_day` and day name as the episode context (D34). The
checks had kept the wrong day off the air; the fix removes the error at its source instead of
relying on them every time. Evidence: the check records of episodes 24, 2437 and 2438; the writer
test asserts the weekday of a Thursday episode and fails with the old example.

---

## D40 · Style lint, length control and a record of every episode

**Status:** Accepted · **Date:** 2026-09-29 · **Revises:** D7 (the check stage), D19 (length)

**Context.** Some of the new conversation rules (D39) can be checked by code, and the length is
the contract with the listener: they chose 3, 5 or 7 minutes. The sample test runs came out at
82% to 111% of the target, because models cannot count characters. Rewriting text costs cents;
regenerating audio costs voice credits.

**Decision.**
- **Style lint (code):** no full calendar date spoken; at most two stock openers and three spoken
  markers in the episode; at most two numbers per turn, a score counting as one; the analyst
  never reads out two or more scores; no section longer than 1.5 times its share.
- **Length (code):** the total must be within 10% of the target. Over it, the model is asked to
  trim, roundup lines first, then the weakest section, never the lead stories' key facts. Under
  it, only sections below 80% of their share are expanded, with analysis of their plan facts and
  no new facts; if none is short, a short episode is accepted (D19). A script more than 25% over
  still fails the episode, which protects the voice credits.
- **One revision for everything:** style and length problems go into the same single rewrite as
  the factual ones (D7). After it, factual problems still fail the episode; style and length
  problems remain as warnings in the check details and in the runner's output, instead of
  looping.
- **A record of every episode,** in the master stage details: planned, script and spoken
  characters; estimated and measured speech seconds, and the measured characters per second, to
  calibrate each voice; and the number and cost of the paid calls, for the language model and for
  the voice, across all attempts.

**Alternatives considered.**
- *Failing the episode on style:* a stock phrase too many is not worth losing an episode or
  paying for a loop.
- *A second rewrite for style:* it doubles the writing cost for small gains.
- *Asking the model to count characters:* measured unreliable.

**Trade-offs.** The lint covers only what code can see; whether turns really answer each other is
judged by reading. Some warnings will reach the voice.

**Evidence.** Measured lengths of the sample test runs: 82% (episode 4), 111% (10), 104% (11),
86% (12), 90% (13) and 107% (14). One unit test per lint rule, one for each length case, and one
for the per-episode counters.

**Known issue, found with the sample (2026-09-29), to fix with the dashboard (Step 9), before
delivery:** the voice
counters include the free development voice, whose calls are recorded as "elevenlabs" at $0.
Episode 23 reports 6,777 voice characters: 3,824 from the tone voice, plus 2,953 really billed. The
counters must separate real voice, cached segments and the development voice.

**Resolved on 2026-09-30 (Step 9).**
- The tone voice is a local stand-in, not a provider, so it no longer returns a provider call, and
  `provider_calls` only holds what a provider bills. A data migration deleted the 88 old tone rows
  (37,164 characters at $0). Episodes and stage records were left untouched: their checksums were
  the same before and after the migration.
- The voice stage records which voice spoke and the characters generated, billed and reused from
  the cache. The episode record adds the voice and the reused characters.
- ElevenLabs now shows the 2,953 characters episode 23 really billed. A voice preview of 871
  characters, made before the full take and reused by it from the cache, was paid outside the
  product's records; the project's own cost log counts it.
- Records written before the fix are kept as they were; the dashboard reads `provider_calls`.
- Evidence: a test that the tone voice leaves no provider call and keeps its stage history, a test
  that a retried voice stage reports everything reused, a migration test with real rows, and four
  sabotages. In the end-to-end run of Step 9, the voice stage recorded 3,927 tone characters, 0
  billed.

---

## D41 · Episodes can be regenerated as of a past moment

**Status:** Accepted · **Date:** 2026-09-29 · **Revised:** 2026-09-29 (Step 8)

**Context.** To judge a pipeline change, the author wanted the episode 14 script regenerated with
the same date and the same news window, and compared with the original.

**Decision.** The runner accepts `--as-of <ISO time>`. The episode is generated as if it were
that moment: it is the "now" of the run (the episode's day, the day labels of D34 and the news
window of D23), the fetch stage does not run, and news published after it is left out. Official
data is the latest stored, since it only changes when games are played. The episode's own start
and finish times stay real.

**Alternatives considered.**
- *Snapshotting the database:* heavy for a comparison of two scripts.
- *Filtering data by the time it was fetched:* a refreshed data item (D33) is stamped with the
  refresh time, so the results would disappear from the window.

**Trade-offs.** Data refreshed after that moment is used as it is now: fine between rounds, not
across one.

**Evidence.** Between the original episode 14 (2026-09-28, 21:32 UTC) and its regeneration, no
LaLiga, Champions League, EuroLeague or ACB game was played. A unit test checks that no fetch
runs, the plan carries the given time, and later news stays out.

**Revised on 2026-09-29: a database snapshot keeps that moment across rounds.** `--as-of` filters
news by publication time, but official data is the latest stored, and some items are rewritten in
place: once EuroLeague round 2 is played, its fixtures item loses the games already played, and
new results and standings enter a catch-up. Before the worker ingested anything new, a `pg_dump`
of the development database was taken and restored as a separate database. Running the same
runner against it with `--as-of` reproduces the sample's inputs (D45). The alternative rejected
above, a snapshot, became necessary once new rounds would be ingested; it needs no product code.

**Note, 2026-09-29 (Step 8).** The app shows when an episode's news was selected (`news_as_of`),
so a regenerated episode shows its past moment rather than the day it was generated (D53).

---

## D42 · The plan keeps the source's framing, and a rejected turn is repaired, not the episode

**Status:** Accepted · **Date:** 2026-09-29 · **Revises:** D7 (what fails an episode), D37

**Context.** The second regeneration of episode 14 failed on one sentence: "Kevin Punter led
Barça with 19 points". The source said Punter was Barça's best player by valuation (PIR 22), with
19 points; it did not say he was the top scorer. The editorial plan had changed the meaning while
rephrasing, the sentence read well even to a person, the writer copied it, and the judge rejected
it, rightly. One unsupported turn failed a whole episode whose other turns were checked and
correct.

**Decision.**
- **The plan keeps the source's framing.** The editor is told that a fact is stated exactly as
  its source frames it (a best player by rating is not a top scorer; "reportedly" stays), with at
  most two numbers per fact and three facts per section (five for a major story), so it gives
  points, not stat lines.
- **A rejected turn is repaired, not the episode.** Problems are split in two. Problems of the
  whole script (segment order, too many tags, the hook or a lead story not covered, more than 25%
  over the length) still ask for one full rewrite and fail the episode if they stay. Problems of
  one turn (a number or a score not in its cited sources, a verdict from the judge) no longer do:
  only those turns are rewritten, with their reasons, their sources and the turns around them,
  and the judge checks only those turns again. A turn that is still wrong is removed and
  recorded. The episode fails only if a section loses its lead story, or a segment is left
  empty. An unsupported fact still never reaches the voice: it is fixed or its turn goes.

**Alternatives considered.**
- *Checking the plan with the judge before writing:* one more paid call on every episode, for a
  problem the turn check already catches.
- *A second full rewrite:* about $0.04 more each time, and a full rewrite brings new errors: the
  Punter sentence itself survived one.
- *Removing rejected turns without trying to repair them:* it would drop facts that only needed
  rewording, such as "Punter was Barça's best performer, with 19 points".

**Trade-offs.** A removed turn can leave a small gap in the conversation. The repair adds a small
paid call (a few turns and their sources) and a partial judgement, only when a turn fails.

**Future improvements, not required for delivery** (the product meets the brief without them, and the
repair plus a read of every script cover the variability):
- *Judging twice and keeping the majority:* the judge is itself a model and varies between runs. In
  episode 13 it flagged two sentences that it approved on the retry.
- *Guaranteeing the freshest story of each section in code:* the extra candidate usually lets it
  through, but in episode 22 the selection model still chose an older NBA story.
- *Counting a season ("2013/14") as one number* in the plan's two-numbers-per-fact rule: it caused
  retries of the plan.
- *Trimming what the plan reads* (D37).

**Evidence.** Episode 18: plan fact "Kevin Punter led Barça with 19 points, one rebound, one
assist and a PIR of 22" [S14]; source S14: "Best player of each team by valuation (PIR): Kevin
Punter (FC Barcelona): 19 points, 1 rebound, 1 assist, PIR 22". Unit tests cover a repaired turn,
a removed one (for each failing verdict), a lost lead story that fails the episode, and a
whole-script problem that still fails after the rewrite.

**Revised elsewhere on the same day, after episode 18:**
- *D37:* the roundup keeps at most two results, and only those that matter to the listener's team
  (a direct rival, an upcoming opponent) or are truly outstanding. Select passes one more
  candidate per section to the plan, so a club's report or the freshest story is not lost for
  lack of a slot: episode 18 missed the club's report of the 119–101 win, and the NBA section
  took a Friday story over Monday's media day.
- *D39:* each section's target is given in characters and in turns, computed by code (about 115
  characters per turn, a target between the 93 of episode 14 and the 146 to 171 of episodes 13,
  16 and 18). Episode 18 came out at 129% of the target. New rules: a short radio-style intro to
  each section instead of narrated transitions; at most one or two questions from the host per
  section; each host says the other's name at most twice; clear positions, one hedge per episode;
  each upcoming game once in its section and once in the closing; only stats that make a point;
  the analyst also says hello and goodbye.
- *D40:* the lint checks the hedges, the host's questions, the names and the analyst in the
  intro and the closing.
- Official data no longer shows a "Published" date: for data, that date is when it was stored, not
  what it describes, and a table refreshed on the 29th read as "tomorrow" in a run as of the 28th.
- LaLiga player names that are abbreviations with a dot ("J.david") are replaced by the full name
  ("Jonathan David").

---

## D43 · Code picks each section's next game, and results are told the way fans tell them

**Status:** Accepted · **Date:** 2026-09-29 · **Revises:** D33, D37, D39, D40

**Context.** Episode 20 was the first regeneration that passed and sounded like a podcast. Reading
it, the author found five general problems:
- each section's "next up" was the first game of the round (Lens–Sporting, Joventut–Andorra,
  Paris–Partizan), and the listener's own games in the Champions League and the Liga ACB were
  missing from the whole episode;
- "Paris" was PSG in the Champions League and Paris Basketball in the EuroLeague;
- "Raphinha scored all 3 against Sevilla" never said the result was 3–1;
- facts were listed like a match report, and a section ended by announcing the next one ("Now,
  LeBron in Philadelphia.");
- the editor's first answer failed validation, and only the problems of the last attempt were
  recorded.

**Decision.**
- **Code picks the next game.** The official fixtures already store every game. Section by
  section, in episode order, the next game is the listener's team's earliest game in the
  section's fixtures that no earlier section has given; if its only game was already given (the
  league game, told in the club's own section), nothing. If the team is not in those fixtures but
  is in the section's table, it is the earliest game of the team just above or just below it. If
  the listener follows no team, there is none. The editor no longer chooses it; it sees it in its
  prompt.
- **Names that keep the sport clear.** In UEFA data, a name abbreviated with a dot uses the
  short name spelled out ("Slovan Bratislava"), and a small table maps names that are ambiguous
  across sports to the fans' name ("Paris" → "PSG"). In EuroLeague data, a club whose full name is
  its city plus "Basketball" or "Basket" uses it ("Paris Basketball", "Dubai Basketball",
  "Valencia Basket"); the other full names carry sponsors, so the short name stays.
- **Fans' vocabulary, written by code.** Goal data labels two goals by one player "a brace" and
  three "a hat-trick" (penalties count, own goals do not), as it already writes the totals (D33).
  The judge then finds the word in the source instead of having to infer it from the count.
- **The writer's prompt, rewritten in place (D39):** a result is told with its score before it is
  discussed; facts are told the way a fan tells a friend, with the fans' words when the data
  supports them, and never with added colour ("stunning", "comeback") that no source states; each
  turn makes one point; each section opens itself and never ends by announcing the next one; a
  club's name is never shortened to one that could mean a club in the other sport.
- **Lint (D40):** the first turn that cites an official result, outside the intro and the
  closing, must say its score. Like the other style rules, it goes into the single rewrite and
  then stays as a warning.
- **The editor's attempts are recorded.** The select stage details keep the problems of every
  attempt, not only the last one.

**Alternatives considered.**
- *Telling the editor to pick the listener's team's game:* the rule was already implied ("through
  the eyes of a fan of the listener's team"), and the editor still took the first game listed.
  The fixtures are structured data, so code can decide it exactly.
- *A rival's game when the team's game was already told:* early in a season the table does not
  say who a rival is (after one EuroLeague round, half the teams were 1–0), and it would bring back
  games the listener does not care about.
- *UEFA's official names ("Paris Saint-Germain", "Galatasaray A.Ş."):* unambiguous, but formal
  and awkward to say.
- *Letting the judge infer "hat-trick" from "Raphinha 3":* probably accepted, but a rejected turn
  would be removed, and the label costs one line of code.

**Trade-offs.** A listener who follows no team gets no "next up". The name table is kept by hand,
like the pronunciation dictionary (D35). The score lint can trigger the rewrite more often, about
$0.05 each time.

**Evidence.** Episode 20 script and plan (2026-09-29). Measured the same day: the UEFA match and
standings data carry `translations.shortName` ("S. Bratislava" → "Slovan Bratislava", "B.
Dortmund" → "Dortmund") and `displayOfficialName`; the EuroLeague games and standings carry
`name` ("Paris Basketball", "Partizan Mozzart Bet Belgrade"). A dry run on the stored data as of
episode 20's moment gave: Barça football → Getafe, LaLiga → none, Champions League →
Galatasaray–Barcelona, Barça basketball → Dubai Basketball–FC Barcelona, Liga ACB → UCAM
Murcia–Barça, EuroLeague → none, NBA → none. Unit tests cover the next game (the team's game given
once, a direct rival, no team), the names, the goal labels, the score lint and the recorded
attempts.

---

## D44 · Records keep their scope, sections are linked, and a script can be re-checked

**Status:** Accepted · **Date:** 2026-09-29 · **Revises:** D7, D39, D42

**Context.** Episode 22 was chosen as the base for the sample, with four problems left:
- its intro said "an ACB opener with the third-highest score ever", while the source said the
  third-highest total in a league opener. As with Punter (D42), summarising lost the scope and
  changed the meaning, and the judge approved it;
- sections started from scratch ("In LaLiga…", "In the Champions League…"), with few links
  between them and little back-and-forth inside them;
- to fix the intro without rewriting the script, the check had to run again, but the runner
  skips it once it has passed;
- in episodes 20 and 22, the judge's second look at a repaired LaLiga turn came back without a
  verdict for it, and the turn was removed. In a re-check, the same thing could remove the
  intro's welcome.

**Decision.**
- **Records keep their scope.** The judge is told that records and superlatives ("ever", "best",
  "first", "record", "led", "only", "most") keep exactly the scope of their source, and that a
  turn that widens or changes it is overstated. The editor keeps a record's scope when it
  rephrases a fact, and the intro never compresses a record: it says it with its scope or leaves
  the figure out.
- **Linked sections and more back-and-forth.** Rewritten in place in the writer's prompt, with
  the author's wording:
  - each section's first turn picks up a thread, a contrast or the listener's team, and no two
    sections open the same way;
  - one bridge line when the episode moves from one sport to the other, and a short lead-in to
    the closing;
  - a bridge links content and never describes the show's structure;
  - the analyst reacts before adding, the host builds on the analyst's point, and there are
    never two fact-only turns in a row.

  This replaces the short radio-style intro to each section (D42).
- **`runner <id> --recheck`.** It checks an existing script again with the current checks in a
  repair-only mode: one round of code checks and the judge; failing turns are repaired as usual
  (D42); whole-script, style and length problems stay as warnings and never trigger a full
  rewrite. There is no fetch; voice and master follow.
- **A missing verdict is asked again.** When the judge leaves turns without a verdict, it is asked
  once more about those turns only. If a verdict is still missing, the reason records the ids the
  judge did return. Returned ids are also cleaned of brackets and spaces.
- **A regenerated episode releases its audio while it runs.** The database requires "completed if
  and only if it has audio" (D25), so an episode that already had audio clears it when it starts
  again. The re-check test found this; the real voice for a script first voiced with the tone
  would have hit the same error.

**Alternatives considered.**
- *Regenerating episode 22 to fix one sentence:* it would change everything else.
- *Editing the sentence by hand:* the sample must come from the product.
- *Reusing the normal check for a re-check:* its full rewrite would change the whole script as
  soon as a style rule fired.
- *A code check for superlatives:* comparing scopes needs language understanding; that is the
  judge's job.

**Trade-offs.** A second question to the judge costs about $0.002, and only when a verdict is
missing. Conversation rules are still checked by reading, not by code. A re-check that fails
leaves the episode without its previous audio pointer, although the file stays on disk until the
new one is written.

**Evidence.** Episode 22: intro "the third-highest score ever"; source S18 "3ª mayor anotación
en un estreno liguero". Episodes 20 and 22: the partial judgement of the repaired turn returned 83
and 123 output tokens and no verdict for it. Unit tests cover the scope rules in the prompts,
the second question to the judge (including a bracketed id), the repair-only mode, and a
re-check of a completed episode end to end.

---

## D45 · The sample is the best episode the product generated, and it can be reproduced

**Status:** Accepted · **Date:** 2026-09-29

**Context.** The brief asks for "a sample.mp3 file in the repo with the best podcast episode
you've managed to generate using the product". Text is cheap to regenerate (cents); a
five-minute voice take costs about 3,800 ElevenLabs characters, from a shared account whose limit
cannot be read.

**Decision.**
- **Iterate on the text, voice it once.** Each weakness found by reading a script was fixed in the
  product, as a general rule with a test in a commit, and the episode was generated again. Never
  a script or audio edited by hand, and never code for one episode.
- **Same moment for every version.** All regenerations ran as of Monday 28 September, 23:32 in
  Madrid (`--as-of`, D41), so versions compare the same news and data. That is why the episode
  says "It's Monday" and "tomorrow" means Tuesday the 29th.
- **Chosen by reading.** Every fact of the finalists was checked against its sources, sentence by
  sentence. Episode 23 won over episode 22 on links between sections and conversation, at the
  cost of some striking details (Balcerowski's 21 points without a miss, the record since 1990):
  at a fixed length, naturalness and data density compete.
- **Voice preview first.** The intro and the section with the hardest names (871 characters) were
  voiced through the product's own voice functions into its voice cache. After listening, the
  full take ran with the runner and reused them, paying 2,953 more characters.
- **Kept outside the cache:** the master, its nine segments, the script and a manifest (commit,
  `--as-of`, chapters, loudness, characters and sha256 of each segment); and a database snapshot
  (D41), so a later version can be compared on the same inputs. Only `sample.mp3` goes to the
  repository.

**Alternatives considered.**
- *The first episode that passed the checks:* it read like a news wire.
- *Editing a sentence by hand:* the sample would not be the product's output.
- *Voicing every text candidate:* about $0.38 each, against cents for text.
- *Generating the sample from the web app with the day's news:* a real test of the whole flow,
  planned as a final validation, but not comparable with the earlier versions.

**Trade-offs.** Twelve paid text runs in Step 7: eleven generations and one re-check, about $1.29
of OpenAI, including three failed runs that each led to a general fix. Judging by reading is subjective; the checks guarantee facts, not
style. The voice's naturalness is left as an improvement (D46).

**Evidence.** Episodes 10 to 14 (28 September) and 16, 18, 20, 22 and 23 (29 September), with
their scripts and costs in the work log. Episode 23: 3,781 characters, 293.6 seconds, −16.4 LUFS,
all facts checked. The committed `sample.mp3` is byte-identical to the file the pipeline wrote
(sha256 `874c74ee…`).

---

## D46 · Audio: ElevenLabs MP3 at 128 kbps, mastered in one pass

**Status:** Accepted · **Date:** 2026-09-29 · **Confirms:** D6

**Context.** The master stage joins the voice segments with fixed silences and normalises the
loudness to the podcast standard: −16 LUFS integrated, true peak at most −1 dBTP (D6). Two
options were planned for testing with the sample: loudness normalisation in one or two passes,
and a final MP3 at 128 or 192 kbps. While listening, the author also found Sarah's replies
somewhat disconnected, so the pauses were measured.

**Decision.**
- **ElevenLabs delivers `mp3_44100_128`.** According to ElevenLabs' official agent skill, PCM needs
  the Pro plan and MP3 at 192 kbps the Creator plan, and the key cannot read its plan (401).
- **The master stays as it is:** one ffmpeg pass with `loudnorm` in its default dynamic mode
  (−16 LUFS, true peak −1.5 dBTP, LRA 11), then MP3 at 128 kbps. The sample measures −16.4 LUFS
  and −1.8 dBTP.
- **The A/B test changed nothing,** because nothing improved. It was run with ffmpeg alone on the
  same saved segments, so it cost no credits.
  - Two passes would measure first and then apply one fixed gain. Here that gain (+0.72 dB) would
    take the true peak from −0.43 to +0.29 dBTP, over the limit, so `loudnorm` falls back to
    dynamic mode and the result measures the same.
  - 192 kbps makes the file 50% larger. The source is already 128 kbps, so quality does not
    come back.
  - The product's own output was reproduced byte for byte.
- **Pauses measured, not changed.**
  - Speaker changes inside a segment last about 1 second (George to Sarah 1.01 s on average,
    Sarah to George 0.99 s), and they come from ElevenLabs.
  - The master only adds 0.4 s between segments, 0.5 s at the start and 1 s at the end, and it
    does not lengthen any pause (−0.004 s on average).
  - A speaker change across two segments therefore lasts about 0.45 s, half of one inside a
    segment.
  - Shortening those one-second gaps in the master is the first optional improvement: it is free,
    it serves every episode, and it needs no new voice.

**Alternatives considered.**
- *Two passes with a limiter before them:* one more processing stage for no measured gain.
- *192 kbps, or PCM from ElevenLabs:* larger for no gain, and PCM is not available to this key.
- *Trimming the pauses now:* it changes the master and its chapter times, and the sample was
  already approved. It is left for the end.

**Trade-offs.** Dynamic normalisation adjusts the gain over time, which is slightly less faithful
to the original dynamics than one fixed gain. The MP3 is encoded twice (by ElevenLabs and by the
master), a loss that is hard to hear in speech. The one-second gaps between speakers stay.

**Evidence.** ffmpeg `ebur128` measurements of the four variants, and `silencedetect` at −40 and
−50 dB on the nine original segments and on the master. Speakers were told apart by pitch (George
about 115 to 140 Hz, Sarah about 200 to 220 Hz); all 25 speaker changes of the script were found.

---

## D47 · The worker: one polling loop, a short claim and a graceful stop

**Status:** Accepted · **Date:** 2026-09-29

**Context.** Episodes must be generated on schedule with nobody pressing a button. A generation
takes one to three minutes (measured: 41 s to 2 min 48 s) and pays for OpenAI and ElevenLabs calls.
The process will be stopped on purpose (it is how the worker is paused) and it can die (a crash,
`kill`, a power cut).

**Decision.** `app/worker.py` is a single process. Every `WORKER_POLL_SECONDS` (10 s) it:
1. **Recovers stuck episodes:** an episode `in_progress` for more than 30 minutes becomes `failed`
   ("Interrupted…"), and its running stages become `failed` ("interrupted"). It is one
   `UPDATE … RETURNING` that re-checks the status, so an episode finishing at that instant is not
   overwritten. It goes by age, not "every episode in progress", because another worker or a
   manual run may be working for real. A retry resumes from the last checkpoint (D3).
2. **Schedules** the episodes that are due (D48).
3. **Claims one queued episode** with `SELECT … FOR UPDATE SKIP LOCKED`, oldest first, checks the
   spending cap (D48) and runs the pipeline. The row lock lasts until the pipeline's first commit
   marks the episode `in_progress`: no provider call is ever made while holding it.
4. **Ingests the catalogue** every three hours (D24), after the episode: what a listener is waiting
   for goes first.

Around the loop:
- **Graceful stop.** Docker stops a container with SIGTERM. The worker's handler only sets a flag:
  the loop finishes the episode in progress, starts nothing new (not even a due ingest) and exits
  with code 0. Idle waits are one-second steps that check the flag. Compose waits up to
  `stop_grace_period: 10m` before SIGKILL. `docker compose kill worker` stops at once; step 1 then
  recovers the episode.
- **A stage only counts as completed if it finishes.** Found while designing the stop: an
  interruption that is not an `Exception` (Ctrl+C, a process stop) went past the stage's error
  handling, and the stage was recorded as `completed`. For `check`, a retry then skipped the judge
  and paid for voice on an unchecked script. A stage now starts as `failed`/`interrupted`.
- **Resilience.** An unexpected error in an iteration (a database restart) is logged with its
  trace, and the next iteration retries.
- **In Docker.** The worker is its own Compose service behind `profiles: [worker]`, so
  `docker compose up` never spends credits. It uses the image target with ffmpeg (D29) and shares
  the `appdata` volume (`/data`) with the API. Without the keys it needs, it exits with code 1 and
  names them, instead of restarting in a loop.
- **A fresh HTTP fetcher per task**, closed afterwards, so a process that lives for days re-reads
  each `robots.txt` (D30).

**Alternatives considered.**
- *FastAPI's `BackgroundTasks` for "Generate now"* (added in the Step 10 review): the task runs
  inside the API process after the response is sent, so it dies with that process, has no retry
  and ties minutes of paid work to the web server; and it cannot serve the schedule, where there is
  no request to attach it to. A separate worker reading the queue covers both.
- *Claiming with a single `UPDATE … RETURNING` in the worker:* equivalent. The pipeline already
  marks the episode `in_progress` and commits at once, so the lock is just as short, and only one
  place changes that status.
- *Leases, heartbeats or advisory locks to detect a dead worker at once:* precise, but more moving
  parts. With one worker, a 30-minute age (ten times the longest run measured) is enough.
- *PostgreSQL `LISTEN`/`NOTIFY` to wake the worker the moment an episode is queued:* removes the
  10-second wait, but a notification sent while nobody is listening is lost, so polling would still
  be needed as the fallback. It is a later improvement, not a replacement.
- *Stopping at once on SIGTERM* (raising from the handler): the episode could stop anywhere,
  including mid-commit. Finishing the current task is what Celery's warm shutdown does.
- *A `threading.Event` for the idle wait:* shorter, but `set()` from a signal handler takes a
  lock, and it can deadlock if the signal arrives while the same thread holds it.
- *Starting the worker with `docker compose up`:* a reviewer would spend credits just by running
  the app.
- *A Compose restart policy:* with missing keys it would restart forever; the loop already
  survives errors. Production deployment is future work.

**Trade-offs.**
- Polling adds up to 10 s before a queued episode starts, and one small query every 10 s.
- A worker killed hard blocks that listener for up to 30 minutes.
- The scheduler reads every listener's settings on every iteration: fine for hundreds; at scale,
  each listener's next run would be stored and indexed.
- The ingest clock lives in memory, so every restart ingests again (free GETs, about 1.5 minutes).
- Stopping can take minutes while an episode is running.

**Evidence.**
- *Measured on 2026-09-29, in Docker:*
  - a Python process 1 without a SIGTERM handler ended with code 137 (SIGKILL); with a handler,
    code 0 in 0.7 s;
  - the idle worker stopped in 2.2 s, and a worker in the middle of its ingest waited about 51 s,
    then exited with code 0;
  - a stop requested while the script was being written: the episode completed 75 s later, no
    ingest started, and the process exited with code 0;
  - the first ingest took 95 s, and `docker compose down` without the profile leaves the worker's
    container (hence `docker compose --profile worker down`).
- *Tests:*
  - two real database connections claim two different episodes, and a third gets none, without
    waiting;
  - with the old stage code, the interruption test fails ("check" recorded as `completed`).
- *Sources:*
  - PostgreSQL on `SKIP LOCKED` (see D2), and Supabase's `lock-skip-locked` and
    `lock-short-transactions` rules (read, not installed);
  - Celery: "When shutdown is initiated the worker will finish all currently executing tasks
    before it actually terminates";
  - Compose: `stop_grace_period` defaults to 10 s, and a service with profiles "is only started
    if the profile is activated".

**Revised on 2026-09-30 (Step 10).** Runs grew longer than the "one to three minutes" above once
the pipeline had its editorial plan and repair step, a fresh ingest and real voice: from the
worker in Docker, 176 seconds (test tone, Step 6), 216 and 273 seconds (test tone, from the web
app) and 302 seconds with the real voice, 139 of them in the voice stage. The 30-minute stale age,
the 30-minute lead (D48) and the 10-minute stop grace period still cover the longest run.

---

## D48 · When episodes are made, and how much they may spend

**Status:** Accepted · **Date:** 2026-09-29

**Context.** Each listener sets days, a time and an IANA time zone. The machine running the worker
may be off at that time. Credits are limited and their balance cannot be read (D11), and the worker
runs unattended.

**Decision.**
- **The slot is computed in the listener's time zone.** 07:00 in Madrid stays 07:00 across
  daylight saving changes (05:00 UTC in summer, 06:00 UTC in winter).
- **A 30-minute lead** (set in the definition, Step 1): the 07:00 episode is queued from 06:30, so
  it is ready at 07:00 (the longest run measured is about 3 minutes). `scheduled_for` stays the
  delivery time, which the dashboard compares with `finished_at` to measure punctuality.
- **Catch-up:** only the *latest* slot whose lead has begun is created, and only if it is less
  than 12 hours old *and* later than the moment the listener last saved their settings
  (`podcast_settings.updated_at`). It never builds a backlog: like systemd's `Persistent=`, a missed
  run triggers once. Starting the worker, or changing the schedule, never creates this morning's
  episode. A time that has not arrived yet does count: saving a 07:00 schedule at 06:45 queues it
  at once, because that is the episode being asked for.
- **Only listeners with interests** are scheduled, as the API requires for "Generate".
- **No duplicates.** A `SELECT` first skips listeners who already have that slot or an episode in
  flight. `INSERT … ON CONFLICT DO NOTHING` is the guarantee: with no conflict target it covers both
  the unique `(user_id, scheduled_for)` and the one-in-flight partial index, and a test proves it.
  The `SELECT` also matters because an insert that conflicts still consumes an identity value:
  without it, episode ids would jump by thousands. A manual episode in flight at the scheduled time
  delays the scheduled one. If nothing is new by then, it ends `skipped` at no cost (D19, D23).
- **Voice:** `WORKER_VOICE=tone` by default, so the worker never spends ElevenLabs credits unless
  real voice is enabled. "Generate" only asks for the ElevenLabs key when it is. The API and the
  worker share one rule for the required keys (`Settings.missing_generation_keys`).
- **Spending cap:** `WORKER_DAILY_BUDGET_USD` (default $1.00) over any rolling 24 hours, summing
  every paid call in `provider_calls`, including manual runs. It is checked before an episode
  starts. If it is reached, the episode becomes `failed` with the reason, and it can be retried
  later. An episode that starts under the cap can exceed it by its own cost: about $0.06–0.24 for
  the text, plus about $0.37 for 5 minutes of real voice.
- **Demo:** the real schedule. The time is set a couple of minutes ahead: it is later than the
  save and its lead has begun, so the worker, which polls every 10 seconds, starts it at once.
  There is no special demo mode.

**Alternatives considered.**
- *Starting at the scheduled time:* every episode would arrive a few minutes late.
- *Generating every missed slot:* stale briefings, paid for one after another.
- *Skipping missed slots:* a restart at 06:59 would lose that day's episode.
- *Counting slots from before the schedule was saved:* starting the worker at 15:00 would
  immediately generate, and pay for, that morning's episode.
- *A dedicated `schedule_updated_at` column:* a more precise anchor, at the cost of a migration
  (see the trade-offs).
- *A calendar-day cap:* needs a time zone decision, and allows a burst around midnight.
- *Keeping capped episodes queued until there is budget:* the listener is blocked (409) and does
  not see why.
- *A demo mode that generates every N minutes:* a path production never takes, and it spends on
  every round.

**Trade-offs.**
- `updated_at` changes with any setting, so renaming the show after a missed slot cancels that
  catch-up. The next slot is at most a week away, and a day away on a daily schedule.
- A capped episode counts as `failed`. The dashboard should separate it by its reason (Step 9).
- A fresh clone produces a tone, not voices, until `WORKER_VOICE=elevenlabs` is set.
- News published in the 30 minutes before the scheduled time waits for the next episode.

**Evidence.**
- *Tests:* the daylight-saving change, the lead (06:29 no, 06:31 yes), a schedule saved two
  minutes ahead, a slot 13 hours old, a slot before the settings were saved, and the conflict on
  the partial index. Removing the lead, either catch-up rule, or the 30-minute age of D47, makes
  its test fail.
- *In Docker on 2026-09-29:* the last 24 hours showed $1.44 of spending, so "Generate" (episode 24)
  failed with "Daily spending cap reached: $1.44 of $1.00 in the last 24 hours", with no attempt, no
  stage and no paid call. With the cap raised for the test, the retry completed: 300.3 s,
  −16.5 LUFS, $0.0628.
- *systemd's `Persistent=`:* "the service unit is triggered immediately if it would have been
  triggered at least once during the time when the timer was inactive".

**Revised on 2026-09-30 (Step 10).** The real voice was exercised once from the worker in Docker
before delivery: `WORKER_VOICE=elevenlabs` in a local `.env`, "Generate now" from the web app, six
`eleven_v3` requests (3,390 characters, $0.339) and the master in the container. The run took 302
seconds (D47), well inside the 30-minute lead, and the setting went back to the tone afterwards.

---

## D49 · The web app is served by FastAPI from the same image

**Status:** Accepted · **Date:** 2026-09-29

**Context.** The brief asks for a UI where the user sets their interests and customises the
podcast. D1 and D9 chose a React SPA served by FastAPI. Step 8 had to decide how it is built,
typed, served and shipped in Docker, so that a reviewer still only runs `docker compose up`.

**Decision.**
- **Stack (D1):** React 19, TypeScript, Vite 8, Tailwind 4 and shadcn/ui, created with the shadcn
  CLI (Vite template, `base-nova` style on Base UI). TanStack Query for server state, React Router
  8 in declarative mode, Vitest for the one piece of pure logic that needs tests (D52).
- **Typed client:** `openapi-typescript@7` generates `src/api/schema.d.ts` from FastAPI's OpenAPI
  document, run with `npx` (`npm run api:types`) and committed, so building the image needs no
  running API. A thin `fetch` wrapper (`src/api/client.ts`) uses those types; it asks for JSON and
  turns FastAPI errors (`detail` as text or as a validation list) into one message.
- **Serving:** `app.frontend("/", directory=…)` (FastAPI 0.141). Its routes rank below the API:
  a built file is served as is, and an unknown path falls back to `index.html` only for browser
  navigations (`Accept: text/html`). Opening or refreshing `/settings` or `/internal` loads the
  app, while an unknown `/api/…` fetch still gets a JSON 404. It is registered only if the build
  exists, so tests and the Vite dev server still work.
- **Docker:** the build context is the repository root, and a root `.dockerignore` is an
  **allowlist** (`*`, then only `backend/app`, `backend/migrations`, `backend/pyproject.toml`,
  `frontend` and `sample.mp3`), so `.env` and `data/` can never reach a build. A `node:24-slim`
  stage runs `npm ci` and `npm run build` (type check included) and only `dist/` is copied into
  the `api` image. The image keeps the repository layout under `/app` (`/app/backend`,
  `/app/frontend/dist`, `/app/sample.mp3`), so one `ROOT` constant resolves the same paths inside
  and outside Docker.
- **Development:** `npm run dev` proxies `/api` to `http://127.0.0.1:8000` (not `localhost`,
  which tries IPv6 first on Windows).

**Alternatives considered.**
- *`openapi-fetch`:* it would also type the paths, but it is one more dependency for about twelve
  calls kept in one file.
- *`StaticFiles` plus a catch-all route:* the manual version of what `app.frontend()` does, and
  easy to get wrong for API 404s.
- *A second build context (`additional_contexts`) instead of building from the root:* keeps
  `backend/` as the context but is less familiar and still needs `sample.mp3`.
- *A denylist `.dockerignore`:* a new file in the root would be sent by default.
- *Committing `dist/`:* generated code in the repository, out of date after every change.

**Trade-offs.**
- The first `docker compose up` also installs npm packages and builds the web app (about a
  minute, once; cached afterwards). The `api` image grows from 445 MB to 456 MB.
- The generated types must be regenerated when the API changes; a CI job diffing them is a
  future improvement.
- No hot reload inside Docker; the Vite dev server provides it.

**Evidence.** FastAPI 0.141.1's `_is_frontend_navigation_request` (read in its source) and three
tests (`test_frontend.py`). Playwright with the system Chrome: `/`, `/settings`, `/internal` and
an unknown path, opened directly and refreshed, on desktop and mobile: 16 of 16, with no console
errors. JavaScript bundle: 388 KB, 124 KB gzipped. The template's `tsc --noEmit` checked nothing
(a solution-style `tsconfig.json` with `"files": []`), so `typecheck` runs `tsc -b`.

---

## D50 · Two screens and a minimal custom player

**Status:** Accepted · **Date:** 2026-09-29

**Context.** A listener opens the app to hear today's episode, trust it and tune it. The owner
approved a visual direction on a static mock before the screens were built.

**Decision.**
- **Episodes (`/`):** the show header with "Generate now" and the next scheduled time; the player
  of the chosen episode; the episode list; then the transcript and its sources. The list is
  polled every 3 seconds only while an episode is queued or in progress, and it shows the running
  stage ("writing the script"), the reason of a skipped or failed episode, "Retry", and a hint to
  start the worker if an episode stays queued for over a minute.
- **"Generate now" knows before the click** (`GET /api/v1/generation`): without keys it is
  disabled and says which key is missing; with the default test-tone voice (D48) it says so. The
  API still enforces both.
- **Settings (`/settings`):** the sections first (switch and weight per catalogue topic, own
  keyword topics, and the running order computed by the API), saved as they change; then the show,
  the two hosts and the schedule, saved with one button (`PUT`), with the API's validation message
  shown when it rejects a field.
- **Player:** play/pause, current time and length, and the **chapter track** as the progress bar
  and the way to jump. Each chapter is a segment as wide as its duration and coloured by sport.
  An invisible native range input sits over the segments: click, drag and keyboard work (arrows
  jump 5 seconds). Nothing else: no speed, volume or download controls.
- **Design:** one family, Archivo, with its width axis (condensed for titles, like broadcast
  captions); ink `#16213a`, paper `#f6f7f9`, pitch green `#2e7d5b` for football, court orange
  `#c9702c` for basketball. The colour means the sport everywhere: track, transcript, settings and
  running order. Light theme only. Fonts are self-hosted (fontsource, OFL).
- **Transcript and sources:** speaker names from the settings, audio tags removed, and each
  citation (S3) linked to its source; only cited sources are listed, marked "Official data" or
  "Official".

**Alternatives considered.**
- *The browser's `<audio controls>`:* simpler, but it looks different in every browser, clashes
  with the dark player and cannot show chapters.
- *Server-sent events or WebSockets for progress:* a live channel for a list that changes a few
  times per episode; polling only while something runs is enough.
- *Toasts for errors:* one more component; an inline alert next to the action is clearer.
- *A dark mode:* the template's theme provider was about 150 lines for no product need.

**Trade-offs.**
- Host names come from the current settings: renaming a host later also renames them in old
  transcripts (the script stores the role, not the name).
- Polling costs a request every 3 seconds per open tab while an episode runs.
- The chapter labels are hidden on narrow screens; the player then shows the current chapter.

**Evidence.** Playwright runs against the real API: play sends a `play` event, 16 seconds of
audio send one heartbeat; the arrow key jumps 5 seconds; clicks land in the right chapter (78.6 s
→ 79 s after the 1 px thumb fix; 1–2 s early before it); keyboard focus is visible on the button
and the track. Every settings action was exercised and the data restored. The pressed toggle
state was invisible with the light palette, so `toggle.tsx` was adapted (pressed = ink).

---

## D51 · Barça football and basketball are two sections of the catalogue

**Status:** Accepted · **Date:** 2026-09-29

**Context.** FC Barcelona was one catalogue topic with two sports, which code split into a
football block and a basketball block, sharing one weight. The owner wanted to follow each one on
its own.

**Decision.**
- **Every catalogue topic has one sport** (`Topic.sport`). FC Barcelona becomes
  `fc-barcelona-football` and `fc-barcelona-basketball`, the same keys its blocks already had, so
  the sample's chapters and sources keep matching. Each section reads the club's official site
  filtered to its sport and the competitions of its sport (LaLiga and the Champions League, or the
  EuroLeague and the ACB).
- **A data migration** turns each `fc-barcelona` interest into both sections, with the same
  weight and the same creation time, so they stay next to each other. Its downgrade merges them
  back without losing someone who follows only basketball. The limit goes from 6 to 8 interests
  (the 7 topics plus one of the listener's own).
- **Sharing airtime is per section** (D19): the D'Hondt quotient is counted per block, with the
  same tie-break as before.
- **The running order is derived, not chosen:** weight, then the order the sections were added,
  grouped by sport (D22). `GET /api/v1/interests` returns the list in that order, computed by the
  pipeline's own functions (`by_priority`, `sport_order`), so the app never shows an order the
  episode does not follow.

**Alternatives considered.**
- *One topic with a sports option:* a new column and a more complex form for one club.
- *Keeping the two sections as one "club" for airtime:* it would ignore the weights the listener
  sets on each section.
- *A manual order with up and down arrows:* a `position` column, an endpoint and changes in
  selection, for control that weights already give.

**Trade-offs.**
- Two sections at high weight can take more airtime than the old single interest. With the
  sample's weights and news in all seven sections, the 5-minute allocation is identical (a test
  proves it); if a section had no news, its spare slot could go to a Barça section instead of a
  competition.
- The Monday snapshot used to reproduce the sample (D45) must be migrated after restoring it
  (`alembic upgrade head`).

**Evidence.** Tests for the new registry rule, the sample allocation and the data migration with
real rows (a sabotaged migration fails it). The development database was migrated: the demo
listener's order and chapters still match the sample.

---

## D52 · Listening events: one heartbeat per 15-second slot actually played

**Status:** Accepted · **Date:** 2026-09-29

**Context.** The product metrics (D8) need to know what was actually heard: a stream is at least
60 seconds, an engaged listen at least 40 % of the episode, counting distinct 15-second slots of
the episode (`position // 15`).

**Decision.**
- **Table `listen_events`:** `episode_id` (cascade delete, indexed), `kind` (`play` or
  `heartbeat`), `position_seconds` (a check keeps it non-negative) and `created_at`. It stores no
  `user_id` (the listener is the episode's owner) and no `is_synthetic` flag (simulated data will
  be marked on the user, Step 9), so nothing is stored twice. Confirmed by the owner.
- **`POST /api/v1/episodes/{id}/listen-events`** returns 204, only for completed episodes (409
  otherwise). The path is kebab-case, the usual style for multi-word URL paths.
- **The player's counter** (`src/lib/listening.ts`) splits the episode into the same fixed
  15-second slots the dashboard counts. It remembers which whole seconds of the episode have
  actually played (a set, so a second is remembered once), and when all the seconds of a slot
  have played, allowing one missing second, it sends **one** heartbeat with the **slot's start**
  (0, 15, 30…). Only steps of up to 5 seconds count as playback, and a seek resets the baseline,
  so it measures audio time (double speed counts the same) and pauses and jumps add nothing.
  `play` is sent when playback starts.
- **Replays never count twice:** remembered seconds are not added again, two partial passes over
  the same seconds do not complete a slot, and a slot is sent once per session. Across sessions
  the same slot arrives with the same position, and the dashboard counts distinct slots.

**Alternatives considered.**
- *A heartbeat every 15 seconds of wall clock* (the Step 1 wording): at double speed it would
  skip half the slots.
- *A heartbeat every 15 seconds of accumulated audio, with the current position* (the first
  version in this step): after a jump back, its positions no longer line up with the fixed slots,
  so replaying could add one extra slot, and two partial passes could add up to a full one.
- *A heartbeat on entering each slot:* pressing play and pausing at once would count a slot.
- *Batching events or `sendBeacon` on page close:* more robust delivery, more code; not needed
  for a demo with simulated volumes.

**Trade-offs.** Only whole slots count: a slot heard for 10 of its 15 seconds adds nothing, so a
session can under-count by up to one slot at each end. Events are fire-and-forget: one lost on a
network error is not retried. Without authentication, any client could post events;
authentication is a future improvement (D27).

**Evidence.** Eight Vitest tests: slots reported once with their start, audio time at double
speed, a replayed slot counted once, two partial passes not adding up, a small jump, big or
backward steps, a pause, and the shorter last slot. Removing the sent-slot memory fails six of
them, including the replay test; removing `seek()` fails the small-jump test. In the browser,
with the real audio: after 16.19 s, one heartbeat at 0; after jumping back to 0.47 s and playing
the same slot to 16.12 s, no new heartbeat.

---

## D53 · A fresh install shows the sample episode, without keys

**Status:** Accepted · **Date:** 2026-09-29

**Context.** A reviewer runs `docker compose up` with no `.env`. The app must show something real
at once, without spending, and only generating should need keys (D10).

**Decision.**
- **Prestart seeds the demo listener only on a fresh database:** "Barça & Beyond" (5 minutes,
  casual, daily at 07:00 Madrid time), its seven sections in the sample's order, and the sample
  episode. If the demo user already exists, nothing is touched, so a deleted interest does not come
  back on restart.
- **The episode comes from the real one:** `scripts/export_sample.py` exports episode 23 (title,
  times, script, chapters, plan and its 35 linked sources) to `app/sample_episode.json`, and the
  seed copies `sample.mp3` into the data volume (`demo/sample.mp3`).
- **Sources are stored without the outlets' text:** headline, link, date and outlet only; the text
  of official *data* (results, standings, fixtures, written by this project's code from official
  data) is kept. Selection ignores any article without text, so a seeded source can never back a
  claim.
- **`news_as_of`:** the API exposes when an episode's news was selected (the plan's
  `selected_at`). The sample was generated on Tuesday as of Monday 23:32 in Madrid (D41), and its
  script says "It's Monday", so the app shows that moment instead of the generation time.

**Alternatives considered.**
- *A database dump as the seed:* opaque and tied to one schema version.
- *Storing the full article text:* it redistributes outlets' content in a public repository.
- *A special demo mode:* a code path production never takes.
- *Reseeding on every start:* it would undo the reviewer's own changes.

**Trade-offs.**
- A seeded news URL is never rewritten by ingestion (news rows are insert-only), so that article
  stays without text. Those stories are days old by the time anyone runs the app.
- The export must be run again if the sample changes. Ids differ from the development database
  (the sample is episode 1 in a fresh install, 23 here).

**Evidence.** Three tests (`test_demo.py`): a fresh database serves the sample through the API
with chapters in the running order and the same audio bytes; seeding twice changes nothing; an
existing demo user is left alone. A clean run of the public copy with no `.env` showed the
sample, 4,698,322 audio bytes (the size of `sample.mp3`), the missing key, and a 503 on
"Generate".

---

## D54 · Dashboard metrics are computed in SQL from one definition of a listen

**Status:** Accepted · **Date:** 2026-09-30 · **Builds:** D8, on the events of D52

**Context.** The dashboard has to show whether the product works for listeners and how the
pipeline behaves. The player sends a `play` event and one heartbeat per 15-second slot actually
heard (D52). The metrics must agree with each other and be defensible one by one.

**Decision.**
- **One base, one row per completed episode** (`LISTENS` in `app/metrics.py`):
  - when it was first played;
  - how much was heard: distinct 15-second slots, the last one counting only its real length;
  - when that crossed 60 seconds (a *stream*, Spotify's definition) and 40% of the episode (an
    *engaged listen*, Apple's).
  - Replaying a slot or skipping ahead cannot change it, and an episode counts at most once.
- **Product, all from that base:**
  - engaged listens per week, the North Star (Monday to Sunday, UTC, dated when the listen
    crossed 40%);
  - weekly engaged listeners;
  - the funnel and the average share heard, over episodes ready between 28 days and 24 hours ago,
    so each had a day to be heard;
  - activation: a new listener's first episode heard engaged within 24 hours;
  - the drop-off curve: the share of played episodes that heard each tenth of the episode;
  - topics: of the played episodes that reached a section, how many heard its last slot;
  - cohorts: an engaged listen on days 0–6 and 21–27 after signup, counted only once that week
    has passed;
  - on-time delivery: scheduled episodes, once resolved, ready by their time. Manual and skipped
    episodes are left out, and a failed one counts as late.
- **Operations** read `stage_runs` and `provider_calls`:
  - outcomes, with spending-cap stops kept apart from failures;
  - cost per completed episode that has run records;
  - runs, success, p50 and p95 duration and cost per stage (each stage talks to one provider, so
    stage failures are provider failures);
  - failures grouped by the stage that stopped them;
  - the 20 latest runs;
  - the spend of the last 24 hours, from the worker's own function (real users only).
- **Counts, not percentages, in the API:** the page divides and shows "—" when there is no base.
- **Thresholds are backend constants,** passed to SQL text as bound parameters.

**Alternatives considered.**
- *Computing in Python after loading the events:* it moves every event to the app; the database
  aggregates next to the data.
- *A SQL view:* the thresholds would be hard-coded in a migration.
- *Engaged listens per topic (Step 1):* see D8's revision.

**Trade-offs.**
- Long SQL strings: named CTEs make them readable, but they are not type-checked, so every
  definition has a test.
- The funnel and the topics leave out the last day.
- A section shorter than one slot is not measured.
- A slot heard for 10 of its 15 seconds adds nothing (D52).

**Evidence.** Nine tests on hand-built data with known answers. Each one has a sabotage that breaks
its definition in the SQL and makes it fail:
- distinct slots and the 24-hour window;
- "≥" at exactly 60 seconds and at exactly 40%;
- the shorter last slot;
- the week in which the listen crossed 40%;
- activation within 24 hours;
- finished sections;
- cohort eligibility;
- scheduled-only delivery;
- the simulated-data switch;
- cap stops kept apart;
- cost only with run records.

The product tab takes 0.16 s over about 1,200 simulated episodes. In the end-to-end run of Step 9,
the listen heard to 45% appeared as one engaged listen in the current week.

---

## D55 · Simulated data lives in the same tables, marked on the user

**Status:** Accepted · **Date:** 2026-09-30 · **Builds:** D8, D52

**Context.** The brief allows mocked data. A dashboard needs weeks of listeners to mean anything,
and a reviewer without keys should see it at once. Real events must go through the same queries.

**Decision.**
- **`users.is_synthetic`** marks simulated listeners; everything they own inherits the mark, so
  nothing is stored twice (D52).
- **`app/synthetic.py` builds them deterministically** from a fixed seed and the moment of seeding:
  - 69 listeners who sign up over 8 weeks, and about 1,200 episodes;
  - calibrated on this project's own runs: average tokens and latency per call, the pipeline's
    prices, 12.4 characters of speech per second and $0.10 per 1,000 characters, so a completed
    episode costs about $0.45;
  - invented patterns: drop-off in the first two minutes, some sections skipped more than others,
    listening that fades with the weeks, 30% who stop listening while episodes keep coming, a
    group of curious sign-ups who barely listen, and a few replays.
- **Seeded by the prestart job** on a fresh database (about 10 seconds, once).
  `python -m app.synthetic --reset` recreates them as of now.
- **The worker ignores them** when scheduling, when claiming and in the spending cap. They have no
  settings or interests, so they would never be scheduled anyway; the guards are a second line of
  defence, each with a test.
- **The page says the data is simulated,** and a switch hides it.

**Alternatives considered.**
- *A database dump:* opaque and tied to one schema version.
- *A separate demo database:* the queries would not be tested on real rows.
- *A flag on every row:* the same fact stored many times.
- *Random numbers without calibration:* the operations tab would show invented costs and timings.

**Trade-offs.**
- The simulated weeks end on the day of seeding: an old install shows old weeks until `--reset`.
- Simulated completed episodes point to an audio path that does not exist; the app never serves
  them.
- The listening patterns are invented; only the costs and timings come from measurements.

**Evidence.**
- Three tests: the data is deterministic, every row follows the product's rules, and seeding and
  deleting touch only simulated users.
- Three worker tests with sabotages.
- The tests caught a real bug in the generator: a heartbeat at second 300 of a 300-second episode.
- A clean install without `.env` seeded the 69 listeners on its first start, and a restart seeded
  none.

---

## D56 · The internal dashboard: its own API and page, and retries for real runs only

**Status:** Accepted · **Date:** 2026-09-30 · **Builds:** D8, D9, D27

**Context.** The team needs the metrics of D54 in a page, and a way to act on a failed run.
Listeners must not pay for the team's tools.

**Decision.**
- **API under `/api/v1/internal`:**
  - `GET /product` and `GET /operations`, with `?include_simulated=`;
  - `POST /episodes/{id}/retry`: it needs the keys (503), refuses simulated episodes (409) and
    otherwise requeues the episode with the same function as the listener's retry.
- **The page `/internal`,** linked on the right of the menu:
  - one filter row with the simulated-data switch, and two tabs;
  - charts with shadcn's chart component (Recharts 3), each with a table view;
  - values readable without hovering;
  - one validated colour for single series;
  - percentages that never show 100% or 0% unless exact.
- **Loaded only when opened** (`React.lazy`): the listener's app stays at 390 KB (125 KB gzipped),
  and the dashboard is a separate 391 KB file.
- **No login:** everything under `/internal` can be protected by a team role once authentication
  exists (D27).

**Alternatives considered.**
- *Metabase or Grafana* (D8): one more service.
- *Retrying only from the listener's endpoint:* the team could not act on another listener's run.
- *Filters inside each chart:* numbers from different slices on one page.
- *Charts in the main bundle:* it doubled the JavaScript every listener downloads.

**Trade-offs.**
- The dashboard is open to anyone who reaches the app, like the rest of it (D27).
- Opening it loads a second file.
- On a phone, the wide tables scroll horizontally inside their cards.

**Evidence.**
- Four API tests, one with a sabotage.
- Playwright on both tabs, desktop and phone, with and without simulated data: no console errors
  and no page overflow.
- **An end-to-end run** (2026-09-30), from "Generate now" in the page through the worker (tone
  voice) to the dashboard:
  - the episode completed, 321 seconds of audio;
  - $0.1471 of OpenAI, no ElevenLabs call and no other episode created;
  - a listen to 45% in the browser became this week's engaged listen, and the run appeared with its
    cost and stages.

---

## AI tooling: agent skills

Agent skills are instruction packs for Claude Code. They are installed per project, only in the
step that needs them, after reading their `SKILL.md`, and they are removed when they stop being
useful.

| Skill | Source | Step | Why | What it contributed |
|---|---|---|---|---|
| `documentation-and-adrs` | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) · MIT · 42.6K installs | 2, kept in 3 to 5 | Writing these records | The Status and Date fields, and the rule to supersede records instead of deleting them. It adapted to this file's existing format. |
| `fastapi` | [fastapi/fastapi](https://github.com/fastapi/fastapi/tree/master/fastapi/.agents/skills/fastapi) · MIT · official · 10.7K installs | 4 | Current conventions from FastAPI's maintainers | `Annotated` dependency aliases (`SessionDep`, `CurrentUser`), return types instead of `response_model`, the prefix and tags on each `APIRouter`, `def` endpoints for blocking database code, and when a `yield` dependency closes. Its SQLModel, uv and ty advice was set aside on purpose (D1, D15). |
| `shadcn` | [shadcn-ui/ui](https://github.com/shadcn-ui/ui/tree/main/skills/shadcn) · MIT · official · 351K installs | 8 | Using shadcn/ui components the way their authors intend | Forms built from `FieldSet`, `Field` and `FieldLabel`; `ToggleGroup` for 2 to 7 options (length, tone, weight, days); `Badge` and `Alert` instead of custom markup; semantic colour tokens. Its preset name `base-nova` was out of date: the current CLI accepts `nova` and records `base-nova`. |
| `frontend-design` | [anthropics/skills](https://github.com/anthropics/skills/tree/main/skills/frontend-design) · 934K installs | 8 | A design direction that does not look templated | A token plan (palette, one type family, layout) reviewed against common generated looks; one bold element (the chapter track) with everything else quiet; self-critique from screenshots, which found the unreadable pressed state and the episode list lost below a long transcript. |
| `dataviz` | Bundled with the Claude Code environment (not installed in the project) | 9 | Chart design with checks instead of taste | Form before colour (stat tiles and one hero figure where the data is a single number; no dual axis); its script validated the chart colours against the card surface (`#2a78d6` for single series; `#86b6ef` as the lighter step for the week in progress, 2.11:1; a one-hue scale for cohort cells, with text at 6.4:1 or more); a table view for every chart; the previous render kept while refetching. |

**Evaluated and not installed:**
- `github/awesome-copilot@create-architectural-decision-record` (MIT, 10.1K installs): it
  enforces one file per record and coded bullet IDs, which is noise for short records.
- `openai/skills` → `openai-docs`: built for Codex, and it depends on an MCP server and a helper
  script. The official OpenAI docs are read directly instead.
- `elevenlabs/skills@text-to-speech` (official, MIT, 12.3K installs), Step 3: it does not cover
  text-to-dialogue, and it recommends request stitching, which v3 does not support. It also
  reads the cost from a different header from the one the API returned in our tests
  (`character-cost`).
- `bytedance/deer-flow@podcast-generation` (MIT, 2.3K installs), Step 3: it is tied to its own
  agent environment and text-to-speech script.
- `supabase/agent-skills@supabase-postgres-best-practices` (official, MIT, 419K installs), Step 4:
  read, and its schema rules are cited in D25. It was not installed: its long description is loaded
  on every message, and several rules do not apply here, such as row-level security, cursor
  pagination (D12) and idempotent `DO` blocks, which Alembic does not need.
- Step 5, after reading each `SKILL.md`, no new skill was installed; `fastapi` and
  `documentation-and-adrs` were kept:
  - `affaan-m/ecc@cost-aware-llm-pipeline` (MIT, 9.4K installs): generic, with Anthropic examples;
    what it proposes (a model per task, recording the cost of each call) is already in D5 and D11;
  - `refoundai/lenny-skills@ai-evals` (MIT, 2K installs): mostly podcast quotes; the useful part,
    measuring a judge on labelled examples, is already in D20;
  - `wshobson/agents@python-testing-patterns` (MIT, 33.6K installs): basic pytest patterns
    already in use;
  - `digitalsamba/claude-code-video-toolkit@ffmpeg` (MIT, 9.3K installs): built for video.
- Step 7: no new skill; `fastapi` and `documentation-and-adrs` were kept. The official
  `elevenlabs/skills@text-to-speech` was read again for its output formats (PCM needs the Pro plan,
  MP3 at 192 kbps the Creator plan), which set the audio format (D46). It was not installed, for the
  same reasons as in Step 3.
- Step 6: no new skill; `fastapi` and `documentation-and-adrs` were kept. Searched for a Postgres
  queue, Docker Compose and background workers. `supabase-postgres-best-practices` was read again,
  and its `lock-skip-locked` and `lock-short-transactions` rules are cited in D47.
  `affaan-m/ecc@docker-patterns` (12.4K installs) is generic and says nothing about signals or
  profiles. `github/awesome-copilot@multi-stage-dockerfile` (27.4K installs) is about compiling in
  one stage and shipping from another, while here the stages only split what each service needs.
- Step 8: `shadcn` and `frontend-design` were installed (above). `vercel-labs/agent-skills@web-design-guidelines`
  (680K installs) was left out by the owner; `vercel-react-best-practices` (753K) targets Next.js;
  the TanStack Query skills are community-made with few installs (11.8K and 8.9K); and
  `antfu/skills@vite` (36.6K) covers a configuration of a few lines. For visual checks,
  `anthropics/skills@webapp-testing` and `microsoft/playwright-cli@playwright-cli` were read: the
  first amounts to writing Python Playwright scripts, plus a server helper that Docker makes
  unnecessary; the second is a 0.x CLI that grants itself shell permissions. Playwright's Python
  API was used directly, with the system Chrome.
- Step 9: `dataviz` was used (above), and `shadcn` and `frontend-design` were kept. Searches for dashboards, Recharts,
  SQL analytics and product metrics returned mostly unrelated skills. `wshobson/agents@kpi-dashboard-design`
  (14.8K installs, community) was read: a generic guide to SaaS KPIs (MRR, churn), with nothing for metrics
  that were already defined.
- Step 10 (the delivery documents): no new skill; `documentation-and-adrs` was kept. A search for README
  skills returned `anthropics/skills@doc-coauthoring` (87.3K installs), described as a guided co-writing
  workflow; the README and this repository's `solution.md` summarise records that already exist, so it
  was not installed.
