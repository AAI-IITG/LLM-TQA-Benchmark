# PHM Temporal QA Benchmark

This repository is the v0.1 foundation for benchmarking temporal question
answering over Prognostics and Health Management (PHM) data. The first domain
is NASA C-MAPSS FD001. The design deliberately separates:

1. source observations;
2. reproducibly derived events;
3. question wording;
4. executable gold-answer programs; and
5. model predictions.

That separation prevents an LLM-generated paraphrase or an estimated
degradation onset from silently becoming ground truth.

## Current milestone

Step 1 is complete: benchmark scope, canonical event and QA schemas, a small
temporal program DSL, semantic validation, synthetic fixtures, and tests.
No benchmark score is reported yet.

## Repository map

```text
configs/                 Benchmark configuration
docs/                    Scope and design decisions
examples/                Synthetic schema fixtures (not benchmark data)
src/phm_tqa/schema.py    Canonical Pydantic models
src/phm_tqa/oracle.py    Executable gold-program oracle
src/phm_tqa/validate.py  Structural and semantic validation CLI
tests/                   Unit tests
data/                    Raw/interim/processed data placeholders
```

## Quick start

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
phm-tqa-validate \
  --events examples/events.jsonl \
  --questions examples/questions.jsonl
python -m unittest discover -s tests -v
```

Without installing the package:

```bash
PYTHONPATH=src python -m phm_tqa.validate \
  --events examples/events.jsonl \
  --questions examples/questions.jsonl
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Non-negotiable benchmark rules

- Every gold answer has an executable program and explicit supporting fact IDs.
- Every derived event records its extraction method, version, and parameters.
- Predicted events cannot support a gold answer.
- C-MAPSS test-set failure time is derived from the provided RUL truth; it is
  never marked as directly observed.
- C-MAPSS degradation onset is a derived construct, not a supplied label.
- Splitting is group-aware by unit and paraphrase family, never random by QA row.
- Natural-language paraphrasing may change wording, but never the program or
  canonical answer.

See `docs/SCOPING_NOTE.md` for the full v0.1 contract and the next build step.

