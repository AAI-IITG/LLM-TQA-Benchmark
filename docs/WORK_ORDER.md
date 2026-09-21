# Work Order & Execution Tracking

This document serves as the step-by-step execution tracker for the LLM-TQA-Benchmark project. It breaks down the broader implementation phases into discrete tasks, tracking their status and the strict criteria (Gates) required to proceed to the next step.

| Step | Phase | Task Description | Category | Status | Gate / Verification Criteria |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **1** | 1 | Parse C-MAPSS FD001 raw text files | Data Ingestion | ⏳ To Do | Raw files read successfully; 21 sensors & 3 settings preserved. |
| **2** | 1 | Extract Trajectories & `OBSERVATION` Events | Data Ingestion | ⏳ To Do | Unit/cycle continuity verified; outputs match `EventRecord` schema. |
| **3** | 1 | Derive `DEGRADATION_ONSET` & `FAILURE` Events | Data Processing | ⏳ To Do | Test RUL accurately mapped; events strictly marked as `DERIVED`. |
| **4** | 1 | Finalize Event Log & Manifest | Validation | ⏳ To Do | `fd001_events.jsonl` passes `phm-tqa-validate`; hashes generated. |
| **5** | 2 | Build Question Template Generator | Code/Infrastructure | ⏳ To Do | Templates cover point-in-time, ordering, duration, RUL, etc. |
| **6** | 2 | Generate Canonical Questions & Programs | Data Generation | ⏳ To Do | Oracles execute successfully against `fd001_events.jsonl`. |
| **7** | 2 | Build LLM Paraphrasing Pipeline | Data Generation | ⏳ To Do | Paraphrased text generated without altering canonical answers/programs. |
| **8** | 2 | Semantic Verification & Quality Control | Verification | ⏳ To Do | 10% sample human-reviewed; no trivial shortcuts (e.g., all "yes"). |
| **9** | 2 | Dataset Splitting & Leakage Controls | Data Processing | ⏳ To Do | Splits strictly grouped by Unit ID and Semantic Family. |
| **10** | 2 | Finalize QA Dataset | Validation | ⏳ To Do | `fd001_questions.jsonl` fully passes `phm-tqa-validate`. |
| **11** | 3 | Build LLM Evaluation Harness | Code/Infrastructure | ⏳ To Do | Test suite successfully parses structured model outputs and calculates metrics (Exact Match, Tolerance). |
| **12** | 3 | Execute Baseline LLM Runs | Experiment | ⏳ To Do | Zero-shot, Few-shot, and RAG architectures executed on targeted LLMs. |
| **13** | 4 | Error Analysis & Failure Taxonomy | Analysis | ⏳ To Do | Failures categorized (e.g., arithmetic, ordering, hallucination). |
| **14** | 4 | Final Report & Neurosymbolic Recommendations | Documentation | ⏳ To Do | Report published mapping failures to future neurosymbolic components. |

### Status Legend
- ⏳ **To Do**: Pending execution.
- 🚧 **In Progress**: Currently being worked on.
- ✅ **Done**: Completed and passed verification gate.
- ❌ **Blocked**: Hindered by a dependency or error.
