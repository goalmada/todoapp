#!/usr/bin/env python3
"""
eval_classifier.py - measure whether a cheaper model can replace an incumbent classifier.

Runs one or more candidate models over the same set of cases, compares each against a
gold label (either hand-labelled ground truth or the current production classifier's
output), and reports agreement, precision/recall, latency and projected monthly cost.

Zero dependencies - stdlib only. Works against any OpenAI-compatible endpoint:

    OpenRouter    --base-url https://openrouter.ai/api/v1   (default)
    Ollama        --base-url http://localhost:11434/v1
    LM Studio     --base-url http://localhost:1234/v1
    vLLM          --base-url http://<host>:8000/v1

The same harness therefore evaluates hosted and local models identically, which is the
point: decide on accuracy first, decide where to host second.

Usage:
    export OPENROUTER_API_KEY=sk-or-...
    python3 eval_classifier.py \
        --cases cases.jsonl \
        --prompt prompt.txt \
        --model qwen/qwen3-30b-a3b \
        --model deepseek/deepseek-chat \
        --parse 'json:match' \
        --positive yes \
        --volume-per-day 250000
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)
RETRY_STATUS = {408, 409, 429, 500, 502, 503, 504}


# ---------------------------------------------------------------- rendering


def render(template: str, data: dict) -> str:
    """Fill {{field}} placeholders from a case's input.

    Deliberately not str.format - production prompts are full of literal braces
    from JSON examples, and those must survive untouched.
    """

    def sub(m: re.Match) -> str:
        key = m.group(1)
        if key not in data:
            raise KeyError(f"case is missing field {key!r} required by the prompt")
        value = data[key]
        return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)

    return PLACEHOLDER.sub(sub, template)


# ---------------------------------------------------------------- transport


@dataclass
class Response:
    text: str = ""
    cost: float | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency: float = 0.0
    error: str | None = None


def call_model(
    base_url: str,
    api_key: str,
    model: str,
    system: str | None,
    user: str,
    *,
    max_tokens: int,
    timeout: float,
    retries: int,
) -> Response:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
        # OpenRouter returns real spend here; local servers ignore it.
        "usage": {"include": True},
    }
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    delay = 1.0
    last = "unknown error"
    for attempt in range(retries + 1):
        started = time.monotonic()
        try:
            req = urllib.request.Request(
                f"{base_url.rstrip('/')}/chat/completions", data=body, headers=headers
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
            elapsed = time.monotonic() - started
            usage = data.get("usage") or {}
            return Response(
                text=(data["choices"][0]["message"].get("content") or "").strip(),
                cost=usage.get("cost"),
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                latency=elapsed,
            )
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:200].decode(errors='replace')}"
            if e.code not in RETRY_STATUS:
                break
        except Exception as e:  # timeouts, connection resets, malformed JSON
            last = f"{type(e).__name__}: {e}"

        if attempt < retries:
            time.sleep(delay)
            delay = min(delay * 2, 30.0)

    return Response(error=last, latency=time.monotonic() - started)


# ---------------------------------------------------------------- parsing


def extract_json(text: str) -> dict | None:
    for candidate in (FENCE.findall(text) or [text]):
        candidate = candidate.strip()
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end <= start:
            continue
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def parse_label(text: str, mode: str) -> str | None:
    """mode is 'raw', 'json:<dotted.path>' or 'regex:<pattern with one group>'."""
    if not text:
        return None

    if mode.startswith("json:"):
        obj = extract_json(text)
        if obj is None:
            return None
        cursor: object = obj
        for part in mode[5:].split("."):
            if not isinstance(cursor, dict) or part not in cursor:
                return None
            cursor = cursor[part]
        raw = cursor
    elif mode.startswith("regex:"):
        m = re.search(mode[6:], text, re.IGNORECASE | re.DOTALL)
        if not m:
            return None
        raw = m.group(1)
    else:
        raw = text

    if isinstance(raw, bool):
        return "true" if raw else "false"
    return normalise(str(raw))


def normalise(value: str) -> str:
    return value.strip().strip("\"'`.,:;").lower()


# ---------------------------------------------------------------- scoring


@dataclass
class Result:
    model: str
    rows: list = field(default_factory=list)  # (case_id, gold, pred, latency, cost, err)

    @property
    def scored(self):
        return [r for r in self.rows if r[2] is not None]

    @property
    def parse_failures(self):
        return sum(1 for r in self.rows if r[2] is None and r[5] is None)

    @property
    def call_errors(self):
        return sum(1 for r in self.rows if r[5] is not None)


def binary_metrics(pairs, positive: str) -> dict:
    tp = fp = fn = tn = 0
    for gold, pred in pairs:
        g, p = gold == positive, pred == positive
        if g and p:
            tp += 1
        elif p and not g:
            fp += 1
        elif g and not p:
            fn += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def sweep_threshold(pairs, positive: str) -> dict:
    """Numeric predictions: find the cutoff that maximises F1.

    A cheap model often ranks correctly while scoring on a different scale. Raw
    agreement at the incumbent's threshold understates it; re-tuning the cutoff is
    usually the fix, not rejecting the model.
    """
    numeric = []
    for gold, pred in pairs:
        try:
            numeric.append((gold, float(pred)))
        except (TypeError, ValueError):
            continue
    if not numeric:
        return {}

    best = {"f1": -1.0}
    lo = min(v for _, v in numeric)
    hi = max(v for _, v in numeric)
    if hi <= lo:
        return {}
    for i in range(101):
        cut = lo + (hi - lo) * i / 100
        m = binary_metrics([(g, positive if v >= cut else "~") for g, v in numeric], positive)
        if m["f1"] > best["f1"]:
            best = {**m, "threshold": cut}
    return best


# ---------------------------------------------------------------- reporting


def pct(x: float) -> str:
    return f"{x * 100:5.1f}%"


def report(results: list[Result], args, gold_counts: dict) -> None:
    print()
    print(f"Cases: {sum(gold_counts.values())}    Gold distribution: ", end="")
    print(", ".join(f"{k}={v}" for k, v in sorted(gold_counts.items())))
    if args.volume_per_day:
        print(f"Projecting monthly cost at {args.volume_per_day:,}/day x 30 days.")
    print()

    header = f"{'model':<38} {'agree':>7} {'prec':>7} {'recall':>7} {'F1':>7} {'p50':>7} {'p95':>7} {'$/mo':>10}  notes"
    print(header)
    print("-" * len(header))

    for r in results:
        scored = r.scored
        if not scored:
            print(f"{r.model:<38} {'-':>7} {'-':>7} {'-':>7} {'-':>7} {'-':>7} {'-':>7} {'-':>10}  "
                  f"no usable output ({r.call_errors} errors)")
            continue

        pairs = [(row[1], row[2]) for row in scored]
        agreement = sum(1 for g, p in pairs if g == p) / len(pairs)
        latencies = sorted(row[3] for row in scored)
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]

        if args.numeric:
            # Predictions are scores, not labels; exact-match agreement is meaningless.
            agreement = None
            m = sweep_threshold(pairs, args.positive) or {"precision": 0, "recall": 0, "f1": 0}
        elif args.positive:
            m = binary_metrics(pairs, args.positive)
        else:
            m = {"precision": float("nan"), "recall": float("nan"), "f1": float("nan")}

        costs = [row[4] for row in scored if row[4] is not None]
        if costs and args.volume_per_day:
            monthly = f"${sum(costs) / len(costs) * args.volume_per_day * 30:,.0f}"
        elif costs:
            monthly = f"${sum(costs):.4f}"
        else:
            monthly = "local"

        notes = []
        if r.parse_failures:
            notes.append(f"{r.parse_failures} unparseable")
        if r.call_errors:
            notes.append(f"{r.call_errors} errors")
        if args.numeric and "threshold" in m:
            notes.append(f"best cutoff {m['threshold']:.3f}")

        print(
            f"{r.model:<38} {(pct(agreement) if agreement is not None else '-'):>7} "
            f"{pct(m['precision']):>7} {pct(m['recall']):>7} "
            f"{pct(m['f1']):>7} {p50:6.2f}s {p95:6.2f}s {monthly:>10}  {', '.join(notes)}"
        )

    confusable = [] if args.numeric else [r for r in results if r.scored]
    if args.positive and confusable:
        print()
        print("Confusion (positive = %r):" % args.positive)
        for r in confusable:
            m = binary_metrics([(row[1], row[2]) for row in r.scored], args.positive)
            print(f"  {r.model:<38} tp={m['tp']:<5} fp={m['fp']:<5} fn={m['fn']:<5} tn={m['tn']:<5}")
        print()
        print("  fp = published a match that isn't one (reputational cost)")
        print("  fn = missed a real signal (opportunity cost)")
        print("  Weigh these asymmetrically - they are not equally expensive for you.")


# ---------------------------------------------------------------- main


def load_cases(path: str, limit: int | None) -> list[dict]:
    cases = []
    with open(path) as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as e:
                sys.exit(f"{path}:{lineno}: invalid JSON - {e}")
            if "input" not in case or "expected" not in case:
                sys.exit(f"{path}:{lineno}: each case needs 'input' and 'expected'")
            case.setdefault("id", f"case-{lineno}")
            cases.append(case)
    if limit:
        cases = cases[:limit]
    if not cases:
        sys.exit(f"{path}: no cases found")
    return cases


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cases", required=True, help="JSONL: {id, input:{...}, expected:<label>}")
    p.add_argument("--prompt", required=True, help="user-message template using {{field}} placeholders")
    p.add_argument("--system", help="optional system-prompt file")
    p.add_argument("--model", action="append", required=True, help="repeatable")
    p.add_argument("--base-url", default="https://openrouter.ai/api/v1")
    p.add_argument("--api-key-env", default="OPENROUTER_API_KEY")
    p.add_argument("--parse", default="raw", help="raw | json:<dotted.path> | regex:<pattern>")
    p.add_argument("--positive", help="label treated as positive for precision/recall")
    p.add_argument("--numeric", action="store_true", help="predictions are scores; sweep the cutoff")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--max-tokens", type=int, default=256)
    p.add_argument("--timeout", type=float, default=120.0)
    p.add_argument("--retries", type=int, default=3)
    p.add_argument("--limit", type=int, help="only run the first N cases")
    p.add_argument("--volume-per-day", type=int, help="classifications/day, for cost projection")
    p.add_argument("--cache", default=".eval-cache.jsonl", help="resume without re-paying")
    p.add_argument("--out", help="write per-row results to this JSONL")
    args = p.parse_args()

    api_key = os.environ.get(args.api_key_env, "local")
    cases = load_cases(args.cases, args.limit)
    template = open(args.prompt).read()
    system = open(args.system).read() if args.system else None

    cache: dict[str, dict] = {}
    if args.cache and os.path.exists(args.cache):
        with open(args.cache) as fh:
            for line in fh:
                try:
                    entry = json.loads(line)
                    cache[entry["key"]] = entry
                except (json.JSONDecodeError, KeyError):
                    continue
        if cache:
            print(f"Loaded {len(cache)} cached responses from {args.cache}", file=sys.stderr)

    cache_fh = open(args.cache, "a") if args.cache else None
    prompt_hash = hashlib.sha256((template + (system or "")).encode()).hexdigest()[:12]

    gold_counts: dict[str, int] = {}
    for c in cases:
        gold = normalise(str(c["expected"]))
        gold_counts[gold] = gold_counts.get(gold, 0) + 1

    results: list[Result] = []
    for model in args.model:
        print(f"Running {model} over {len(cases)} cases...", file=sys.stderr)
        result = Result(model=model)

        def run(case: dict) -> tuple:
            key = f"{model}|{prompt_hash}|{case['id']}"
            if key in cache:
                c = cache[key]
                resp = Response(text=c["text"], cost=c.get("cost"), latency=c.get("latency", 0.0))
            else:
                try:
                    user = render(template, case["input"])
                except KeyError as e:
                    return (case["id"], normalise(str(case["expected"])), None, 0.0, None, str(e))
                resp = call_model(
                    args.base_url, api_key, model, system, user,
                    max_tokens=args.max_tokens, timeout=args.timeout, retries=args.retries,
                )
                if cache_fh and not resp.error:
                    cache_fh.write(json.dumps({
                        "key": key, "text": resp.text,
                        "cost": resp.cost, "latency": resp.latency,
                    }) + "\n")
                    cache_fh.flush()

            gold = normalise(str(case["expected"]))
            pred = None if resp.error else parse_label(resp.text, args.parse)
            return (case["id"], gold, pred, resp.latency, resp.cost, resp.error)

        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            result.rows = list(pool.map(run, cases))
        results.append(result)

    if cache_fh:
        cache_fh.close()

    if args.out:
        with open(args.out, "w") as fh:
            for r in results:
                for cid, gold, pred, lat, cost, err in r.rows:
                    fh.write(json.dumps({
                        "model": r.model, "id": cid, "expected": gold, "predicted": pred,
                        "latency": lat, "cost": cost, "error": err,
                    }) + "\n")
        print(f"Per-row results written to {args.out}", file=sys.stderr)

    report(results, args, gold_counts)


if __name__ == "__main__":
    main()
