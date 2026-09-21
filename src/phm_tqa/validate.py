"""Validate JSONL records and reproduce every stored gold answer."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from .oracle import EventStore, OracleError, evaluate_program
from .schema import EvidenceStatus, EventRecord, EventType, QuestionRecord, SourceSplit


T = TypeVar("T", bound=BaseModel)


def load_jsonl(path: Path, model: type[T]) -> tuple[list[T], list[str]]:
    records: list[T] = []
    errors: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                records.append(model.model_validate(payload))
            except (json.JSONDecodeError, ValidationError) as exc:
                errors.append(f"{path}:{line_number}: {exc}")
    return records, errors


def answers_equal(actual: object, expected: object, tolerance: float | None) -> bool:
    if tolerance is None:
        return actual == expected
    if not isinstance(actual, (int, float)) or isinstance(actual, bool):
        return False
    if not isinstance(expected, (int, float)) or isinstance(expected, bool):
        return False
    return math.isclose(float(actual), float(expected), abs_tol=tolerance, rel_tol=0.0)


def validate_records(
    events: list[EventRecord], questions: list[QuestionRecord]
) -> list[str]:
    errors: list[str] = []
    event_ids = [event.event_id for event in events]
    question_ids = [question.question_id for question in questions]
    if len(set(event_ids)) != len(event_ids):
        errors.append("duplicate event_id detected")
    if len(set(question_ids)) != len(question_ids):
        errors.append("duplicate question_id detected")

    unit_partitions: dict[str, set[str]] = {}
    paraphrase_partitions: dict[str, set[str]] = {}
    for question in questions:
        for unit_id in question.unit_ids:
            unit_partitions.setdefault(unit_id, set()).add(question.partition.value)
        family_id = question.generation.paraphrase_family_id
        paraphrase_partitions.setdefault(family_id, set()).add(question.partition.value)
    for unit_id, partitions in unit_partitions.items():
        if len(partitions) > 1:
            errors.append(
                f"unit {unit_id} crosses benchmark partitions: {sorted(partitions)}"
            )
    for family_id, partitions in paraphrase_partitions.items():
        if len(partitions) > 1:
            errors.append(
                f"paraphrase family {family_id} crosses partitions: "
                f"{sorted(partitions)}"
            )

    for event in events:
        dataset = event.dataset.lower().replace("-", "")
        if dataset == "cmapss":
            if (
                event.source_split is SourceSplit.TEST
                and event.event_type is EventType.FAILURE
                and event.evidence_status is EvidenceStatus.OBSERVED
            ):
                errors.append(
                    f"{event.event_id}: C-MAPSS test failure cannot be marked observed"
                )
            if (
                event.event_type is EventType.DEGRADATION_ONSET
                and event.evidence_status is EvidenceStatus.OBSERVED
            ):
                errors.append(
                    f"{event.event_id}: C-MAPSS degradation onset must be derived"
                )

    try:
        store = EventStore(events)
    except OracleError as exc:
        errors.append(str(exc))
        return errors

    for question in questions:
        missing_context = set(question.context.event_ids) - set(store.by_id)
        if missing_context:
            errors.append(
                f"{question.question_id}: missing context events "
                f"{sorted(missing_context)}"
            )
        missing = set(question.gold_fact_ids) - set(store.by_id)
        if missing:
            errors.append(
                f"{question.question_id}: missing gold facts {sorted(missing)}"
            )
            continue
        predicted = [
            fact_id
            for fact_id in question.gold_fact_ids
            if store.by_id[fact_id].evidence_status is EvidenceStatus.PREDICTED
        ]
        if predicted:
            errors.append(
                f"{question.question_id}: predicted events cannot define gold: {predicted}"
            )
        mismatched_source = [
            fact_id
            for fact_id in question.gold_fact_ids
            if (
                store.by_id[fact_id].dataset != question.dataset
                or store.by_id[fact_id].subset != question.subset
            )
        ]
        if mismatched_source:
            errors.append(
                f"{question.question_id}: gold facts use another dataset/subset: "
                f"{mismatched_source}"
            )
        mismatched_units = [
            fact_id
            for fact_id in question.gold_fact_ids
            if store.by_id[fact_id].unit_id not in question.unit_ids
        ]
        if mismatched_units:
            errors.append(
                f"{question.question_id}: gold facts use unlisted target units: "
                f"{mismatched_units}"
            )

        try:
            result = evaluate_program(question.program, store)
        except (OracleError, TypeError, ValueError) as exc:
            errors.append(f"{question.question_id}: oracle failed: {exc}")
            continue

        expected_facts = set(question.gold_fact_ids)
        consumed_facts = set(result.consumed_event_ids)
        if consumed_facts != expected_facts:
            errors.append(
                f"{question.question_id}: program consumed {sorted(consumed_facts)}, "
                f"but gold_fact_ids are {sorted(expected_facts)}"
            )
        if not answers_equal(
            result.value,
            question.answer.canonical_value,
            question.answer.tolerance,
        ):
            errors.append(
                f"{question.question_id}: oracle returned {result.value!r}, "
                f"expected {question.answer.canonical_value!r}"
            )

    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate PHM temporal QA event and question JSONL files."
    )
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    events, event_errors = load_jsonl(args.events, EventRecord)
    questions, question_errors = load_jsonl(args.questions, QuestionRecord)
    errors = event_errors + question_errors
    if not errors:
        errors.extend(validate_records(events, questions))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Validation failed with {len(errors)} error(s).")
        return 1
    print(
        f"Validation passed: {len(events)} events, "
        f"{len(questions)} questions, all gold programs reproduced."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
