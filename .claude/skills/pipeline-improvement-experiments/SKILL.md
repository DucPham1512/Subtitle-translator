---
name: pipeline-improvement-experiments
description: Use when planning an accuracy fix or benchmark.
---

# Pipeline improvement experiments

Use this before building or benchmarking any change meant to raise accuracy in a multi-stage pipeline (speaker attribution, recognition, OCR, LLM translation).

## 1. Locate the failing stage before choosing a fix

Break the errors down by the stage that produced them, not by the symptom. For each error, ask: **was the right answer even available to the stage that made the final choice?** For example, was the gold speaker in the candidate list the translator received?

- If the right answer is missing upstream (absent from the candidates, never clustered, never detected), a downstream improvement can't fix it. Better prompts, richer memory or descriptions are all downstream. The fix has to be in the stage that builds the candidates.
- Split by population (main cast vs new characters, first appearance vs returning, voice status). Overall accuracy hides that one population carries most of the errors.

## 2. Run a free ceiling check before writing code

Use only the data already recorded: machine artifacts plus the gold. No LLM calls and no writes. Compute the most a perfect version of the proposed method could fix:

- For grouping or fusion ideas, measure the purity of the groups the new signal would contribute, and count the target errors that fall in a group whose majority is the right answer.
- Report the ceiling in user terms, e.g. "at most 72 lines, about 4.5 fewer manual fixes per episode out of about 25", plus a realistic estimate (often about half).
- Check what the signal really means. Example: "an unknown sprite is talking" turned out to be main cast on more than half the lines, so it was not a novelty signal on its own.
- Let the user decide from the ceiling whether the work is worth it, and record the measurement where decisions are logged.

## 3. Compare runs fairly

- If the gold was corrected from the recorded machine output, a reference run that reuses the LLM cache reproduces that output and is biased towards gold. Any fresh, uncached run will look worse against it, on subjective fields especially: listener, exact wording, pronouns.
- Compare fresh against fresh: run the control with the feature off and the cache bypassed. Otherwise call the comparison confounded and say so.
- Estimate run time from the uncached rate, not from earlier cached runs. Uncached chain runs can take 2Ã¢â‚¬â€œ3 times longer.
- When a config flag is turned off only for a control run, set it in memory in a small runner script. Plain `--resume` of a CLI run re-reads the config file and would silently undo it.

## 4. Decide and record

- No gain on the target metric Ã¢â€ â€™ switch the feature off but keep the code, and record why, plus where it might still help (e.g. human review aids that the benchmark can't measure).
- Time-box experiments on the weakest population. Accepting the current level is a valid outcome when the ceiling is low.
