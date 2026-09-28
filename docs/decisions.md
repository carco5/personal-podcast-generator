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
| D20 | [Every check is proven by a sabotage test, and the judge is measured](#d20--every-check-is-proven-by-a-sabotage-test-and-the-judge-is-measured) | Accepted, measured in Step 5 |
| D21 | [Episodes of 3, 5 or 7 minutes, and a 5-minute sample](#d21--episodes-of-3-5-or-7-minutes-and-a-5-minute-sample) | Accepted |
| D22 | [The episode follows the listener's priorities](#d22--the-episode-follows-the-listeners-priorities) | Accepted |
| D23 | [What an episode covers: what is new, or a catch-up the first time](#d23--what-an-episode-covers-what-is-new-or-a-catch-up-the-first-time) | Accepted |
| D24 | [Sources are ingested on a schedule and stored](#d24--sources-are-ingested-on-a-schedule-and-stored) | Accepted, built in Step 5 |
| D25 | [The data model grows step by step, and PostgreSQL enforces it](#d25--the-data-model-grows-step-by-step-and-postgresql-enforces-it) | Accepted |
| D26 | [Migrations with Alembic, applied by a prestart job](#d26--migrations-with-alembic-applied-by-a-prestart-job) | Accepted |
| D27 | [API without login: one current-user dependency, and the database as the guard](#d27--api-without-login-one-current-user-dependency-and-the-database-as-the-guard) | Accepted |
| D28 | [Tests run against a real PostgreSQL](#d28--tests-run-against-a-real-postgresql) | Accepted |
| D29 | [One backend image with a cached dependency layer](#d29--one-backend-image-with-a-cached-dependency-layer) | Accepted |
| D30 | [Sources are downloaded like a responsible crawler](#d30--sources-are-downloaded-like-a-responsible-crawler) | Accepted |
| D31 | [Official data is read from the data inside official pages](#d31--official-data-is-read-from-the-data-inside-official-pages) | Accepted |
| D32 | [The pipeline runs as recorded stages, behind small provider interfaces](#d32--the-pipeline-runs-as-recorded-stages-behind-small-provider-interfaces) | Accepted |

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
and the one-in-flight index (D25).

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

**Status:** Accepted · **Date:** 2026-09-26 · **Revised:** 2026-09-27

**Context.** Reviewers must be able to run the project with one command, and the API keys belong
to Prosper.

**Decision.** `docker compose up` starts the database, a one-off `prestart` job (migrations and the
demo user, D26), the API and the worker (Step 6). The `.env` file is optional (`required: false`).
Without keys the app still loads with the sample episode, the simulated dashboard and the full UI.
Only "Generate" needs keys: the API answers 503 and names the missing variables. The database port
is not published, and the API is published on `127.0.0.1` only, because it has no authentication
and can spend provider credits.

**Alternatives considered.** *A public deployment:* a public URL could spend the provider credits
without control.

**Trade-offs.** No URL to try the app without Docker. Deployment and authentication are future
work.

**Evidence.** Docker Compose documentation: since Compose 2.24.0, an `env_file` entry with
`required: false` is ignored when the file is missing. Revised in Step 4: the migration job became
`prestart`, and the API port is bound to localhost.

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

---

## D12 · REST conventions aligned with Prosper's public API

**Status:** Accepted · **Date:** 2026-09-26 · **Revised:** 2026-09-27

**Context.** The reviewers build and maintain a public REST API. Following their conventions where
they are consistent makes this API familiar to them.

**Decision.**
- `/api/v1/` prefix and `GET /api/v1/health`, as in Prosper's API.
- `page` + `limit` pagination, as in Prosper's call-log listing: `page` starts at 0, and a list
  answers `{"episodes": [...], "page_count": …, "next_page": … | null}`, the shape of Prosper's
  `{"call_logs": [...], "page_count", "next_page"}`.
- An endpoint to retry a failed episode, similar to Prosper's `rerun-failed` webhooks endpoint.
- Episode status values `queued`, `in_progress`, `completed`, `failed` and `skipped`, in one
  consistent style. This is the job lifecycle of GitHub's Checks API (`queued`, `in_progress`,
  `completed`) plus `failed`, and `skipped`, which is one of that API's conclusions.

**Alternatives considered.**
- *Copying Prosper's status values:* they differ between resources (for example `In Progress` and
  `Failed` for campaign targets, `IN_PROGRESS` and `COMPLETED` for cases), so there is no single
  convention to copy.
- *`page_size` pagination:* common elsewhere, but Prosper uses `limit`.

**Trade-offs.** Offset pagination gets slower on deep pages. With tens of episodes per user this
does not matter; keyset pagination is the next step if lists grow.

**Evidence.** Prosper's public OpenAPI document (`voice.getprosperapp.com/openapi.json`), checked
on 2026-09-27, and again in Step 4 for the page numbering and the response shape. [GitHub Checks API](https://docs.github.com/en/rest/checks/runs): `status` is
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

**Status:** Accepted · **Date:** 2026-09-27 · **Revised:** 2026-09-27 (Step 4), 2026-09-28 (Step 5)

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

**Status:** Accepted · **Date:** 2026-09-27 · **Revised:** 2026-09-28 (Step 5)

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

**Status:** Accepted · **Date:** 2026-09-27

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

## D29 · One backend image with a cached dependency layer

**Status:** Accepted · **Date:** 2026-09-27

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
  - the image is built once (`image: podcast-backend`), and each service sets its own command;
  - a YAML fragment (`x-backend`) holds what they share: the build, the optional `.env` and the
    in-network database URL.

**Alternatives considered.**
- *`pip install .`:* every change to the code reinstalls every dependency, and a second copy of
  the code ends up in `site-packages`.
- *uv with `--no-install-project`:* the same idea with a lock file, at the cost of one more tool
  (D15).
- *`fastapi[standard]` with `fastapi run`:* more dependencies than uvicorn alone.

**Trade-offs.** The image is 445 MB, mostly lxml and the provider SDKs. There is no multi-stage
build, because nothing is compiled.

**Evidence.** Measured on 2026-09-27:
- the first build took about 1.5 minutes, and a rebuild after a change to the code took 3 seconds,
  with the dependency layer reported as `CACHED`;
- `id` inside the container reports uid 999 (`podcast`).

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
  with `SKIP LOCKED`, and that step decides where the claim lives.
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
- a slash between two words becomes a space;
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

## AI tooling: agent skills

Agent skills are instruction packs for Claude Code. They are installed per project, only in the
step that needs them, after reading their `SKILL.md`, and they are removed when they stop being
useful.

| Skill | Source | Step | Why | What it contributed |
|---|---|---|---|---|
| `documentation-and-adrs` | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) · MIT · 42.6K installs | 2, kept in 3 to 5 | Writing these records | The Status and Date fields, and the rule to supersede records instead of deleting them. It adapted to this file's existing format. |
| `fastapi` | [fastapi/fastapi](https://github.com/fastapi/fastapi/tree/master/fastapi/.agents/skills/fastapi) · MIT · official · 10.7K installs | 4 | Current conventions from FastAPI's maintainers | `Annotated` dependency aliases (`SessionDep`, `CurrentUser`), return types instead of `response_model`, the prefix and tags on each `APIRouter`, `def` endpoints for blocking database code, and when a `yield` dependency closes. Its SQLModel, uv and ty advice was set aside on purpose (D1, D15). |

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
