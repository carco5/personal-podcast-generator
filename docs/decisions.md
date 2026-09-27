# Architecture decisions

Each record has a status, a date, the context, the decision, the alternatives considered, the
trade-offs and the evidence behind it. Records are never deleted: if a decision changes, a new
record supersedes the old one and both stay here.

| # | Decision | Status |
|---|---|---|
| D1 | [Stack: FastAPI + PostgreSQL + React/TypeScript](#d1--stack-fastapi--postgresql--reacttypescript) | Accepted |
| D2 | [The `episodes` table is the job queue, drained by one worker](#d2--the-episodes-table-is-the-job-queue-drained-by-one-worker) | Accepted |
| D3 | [A staged pipeline with checkpoints, using the provider SDKs directly](#d3--a-staged-pipeline-with-checkpoints-using-the-provider-sdks-directly) | Accepted |
| D4 | [News sources behind a `NewsProvider` interface](#d4--news-sources-behind-a-newsprovider-interface) | Accepted |
| D5 | [One OpenAI model per task](#d5--one-openai-model-per-task) | Accepted |
| D6 | [Voice: ElevenLabs v3 text-to-dialogue](#d6--voice-elevenlabs-v3-text-to-dialogue) | Accepted, validated in Step 3 |
| D7 | [Check the script before paying for voice](#d7--check-the-script-before-paying-for-voice) | Accepted |
| D8 | [Internal dashboard: product and operations](#d8--internal-dashboard-product-and-operations) | Accepted |
| D9 | [Frontend: a single-page app served by FastAPI](#d9--frontend-a-single-page-app-served-by-fastapi) | Accepted |
| D10 | [Runs locally with Docker Compose, including without API keys](#d10--runs-locally-with-docker-compose-including-without-api-keys) | Accepted |
| D11 | [Cost-aware development](#d11--cost-aware-development) | Accepted |
| D12 | [REST conventions aligned with Prosper's public API](#d12--rest-conventions-aligned-with-prospers-public-api) | Accepted |
| D13 | [Two fixed, configurable hosts](#d13--two-fixed-configurable-hosts) | Accepted |
| D14 | [Record the sample episode before building the web app](#d14--record-the-sample-episode-before-building-the-web-app) | Accepted |
| D15 | [Repository layout, Python version and tooling](#d15--repository-layout-python-version-and-tooling) | Accepted |
| D16 | [Configuration and secrets](#d16--configuration-and-secrets) | Accepted |
| D17 | [PostgreSQL 18 in Compose](#d17--postgresql-18-in-compose) | Accepted |
| D18 | [Measure with a throwaway spike before building the pipeline](#d18--measure-with-a-throwaway-spike-before-building-the-pipeline) | Accepted |
| D19 | [An episode is shorter rather than padded](#d19--an-episode-is-shorter-rather-than-padded) | Accepted |
| D20 | [Every check is proven by a sabotage test, and the judge is measured](#d20--every-check-is-proven-by-a-sabotage-test-and-the-judge-is-measured) | Accepted |
| D21 | [Episodes of 3, 5 or 7 minutes, and a 5-minute sample](#d21--episodes-of-3-5-or-7-minutes-and-a-5-minute-sample) | Accepted |
| D22 | [The episode follows the listener's priorities](#d22--the-episode-follows-the-listeners-priorities) | Accepted |
| D23 | [What an episode covers: what is new, or a catch-up the first time](#d23--what-an-episode-covers-what-is-new-or-a-catch-up-the-first-time) | Accepted |
| D24 | [Sources are ingested on a schedule and stored](#d24--sources-are-ingested-on-a-schedule-and-stored) | Accepted |

---

## D1 · Stack: FastAPI + PostgreSQL + React/TypeScript

**Status:** Accepted · **Date:** 2026-09-26

**Context.** The product needs a user-facing UI, a backend that pulls news and generates audio on
a schedule, and an internal dashboard. Prosper's own stack is FastAPI, PostgreSQL and
React/TypeScript.

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

**Evidence.** Prosper's job postings and its public OpenAPI document, which is served by FastAPI.
PyPI (SQLModel 0.0.47, SQLAlchemy 2.1). The FastAPI SQL tutorial points to Alembic for
production migrations.

---

## D2 · The `episodes` table is the job queue, drained by one worker

**Status:** Accepted · **Date:** 2026-09-26 · **Revised:** 2026-09-27

**Context.** Episodes are generated on a per-user schedule. A generation takes minutes and calls
paid APIs, so it must survive restarts and must never run twice for the same slot.

**Decision.** There is no separate jobs table. An episode row carries `status` (`queued` →
`in_progress` → `completed` / `failed`), `scheduled_for` and `attempts`, and
`UNIQUE(user_id, scheduled_for)` prevents duplicates. One worker loops over three tasks: every
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
Revised on 2026-09-27 to add the ingest task (D24).

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
ElevenLabs API pricing and the GenFM documentation.

---

## D4 · News sources behind a `NewsProvider` interface

**Status:** Accepted · **Date:** 2026-09-26 · **Revised:** 2026-09-27

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
| FC Barcelona (football and basketball) | fcbarcelona.com, English articles sitemap | The league sources below, filtered by the team's names |
| EuroLeague | The EuroLeague API | Eurohoops, Sportando |
| Liga ACB | acb.com game reports and news, in Spanish (recent-news sitemap and news listing) | None needed |
| NBA | None reachable: nba.com returns HTTP 403 | ESPN, CBS Sports |
| Champions League | uefa.com news sitemap | The Guardian (`football/championsleague`) |
| LaLiga | None usable: laliga.com's `robots.txt` disallows its news pages | The Guardian (`football/laligafootball`) |

Free-text topics use keywords over the catalogue and, with a key, the Guardian.

**Alternatives considered.**
- *Official sources only:* the NBA's and the EuroLeague's websites block automated access (HTTP
  403 and 429), so there would be no NBA block and no EuroLeague stories beyond the data.
- *acb.com's results and standings pages:* they load their data from an undocumented internal API.
  The official game reports carry the same results and the players' figures.
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
  across languages.
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

---

## D5 · One OpenAI model per task

**Status:** Accepted · **Date:** 2026-09-26 · **Revised:** 2026-09-27

**Context.** Three stages use a language model: selecting stories and checking the script's
claims (D7), which are classification tasks, and writing the script, where quality is audible.

**Decision.** `gpt-6-sol` writes the script, and `gpt-6-luna` selects the stories and checks the
claims. Both are
settings, not hard-coded values (D16). `gpt-6-astra` is kept only as an option to try on the
sample episode.

**Alternatives considered.**
- *`gpt-6-astra` for writing:* about five times the price of `gpt-6-sol`.
- *`gpt-5.6-sol`:* twice the price of `gpt-6-sol`.

**Trade-offs.** Some writing quality compared with `gpt-6-astra`.

**Evidence.** [OpenAI pricing](https://developers.openai.com/api/docs/pricing). The real cost
per episode is measured in the Step 3 spike and recorded per call (D11). Revised on 2026-09-27,
when the claim check became a required stage (D7).

---

## D6 · Voice: ElevenLabs v3 text-to-dialogue

**Status:** Accepted, validated in Step 3 · **Date:** 2026-09-26, validated 2026-09-27

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

---

## D7 · Check the script before paying for voice

**Status:** Accepted · **Date:** 2026-09-26 · **Revised:** 2026-09-27

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

---

## D8 · Internal dashboard: product and operations

**Status:** Accepted · **Date:** 2026-09-26

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

---

## D9 · Frontend: a single-page app served by FastAPI

**Status:** Accepted · **Date:** 2026-09-26

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

---

## D10 · Runs locally with Docker Compose, including without API keys

**Status:** Accepted · **Date:** 2026-09-26

**Context.** Reviewers must be able to run the project with one command, and the API keys belong
to Prosper.

**Decision.** `docker compose up` starts the database, a one-off migration job, the API and the
worker. The `.env` file is optional (`required: false`). Without keys the app still loads with
the sample episode, the simulated dashboard and the full UI. Only "Generate" needs keys, and it
explains which one is missing. The database port is not published.

**Alternatives considered.** *A public deployment:* a public URL could spend the provider credits
without control.

**Trade-offs.** No URL to try the app without Docker. Deployment and authentication are future
work.

**Evidence.** Docker Compose documentation: since Compose 2.24.0, an `env_file` entry with
`required: false` is ignored when the file is missing.

---

## D11 · Cost-aware development

**Status:** Accepted · **Date:** 2026-09-26

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

---

## D12 · REST conventions aligned with Prosper's public API

**Status:** Accepted · **Date:** 2026-09-26 · **Revised:** 2026-09-27

**Context.** The reviewers build and maintain a public REST API. Following their conventions where
they are consistent makes this API familiar to them.

**Decision.**
- `/api/v1/` prefix and `GET /api/v1/health`, as in Prosper's API.
- `page` + `limit` pagination, as in Prosper's call-log listing.
- An endpoint to retry a failed episode, similar to Prosper's `rerun-failed` webhooks endpoint.
- Episode status values `queued`, `in_progress`, `completed` and `failed`, in one consistent
  style. This is the job lifecycle of GitHub's Checks API (`queued`, `in_progress`, `completed`)
  plus `failed`.

**Alternatives considered.**
- *Copying Prosper's status values:* they differ between resources (for example `In Progress` and
  `Failed` for campaign targets, `IN_PROGRESS` and `COMPLETED` for cases), so there is no single
  convention to copy.
- *`page_size` pagination:* common elsewhere, but Prosper uses `limit`.

**Trade-offs.** None significant.

**Evidence.** Prosper's public OpenAPI document (`voice.getprosperapp.com/openapi.json`), checked
on 2026-09-27. [GitHub Checks API](https://docs.github.com/en/rest/checks/runs): `status` is
`queued`, `in_progress` or `completed`. Revised on 2026-09-27 after re-checking the OpenAPI
document: pagination there uses `limit`, and status values are not shared across resources.

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

**Status:** Accepted · **Date:** 2026-09-26 · **Revised:** 2026-09-27

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

**Status:** Accepted · **Date:** 2026-09-27

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

**Status:** Accepted · **Date:** 2026-09-27

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

**Trade-offs.** Tools on the host cannot reach the database until a development override
publishes a port. That is decided in Step 4, together with migrations.

**Evidence.**
- Compose docs: `compose.yaml` is the preferred filename, and the `version` element is
  "obsolete".
- [PostgreSQL image docs](https://hub.docker.com/_/postgres): from 18, `PGDATA` is
  `/var/lib/postgresql/18/docker` and the volume is `/var/lib/postgresql`.
- Local check on 2026-09-27: `data_directory` is `/var/lib/postgresql/18/docker`, there is no
  anonymous volume, and a row survives `docker compose down` followed by `up`.

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

**Status:** Accepted · **Date:** 2026-09-27

**Context.** The user chooses an episode length, but some days bring little news for an interest.
A model asked to fill a fixed length with thin material pads it out: it repeats itself or adds
claims that no source supports.

**Decision.** The chosen length is a target, not a quota.
- The episode plan gives each interest a share of the length by weight, capped by the fresh
  material it has.
- An interest with no fresh material is left out of that day's episode.
- If no interest has fresh material, the episode is not generated, and the reason is recorded
  without spending on voice.

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

---

## D20 · Every check is proven by a sabotage test, and the judge is measured

**Status:** Accepted · **Date:** 2026-09-27

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

**Status:** Accepted · **Date:** 2026-09-27

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

---

## D23 · What an episode covers: what is new, or a catch-up the first time

**Status:** Accepted · **Date:** 2026-09-27

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

---

## D24 · Sources are ingested on a schedule and stored

**Status:** Accepted · **Date:** 2026-09-27

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

---

## AI tooling: agent skills

Agent skills are instruction packs for Claude Code. They are installed per project, only in the
step that needs them, after reading their `SKILL.md`, and they are removed when they stop being
useful.

| Skill | Source | Step | Why | What it contributed |
|---|---|---|---|---|
| `documentation-and-adrs` | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) · MIT · 42.6K installs | 2, kept in 3 | Writing these records | The Status and Date fields, and the rule to supersede records instead of deleting them. It adapted to this file's existing format. |

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
