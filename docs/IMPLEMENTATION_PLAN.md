# Implementation Plan for LLM-TQA-Benchmark

This plan outlines the phase-wise implementation to complete the Prognostics and Health Management (PHM) Temporal QA Benchmark, focusing initially on the NASA C-MAPSS FD001 dataset. It transitions the repository from its current skeleton (schemas, validation, synthetic fixtures) to a complete benchmarking suite, following the 8-week MTech plan and v0.1 Scoping Note.

## User Review Required
> [!IMPORTANT]
> The current plan defines the extraction of degradation onset as a deterministic threshold crossing (as per `SCOPING_NOTE.md`). Before generating the final test set, we need to finalize the precise statistical rule or threshold mechanism that will be fitted on the train split to avoid test leakage.

## Open Questions
> [!WARNING]
> 1. **Data Access**: Have the raw C-MAPSS FD001 files (`train_FD001.txt`, `test_FD001.txt`, `RUL_FD001.txt`) already been downloaded to a specific directory? 
> 2. **Models**: Which specific LLMs (e.g., Gemini, Llama 3) will we officially target for the baselines?

## Proposed Changes

---

### Phase 1: Domain Data Ingestion & Event Extraction

Develop an adapter to read raw C-MAPSS data and output canonical `EventRecord` objects (JSONL) representing the sensor trajectories, operating conditions, and derived events like threshold crossings and failures.

#### [NEW] [src/phm_tqa/adapter_fd001.py](file:///x:/iit%20guwahati%20academics/MTP/LLM-TQA-Benchmark/src/phm_tqa/adapter_fd001.py)
- Parse C-MAPSS `train_FD001.txt`, `test_FD001.txt`, and `RUL_FD001.txt`.
- Emit canonical trajectory rows preserving 3 operating settings and 21 sensors.
- Emit terminal/truncation events.
- Derive test-set failure time from provided RUL truth (marking as `derived`).
- Implement deterministic threshold-crossing extraction fitted on train units to generate `DEGRADATION_ONSET` events.

#### [NEW] [src/scripts/ingest_cmapss.py](file:///x:/iit%20guwahati%20academics/MTP/LLM-TQA-Benchmark/src/scripts/ingest_cmapss.py)
- CLI entrypoint that uses the adapter to transform raw data into `data/interim/fd001_events.jsonl`.
- Validates cycle continuity and writes a dataset manifest with source hashes.

---

### Phase 2: Question Taxonomy & Dataset Construction

Create the generation pipeline that uses the extracted event log to build structural gold-standard `QuestionRecord` objects for the defined temporal question families.

#### [NEW] [src/phm_tqa/generator.py](file:///x:/iit%20guwahati%20academics/MTP/LLM-TQA-Benchmark/src/phm_tqa/generator.py)
- Implement template-based question instantiator based on the taxonomy: Point-in-time state, Before/after, Duration/interval, Ordering, Aggregation, and Forecast/RUL.
- Generate canonical answers and explicit gold programs (using `schema.py` models: `LookupProgram`, `SubtractProgram`, etc.).
- Filter out ambiguous conditions (ensuring leakage controls are met).

#### [NEW] [src/phm_tqa/paraphrase.py](file:///x:/iit%20guwahati%20academics/MTP/LLM-TQA-Benchmark/src/phm_tqa/paraphrase.py)
- Use an LLM API to paraphrase the rigid templated questions into natural language variants.
- Ensure paraphrased variants preserve the semantic integrity, same canonical answer, and same executable program.

#### [NEW] [src/scripts/generate_dataset.py](file:///x:/iit%20guwahati%20academics/MTP/LLM-TQA-Benchmark/src/scripts/generate_dataset.py)
- CLI script to execute generation and paraphrasing.
- Split generated data strictly by Engine Unit + Paraphrase Family to prevent row-wise leakage.
- Output validated QA pairs to `data/processed/fd001_questions.jsonl`.

---

### Phase 3: LLM Benchmarking & Evaluation Harness

Build the harness to feed the benchmark data (with different contextual representations) to off-the-shelf LLMs, collect their responses, and compute metrics.

#### [NEW] [src/phm_tqa/evaluate.py](file:///x:/iit%20guwahati%20academics/MTP/LLM-TQA-Benchmark/src/phm_tqa/evaluate.py)
- Model interface to call local/cloud LLMs.
- Context serializers to format evidence as `event_log`, `raw_window`, or `text`.
- Evaluation engine that parses structured outputs and compares against the typed canonical answer (Exact match for booleans/categoricals, tolerance bounds for floats).

#### [NEW] [src/scripts/run_benchmark.py](file:///x:/iit%20guwahati%20academics/MTP/LLM-TQA-Benchmark/src/scripts/run_benchmark.py)
- Runs the test suite across combinations: Model × Prompting Strategy (Zero-shot, Few-shot) × Context Type.
- Produces CSV results/metrics.

---

### Phase 4: Error Analysis & Consolidation

Systematic evaluation of failure modes (arithmetic, temporal misunderstanding, hallucination).

#### [NEW] [notebooks/error_analysis.ipynb](file:///x:/iit%20guwahati%20academics/MTP/LLM-TQA-Benchmark/notebooks/error_analysis.ipynb)
- Aggregate results from `run_benchmark.py`.
- Isolate failure types (e.g., duration calculation failures vs. event ordering failures).
- Correlate failures with the missing neurosymbolic components (interval logic, relation verification).

## Verification Plan

### Automated Tests
- `python -m unittest discover -s tests -v` (Extending existing tests in `test_validation.py` to cover the FD001 adapter and generators).
- Validation runs via `phm-tqa-validate` over the newly created `fd001_events.jsonl` and `fd001_questions.jsonl` to guarantee strict schema adherence.

### Manual Verification
- Visual inspection of the LLM paraphrased questions to ensure domain semantics haven't been altered.
- Check ~10% sample of the generated questions manually to ensure no trivial shortcuts exist (e.g., all answers being "yes").
