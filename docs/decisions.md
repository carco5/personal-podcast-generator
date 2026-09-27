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
| D6 | [Voice: ElevenLabs v3 text-to-dialogue](#d6--voice-elevenlabs-v3-text-to-dialogue) | Accepted, chunking to be validated in Step 3 |
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

**Status:** Accepted · **Date:** 2026-09-26

**Context.** Episodes are generated on a per-user schedule. A generation takes minutes and calls
paid APIs, so it must survive restarts and must never run twice for the same slot.

**Decision.** There is no separate jobs table. An episode row carries `status` (`queued` →
`in_progress` → `completed` / `failed`), `scheduled_for` and `attempts`, and
`UNIQUE(user_id, scheduled_for)` prevents duplicates. One worker loops over two tasks: it
schedules due episodes (`INSERT … ON CONFLICT DO NOTHING`), then claims one queued episode and
runs the pipeline. Claiming uses `SELECT … FOR UPDATE SKIP LOCKED`, so more workers can be added
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

**Status:** Accepted · **Date:** 2026-09-26

**Context.** The brief asks the backend to pull news "from APIs or scraping outlets' websites".
Every fact in the script must be checkable against the text it came from, so sources must provide
full article text.

**Decision.** Three providers share one interface:
- **RSS feeds**, with the text from `content:encoded`, or extracted from the page with
  trafilatura when the feed does not include it;
- the **official EuroLeague API**, for exact results and schedules;
- the **Guardian Open Platform**, optional (it needs a free key), for any free-text topic.

Catalogue topics map to curated feeds (for example, NBA = ESPN + CBS Sports). Free-text topics use
keywords.

**Alternatives considered.**
- *Google News RSS:* its links end in a consent wall.
- *Bing News RSS:* returned 0 results when measured.
- *GNews and NewsAPI free tiers:* snippets instead of full text, delays of 12–24 h, and limited to
  development use.
- *OpenAI web search:* about $0.01 per call on top of tokens, and it returns a model summary
  rather than the original text, so numbers cannot be checked against a source.

**Trade-offs.** Without a Guardian key, a free-text topic only gets what the catalogue feeds
contain.

**Evidence.** Own measurements on 2026-09-26: feed freshness, availability of full text, and
HTTP status for every candidate source. The official pages of each provider:
[Guardian Open Platform](https://open-platform.theguardian.com/access/) and the
[EuroLeague API](https://api-live.euroleague.net/swagger/index.html).

---

## D5 · One OpenAI model per task

**Status:** Accepted · **Date:** 2026-09-26

**Context.** Two stages use a language model: selecting stories, which is a classification task,
and writing the script, where quality is audible.

**Decision.** `gpt-6-sol` writes the script and `gpt-6-luna` selects the stories. Both are
settings, not hard-coded values (D16). `gpt-6-astra` is kept only as an option to try on the
sample episode.

**Alternatives considered.**
- *`gpt-6-astra` for writing:* about five times the price of `gpt-6-sol`.
- *`gpt-5.6-sol`:* twice the price of `gpt-6-sol`.

**Trade-offs.** Some writing quality compared with `gpt-6-astra`.

**Evidence.** [OpenAI pricing](https://developers.openai.com/api/docs/pricing). The real cost
per episode is measured in the Step 3 spike and recorded per call (D11).

---

## D6 · Voice: ElevenLabs v3 text-to-dialogue

**Status:** Accepted, chunking to be validated in Step 3 · **Date:** 2026-09-26

**Context.** The episode is a conversation between two hosts, and it has to sound natural.

**Decision.** `eleven_v3` text-to-dialogue with two voices. The script is sent in chunks of at
most 2,000 characters, cut at segment boundaries. The planned rule is one request per segment,
which also gives the start time of each segment for free. The chunks are joined with a short
silence and loudness-normalised with ffmpeg. During development: fake audio, a cache keyed by
the hash of the text, and very short v3 texts.

**Alternatives considered.**
- *Flash models:* half the price, but they do not support text-to-dialogue.
- *One TTS request per turn, stitched together:* more requests, and more joins that can be heard.
- *OpenAI TTS:* one voice per request, so it has the same stitching problem as the previous
  option. It is the natural fallback provider, kept as future work.
- *A second provider as fallback:* a second audio path that would have to be tested by ear.

**Trade-offs.** If ElevenLabs is down, the episode fails; it can be retried (D2). A fallback
voice provider is a future improvement.

**Evidence.** ElevenLabs
[text-to-dialogue documentation](https://elevenlabs.io/docs/overview/capabilities/text-to-dialogue):
the API uses the Eleven v3 model, and requests should stay at or under 2,000 characters "for
reliable generation". A 71-character test dialogue on
2026-09-26 confirmed the two voices. Step 3 checks by ear whether the joins between segments
are audible.

---

## D7 · Check the script before paying for voice

**Status:** Accepted · **Date:** 2026-09-26

**Context.** The worst failure for a sports news podcast is a made-up score or statistic.

**Decision.** A deterministic check runs before the voice stage:
- every factual turn cites a `source_id` from this episode's sources;
- every number in the script appears in the cited source.

A sabotage test plants an invented number and requires the check to catch it. If the check fails,
the script is rewritten once with the reason, and a second failure marks the episode `failed`.
Numbers are kept as digits in the script so they can be checked, and are formatted for speech
right before the voice stage.

**Alternatives considered.**
- *An LLM judge only:* it costs money, it is non-deterministic, and it can miss what code catches
  for free. It remains an optional extra, to catch unsupported claims that contain no numbers.
- *Token `logprobs` as a confidence signal:* `gpt-6-luna` rejects the parameter
  (`unsupported_parameter`).
- *HHEM, a local hallucination model:* it would add PyTorch to the image.
- *WER on the generated audio:* extra cost and time; the audio is checked by ear.

**Trade-offs.** The deterministic check cannot catch an invented claim that contains no numbers.

**Evidence.** In a previous project, an LLM agent evaluation suite, a deliberate sabotage of the
mock showed that a pricing grader was anchored on the `$` symbol, so it measured format, not
value. Sabotage tests are how I check that a check can actually fail.

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

**Status:** Accepted · **Date:** 2026-09-26

**Context.** `sample.mp3` is the only deliverable that depends on something outside our control:
the ElevenLabs quota of a shared account whose limit is not visible.

**Decision.** Produce the sample in a single take in Step 7, once audio quality is right and
before the user app (Step 8) and the dashboard (Step 9).

**Alternatives considered.**
- *Record it at the end:* risks finding the quota exhausted.
- *Record several takes "just in case":* spends the quota for nothing.

**Trade-offs.** None in the result; only the order of the steps changes.

**Evidence.** The key's character statistics endpoint shows other activity on the same account.

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

## AI tooling: agent skills

Agent skills are instruction packs for Claude Code. They are installed per project, only in the
step that needs them, after reading their `SKILL.md`, and they are removed when they stop being
useful.

| Skill | Source | Step | Why | What it contributed |
|---|---|---|---|---|
| `documentation-and-adrs` | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) · MIT · 42.6K installs | 2 | Writing these records | The Status and Date fields, and the rule to supersede records instead of deleting them. It adapted to this file's existing format. |

**Evaluated and not installed:**
- `github/awesome-copilot@create-architectural-decision-record` (MIT, 10.1K installs): it
  enforces one file per record and coded bullet IDs, which is noise for short records.
- `openai/skills` → `openai-docs`: built for Codex, and it depends on an MCP server and a helper
  script. The official OpenAI docs are read directly instead.
