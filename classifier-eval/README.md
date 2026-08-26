# Classifier eval harness

Answers one question: **can a cheaper model replace the incumbent classifier without
losing accuracy we care about?**

Decide that before deciding where to host anything. If open models miss the accuracy
bar, no amount of hardware saves the line item; if they clear it, hosting is a separate
and much easier decision.

Zero dependencies, stdlib only.

## Why this shape

The harness talks to any OpenAI-compatible endpoint, so hosted and local models are
measured by the *identical* code path:

| target | `--base-url` |
|---|---|
| OpenRouter | `https://openrouter.ai/api/v1` (default) |
| Ollama | `http://localhost:11434/v1` |
| LM Studio | `http://localhost:1234/v1` |
| vLLM | `http://<host>:8000/v1` |

Run the candidates through OpenRouter first — it costs a few dollars and needs no new
hardware. Only if something clears the bar does "where do we host it" become a real
question.

## Workflow

**1. Build the case file.** JSONL, one case per line:

```json
{"id": "1", "input": {"headline": "...", "market_question": "..."}, "expected": "yes"}
```

`expected` is your gold label. Two ways to get it:

- **Hand-labelled ground truth** — better, and the only way to discover that the
  incumbent is itself wrong.
- **The incumbent's own output** — cheaper. Measures *agreement*, not correctness.
  Fine for "can we swap this out", useless for "is this any good".

Sample a few hundred cases with a realistic positive/negative balance. If matches are
rare in production, an eval set that's 50% positives will flatter every model.

**2. Extract the prompt.** Copy the production prompt into a text file, replacing the
values it interpolates with `{{field}}` placeholders matching your `input` keys.
Placeholders are `{{double-braced}}` precisely so the literal `{` and `}` in your JSON
examples pass through untouched.

**3. Run.**

```bash
export OPENROUTER_API_KEY=sk-or-...

python3 eval_classifier.py \
  --cases cases.jsonl \
  --prompt prompt.txt \
  --model qwen/qwen3-30b-a3b \
  --model deepseek/deepseek-chat \
  --model meta-llama/llama-3.3-70b-instruct \
  --parse 'json:match' \
  --positive yes \
  --volume-per-day 250000 \
  --concurrency 8
```

Include your **current production model** in the `--model` list. Without that row you
have nothing to compare against, and its cost column is the number you're trying to beat.

## Reading the output

```
model                     agree    prec  recall      F1     p50     p95       $/mo  notes
qwen/qwen3-30b-a3b        91.2%   94.1%   88.3%   91.1%   0.84s   1.90s       $310
```

- **agree** — raw match rate against `expected`. Headline number, worst number. On
  skewed data a model that answers "no" to everything can score 90%.
- **prec / recall** — the two that matter, and they are *not* symmetric for you:
  - a **false positive** publishes a match that isn't one — reputational
  - a **false negative** misses a signal — opportunity cost
  Decide which you'd rather eat *before* reading the table, then pick on that column.
- **$/mo** — real spend from OpenRouter's `usage.cost`, extrapolated at
  `--volume-per-day × 30`. Local endpoints report `local`.
- **p50 / p95** — p95 is the one that decides whether a model survives your pipeline.

### Scores instead of labels

If the classifier emits a confidence rather than a verdict:

```bash
--parse 'json:confidence' --positive yes --numeric
```

This sweeps the cutoff and reports the best achievable F1 plus the threshold that gets
it. Worth doing: a cheap model often *ranks* correctly while scoring on a different
scale, so it looks bad at the incumbent's threshold and fine at its own. Re-tune the
cutoff before rejecting the model.

## Options

| flag | effect |
|---|---|
| `--parse` | `raw`, `json:<dotted.path>`, or `regex:<pattern>` (first capture group) |
| `--numeric` | treat predictions as scores; sweep the decision threshold |
| `--concurrency` | parallel requests (default 4) — raise for hosted, lower for local |
| `--limit N` | smoke-test on the first N cases before paying for the full run |
| `--cache` | resume without re-paying; keyed on model + prompt hash + case id |
| `--out` | per-row results as JSONL, for digging into specific disagreements |

The cache key includes a hash of the prompt, so editing the prompt correctly
invalidates prior runs rather than silently reusing them.

## Smoke test

```bash
python3 eval_classifier.py \
  --cases cases.example.jsonl --prompt prompt.example.txt \
  --model <any-model> --parse 'json:match' --positive yes --limit 2
```

Six toy news→market pairs. Confirms wiring, parsing and scoring before you point it at
real data.

## What this deliberately does not measure

Article generation. Long-form quality isn't a precision/recall problem and shouldn't be
graded by one — that workload needs human review, and cost there is better controlled by
capping volume than by cheapening the model.
