# v0.1 Scoping Note: Temporal QA over C-MAPSS FD001

## 1. Research question

How accurately do off-the-shelf language models answer temporally grounded
questions about machine degradation and remaining useful life when the same
underlying facts are presented as raw windows, event logs, compact text, or a
knowledge-graph-like representation?

The deliverable is a benchmark, an evaluation harness, baseline results, and a
failure taxonomy. It is not a new temporal reasoning model.

## 2. Minimal initial scope

Version 0.1 starts with the C-MAPSS FD001 training trajectories. FD001 is useful
for validating the pipeline because each unit is a run-to-failure sequence and
its terminal cycle is observable. It is deliberately narrow: one operating
condition and one simulated degradation setting make many fault-identification
and operating-regime questions either unavailable or trivial.

The first six supported semantic families are:

| Family | Example semantic target | Gold operation |
| --- | --- | --- |
| Sensor state | Was sensor 11 above its train-fitted threshold at cycle 80? | lookup/compare |
| Crossing order | Did sensor 11 cross its threshold before sensor 4? | compare |
| Duration | How many cycles passed from a declared crossing to failure? | subtract |
| RUL | At cycle 90, how many cycles remained? | subtract |
| Trend comparison | Was a sensor's slope steeper in the final half? | compare |
| Lifetime ranking | Which listed unit had the shortest lifetime? | argmin |

The following are excluded until a dataset supplies, or a documented method
derives, the required facts:

- maintenance-event timing;
- calendar dates and times;
- per-unit named fault-mode onset;
- causal claims such as “sensor X caused the failure”;
- maintenance recommendations.

## 3. What counts as a temporal question

A question is temporal only if answering it requires at least one explicit
operation over cycle-indexed facts. Merely mentioning a cycle number is not
sufficient. The operation is stored with the QA item and executed to reproduce
the answer.

The v0.1 operator inventory is:

$$
\mathcal{O}_{0.1} = \{\operatorname{lookup},\operatorname{subtract},
\operatorname{compare},\operatorname{argmin},\operatorname{argmax},
\operatorname{count}\}.
$$

Later versions can add interval overlap, Allen relations, rate estimation,
aggregation over windows, and compositional programs without changing the
outer QA schema.

## 4. Evidence levels

Every event has exactly one evidence status:

1. **Observed**: directly represented by source rows or supplied labels.
2. **Derived**: deterministically computed from observed data using a versioned
   method and recorded parameters.
3. **Predicted**: emitted by a learned model.

Observed and derived facts may support gold answers. Predicted facts may be
included as model context in a dedicated experiment, but cannot define gold.

### C-MAPSS-specific cautions

- A training trajectory ending at cycle $T_u$ supports an observed failure
  cycle under the benchmark's run-to-failure interpretation.
- A test trajectory is truncated. Its eventual failure cycle can be computed as
  $T_u + \mathrm{RUL}_u$ from the supplied test truth and must be marked
  **derived**, not observed.
- “Degradation onset” is not a row-level C-MAPSS label. Any onset used in a
  question must be marked **derived** and tied to a declared change-point or
  threshold-crossing method.
- FD001 does not support meaningful per-unit fault-mode classification from
  explicit labels. We therefore avoid questions that pretend such labels exist.

## 5. Canonical records

### Event record

An event records the dataset, subset, split, unit, event type, cycle interval,
attributes, evidence status, and complete provenance. Intervals are closed:
$[\texttt{cycle_start},\texttt{cycle_end}]$. A point event has equal start and
end cycles.

### QA record

A QA record contains:

- natural-language question text;
- typed canonical answer and optional numeric tolerance;
- temporal operator labels and difficulty;
- context specification and cutoff cycle;
- an executable gold program;
- explicit IDs of every fact consumed by that program;
- generation and verification provenance;
- leakage-control declarations.

Question wording is downstream of semantics. An LLM may paraphrase a verified
template, but it may not create the program or change the answer.

## 6. Split policy

Random QA-row splitting is forbidden because multiple questions and
paraphrases can share the same trajectory and answer. Splits are grouped by:

1. engine unit;
2. semantic item/paraphrase family.

Question type and template family are stratification variables, not grouping
keys: ordinary templates should occur across partitions so every main question
family can be scored. All paraphrases of one semantic item stay in the same
partition. A separate hard partition will contain longer horizons and composed
operations. Thresholds and normalisation statistics are fitted on designated
development units only and then frozen before test generation.

## 7. Evaluation contract

Each system must return a machine-readable answer field in addition to any
free-text rationale. Scoring uses the typed answer:

- exact match for Boolean, categorical, integer, and list answers;
- tolerance accuracy and absolute error for floating-point answers;
- macro results per question family, operator, difficulty, context form, model,
  and prompting condition;
- invalid-output rate reported separately.

Rationales are retained for error analysis but never used to rescue an
incorrect typed answer.

## 8. Acceptance checks for every generated item

An item is admitted only if:

1. its event and QA records pass schema validation;
2. the stored program executes successfully;
3. the executed result equals the canonical answer;
4. the set of consumed event IDs exactly equals `gold_fact_ids`;
5. none of those events is predicted;
6. the question is answerable from the intended context;
7. no answer string or future-only fact leaks into the prompt unintentionally;
8. all items in its unit and semantic/paraphrase group share one split.

## 9. Next build step

Implement the FD001 adapter:

1. parse `train_FD001.txt`, `test_FD001.txt`, and `RUL_FD001.txt`;
2. preserve all 3 operating settings and 21 sensor columns before feature
   selection;
3. emit canonical trajectory rows and terminal/truncation events;
4. validate unit/cycle continuity and test-RUL alignment;
5. write a manifest with source hashes and row counts;
6. add deterministic threshold-crossing derivation fitted only on designated
   training units.
