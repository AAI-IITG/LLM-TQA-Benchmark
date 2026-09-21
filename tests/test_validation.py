from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from phm_tqa.oracle import EventStore, evaluate_program
from phm_tqa.schema import EventRecord, QuestionRecord
from phm_tqa.validate import load_jsonl, validate_records


ROOT = Path(__file__).resolve().parents[1]


class BenchmarkValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.events, event_errors = load_jsonl(
            ROOT / "examples" / "events.jsonl", EventRecord
        )
        cls.questions, question_errors = load_jsonl(
            ROOT / "examples" / "questions.jsonl", QuestionRecord
        )
        if event_errors or question_errors:
            raise AssertionError(event_errors + question_errors)

    def test_fixture_gold_programs_validate(self) -> None:
        self.assertEqual(validate_records(self.events, self.questions), [])

    def test_duration_oracle_returns_107(self) -> None:
        question = next(
            q for q in self.questions if q.question_id == "qa_fixture_duration_001"
        )
        result = evaluate_program(question.program, EventStore(self.events))
        self.assertEqual(result.value, 107)
        self.assertEqual(
            result.consumed_event_ids,
            frozenset({"evt_u012_s11_cross_085", "evt_u012_failure_192"}),
        )

    def test_cmapss_observed_onset_is_rejected(self) -> None:
        payload = self.events[1].model_dump(mode="json")
        payload["event_id"] = "evt_bad_observed_onset"
        payload["event_type"] = "degradation_onset"
        payload["evidence_status"] = "observed"
        bad_event = EventRecord.model_validate(payload)
        errors = validate_records([*self.events, bad_event], self.questions)
        self.assertTrue(
            any("degradation onset must be derived" in error for error in errors)
        )

    def test_wrong_stored_answer_is_rejected(self) -> None:
        payload = self.questions[1].model_dump(mode="json")
        payload["question_id"] = "qa_bad_answer"
        payload["answer"]["canonical_value"] = 108
        bad_question = QuestionRecord.model_validate(payload)
        errors = validate_records(self.events, [bad_question])
        self.assertTrue(any("oracle returned 107" in error for error in errors))

    def test_loader_reports_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "bad.jsonl"
            path.write_text("{not-json}\n", encoding="utf-8")
            records, errors = load_jsonl(path, EventRecord)
        self.assertEqual(records, [])
        self.assertEqual(len(errors), 1)


if __name__ == "__main__":
    unittest.main()
