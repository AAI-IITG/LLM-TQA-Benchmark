# AI Agent Guidelines

This document outlines the responsibilities, workflows, and strict constraints for any AI agents (or subagents) contributing to the `LLM-TQA-Benchmark` repository.

## 1. Core Responsibilities
- **Phased Execution**: All development must follow the phases outlined in `docs/IMPLEMENTATION_PLAN.md`.
- **Journaling**: Every modification to the repository (code, schema, or documentation) must be meticulously logged in `docs/JOURNAL.md`. The log must include the specific changes made and the architectural or logical reason for the change.
- **Verification**: Agents must ensure that newly generated questions or extracted events pass the schema validation (`phm-tqa-validate`) before committing them to the dataset.

## 2. strict Constraints (from Scoping Note)
- **No Hallucinated Data**: Predicted events or hallucinated degradation onset times cannot be used as supporting facts for gold answers.
- **Schema Adherence**: All temporal operations must strictly use the existing canonical Pydantic models defined in `src/phm_tqa/schema.py`.
- **No Paraphrasing of Logic**: While question text can be paraphrased by LLMs, the canonical answer and the underlying executable program must remain identical to the template.
- **Run-to-failure Interpretation**: Test trajectories are truncated. Failure times for test sets must be marked as `derived` (computed using RUL), never as `observed`.

## 3. Workflow for Agents
1. **Plan**: Review `docs/IMPLEMENTATION_PLAN.md` and `docs/SCOPING_NOTE.md` before starting a task.
2. **Execute**: Implement the code or generate the data. 
3. **Verify**: Run `python -m unittest discover -s tests -v` and `phm-tqa-validate`.
4. **Document**: Append a detailed entry to `docs/JOURNAL.md`.
