# Step 3 spike: measurements before building the pipeline

Before building the pipeline, I ran the whole path once with real news and the real providers,
to replace estimates with measurements. The code is
[`backend/scripts/spike.py`](../backend/scripts/spike.py). It is throwaway and runs one stage at a
time, and its `--dry-run` option prints the cost before any paid call. Run on 2026-09-27.

## What it ran

| Stage | What | Result |
|---|---|---|
| fetch | EuroLeague Round 1 results (official API), the latest EuroLeague story from Eurohoops (full text in the RSS feed) and the latest NBA story from ESPN (article page extracted with trafilatura) | 4 sources in 1.0 s |
| write | `gpt-6-sol` with `reasoning.effort: low` and Structured Outputs: 3 segments, each turn with its `source_ids` | 545 characters in 7.2 s |
| voice | `eleven_v3` text-to-dialogue: one request per segment, plus a probe for scores and names | 663 characters billed |
| master | ffmpeg: 0.4 s between segments, 0.5 s lead-in, 1 s tail, `loudnorm` | 47.1 s of audio in 1.1 s |

Total spent: about $0.0074 of OpenAI and 663 ElevenLabs characters (about $0.07 at list price).

## Measurements

**Script (OpenAI).** 1,710 input tokens and 316 output tokens, 49 of them reasoning. Almost all
the input (1,707 tokens) was written to the prompt cache, which `gpt-6-sol` bills at $2.50 per
1M tokens instead of $2.00, so the call cost about $0.0074. Every number in the script appeared
in the source it cited.

**Voice (ElevenLabs).**

| Request | Characters sent | Billed (`character-cost`) | Wall time | Audio | Characters per second |
|---|---|---|---|---|---|
| Segment 1 | 167 | 167 | 6.7 s | 12.8 s | 13.0 |
| Segment 2 | 161 | 161 | 6.4 s | 15.4 s | 10.5 |
| Segment 3 | 226 | 226 | 7.6 s | 16.6 s | 13.6 |
| Probe | 109 | 109 | 6.6 s | 12.6 s | 8.7 |

- The billed characters equal the characters sent, audio tags included.
- The script's segments averaged **12.4 characters per second** of audio (113 to 137 words per
  minute). An earlier 71-character test suggested about 20, which is why a script written for
  30 seconds lasted 45.
- The first audio byte arrived after 0.5 to 0.8 s, and each request took 6 to 8 s.
- v3 returns audio with no silence before the first word or after the last one. Inside a request
  it leaves about 1 s at each change of speaker and 0.3 to 0.6 s between sentences.
- The segments came out at -16.9, -17.1 and -17.3 LUFS: no volume jumps between requests.

**Master (ffmpeg).** 47.1 s at -16.4 LUFS integrated, with a true peak of -1.9 dBFS. That is
within [Apple Podcasts' audio requirements](https://podcasters.apple.com/support/893-audio-requirements):
-16 LKFS with a tolerance of 1 dB, and a true peak no higher than -1 dBFS.

## Listening check

- The joins between requests sound natural: the same tone, and a natural pause.
- The scores ("78 to 77", "106 to 89", "96 to 94") and the `[excited]` and `[laughs]` tags sound
  right.
- The probe: v3 read both "89–82" and "89 to 82" correctly, and pronounced Žalgiris and
  Fenerbahçe correctly.
- The only problem was that the episode started abruptly on the first word. It is fixed with a
  0.5 s lead-in, plus a 1 s tail so that it does not end abruptly either.

## What changes in the pipeline

| Finding | Consequence |
|---|---|
| The joins sound natural | One voice request per segment is confirmed ([D6](decisions.md#d6--voice-elevenlabs-v3-text-to-dialogue)). Segment start times come from the audio durations, without a timestamps API. |
| 12.4 characters per second | The script length is planned in characters: about 3,700 for 5 minutes. |
| Cost of a 5-minute episode (estimate) | About $0.37 of voice. OpenAI costs a few cents: about $0.04 with 8 to 10 sources (about 10,000 input tokens and 1,500 output tokens at the measured prices). Voice is about 90% of the cost. |
| Audio tags are billed | They count towards the length and the budget. |
| Both ways of writing a score read correctly | Scores are still rewritten as "89 to 82" before the voice: the result is deterministic, for 3 characters per score ([D7](decisions.md#d7--check-the-script-before-paying-for-voice)). |
| Hard names pronounced correctly | No IPA for now; revisited if the sample shows a problem. |
| The model skipped the strongest story and put two scores in one sentence | The code builds the segment plan (introduction, one block per interest in order of weight, closing) and the model writes each block. |
| Cache writes are billed | The cost calculation uses the cache-write price. Step 5 checks whether prompt caching pays off for one episode a day. |
| The EuroLeague API has three name fields | `abbreviatedName` reads best: "Real Madrid" and "Crvena Zvezda", not "Real" and "Crvena". |
| The whole path took about 37 s for 47 s of audio | Generation takes seconds, not minutes. The full-length measurement comes with the sample in Step 7. |

## Limits

- One script and one take. v3 is not deterministic, so the sample in Step 7 is the real test at
  full length.
- `loudnorm` ran in one pass. A two-pass run is more exact, and it is evaluated for the sample.
- The audio is encoded as MP3 twice: by ElevenLabs and after mastering. At 128 kbps it was not
  audible in speech. Requesting uncompressed audio is evaluated for the sample.

## Reproduce

From `backend/`, with the keys in `.env`:

```text
python scripts/spike.py fetch
python scripts/spike.py write --dry-run   # prints the estimated cost, no API call
python scripts/spike.py write             # paid: OpenAI
python scripts/spike.py voice --dry-run   # prints the texts and characters, no API call
python scripts/spike.py voice             # paid: ElevenLabs, cached by hash
python scripts/spike.py master
```
