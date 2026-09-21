"""Execute the restricted temporal program DSL against canonical events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .schema import (
    ArgExtremeProgram,
    CompareProgram,
    CountProgram,
    EventFieldValue,
    EventRecord,
    EventSelector,
    GoldProgram,
    LiteralValue,
    LookupProgram,
    SelectorMode,
    SubtractProgram,
    ValueExpression,
)


class OracleError(ValueError):
    """Raised when a gold program is ambiguous or cannot be executed."""


@dataclass(frozen=True)
class OracleResult:
    value: Any
    consumed_event_ids: frozenset[str]


class EventStore:
    def __init__(self, events: list[EventRecord]):
        self.events = list(events)
        self.by_id = {event.event_id: event for event in events}
        if len(self.by_id) != len(events):
            raise OracleError("event IDs must be unique")

    @staticmethod
    def _resolve_field(event: EventRecord, field: str) -> Any:
        value: Any = event
        for part in field.split("."):
            if isinstance(value, EventRecord):
                if not hasattr(value, part):
                    raise OracleError(f"unknown event field: {field}")
                value = getattr(value, part)
            elif isinstance(value, dict):
                if part not in value:
                    raise OracleError(f"unknown event attribute path: {field}")
                value = value[part]
            else:
                raise OracleError(f"cannot descend into field path: {field}")
        return value.value if hasattr(value, "value") else value

    def select(self, selector: EventSelector) -> list[EventRecord]:
        if selector.event_id is not None:
            event = self.by_id.get(selector.event_id)
            if event is None:
                raise OracleError(f"unknown event_id: {selector.event_id}")
            candidates = [event]
        else:
            candidates = list(self.events)

        if selector.unit_id is not None:
            candidates = [e for e in candidates if e.unit_id == selector.unit_id]
        if selector.event_type is not None:
            candidates = [e for e in candidates if e.event_type == selector.event_type]
        if selector.cycle_contains is not None:
            cycle = selector.cycle_contains
            candidates = [
                e for e in candidates if e.cycle_start <= cycle <= e.effective_cycle_end
            ]
        for field, expected in selector.filters.items():
            candidates = [
                e for e in candidates if self._resolve_field(e, field) == expected
            ]

        candidates.sort(key=lambda e: (e.cycle_start, e.effective_cycle_end, e.event_id))
        if selector.selector is SelectorMode.FIRST:
            candidates = candidates[:1]
        elif selector.selector is SelectorMode.LAST:
            candidates = candidates[-1:]
        elif selector.selector is SelectorMode.ONLY and len(candidates) != 1:
            raise OracleError(
                f"selector expected exactly one event, found {len(candidates)}"
            )
        if not candidates:
            raise OracleError("selector matched no events")
        return candidates

    def value(self, expression: ValueExpression) -> OracleResult:
        if isinstance(expression, LiteralValue):
            return OracleResult(expression.value, frozenset())
        if isinstance(expression, EventFieldValue):
            events = self.select(expression.event)
            if len(events) != 1:
                raise OracleError("event_field requires a single selected event")
            event = events[0]
            return OracleResult(
                self._resolve_field(event, expression.field),
                frozenset({event.event_id}),
            )
        raise OracleError(f"unsupported value expression: {type(expression).__name__}")


def evaluate_program(program: GoldProgram, store: EventStore) -> OracleResult:
    if isinstance(program, LookupProgram):
        return store.value(program.target)

    if isinstance(program, SubtractProgram):
        left = store.value(program.left)
        right = store.value(program.right)
        try:
            value = left.value - right.value
        except TypeError as exc:
            raise OracleError("subtract operands must be numeric") from exc
        return OracleResult(value, left.consumed_event_ids | right.consumed_event_ids)

    if isinstance(program, CompareProgram):
        left = store.value(program.left)
        right = store.value(program.right)
        relations = {
            "lt": lambda a, b: a < b,
            "le": lambda a, b: a <= b,
            "gt": lambda a, b: a > b,
            "ge": lambda a, b: a >= b,
            "eq": lambda a, b: a == b,
            "ne": lambda a, b: a != b,
        }
        value = relations[program.relation](left.value, right.value)
        return OracleResult(value, left.consumed_event_ids | right.consumed_event_ids)

    if isinstance(program, ArgExtremeProgram):
        evaluated = [(candidate.label, store.value(candidate.value)) for candidate in program.candidates]
        values = [result.value for _, result in evaluated]
        extreme = min(values) if program.op == "argmin" else max(values)
        winners = [label for label, result in evaluated if result.value == extreme]
        if len(winners) != 1:
            raise OracleError(f"{program.op} has a tie; gold answer would be ambiguous")
        consumed = frozenset().union(
            *(result.consumed_event_ids for _, result in evaluated)
        )
        return OracleResult(winners[0], consumed)

    if isinstance(program, CountProgram):
        events = store.select(program.events)
        value = len(events) if program.distinct_by == "event" else len({e.unit_id for e in events})
        return OracleResult(value, frozenset(e.event_id for e in events))

    raise OracleError(f"unsupported program: {type(program).__name__}")

