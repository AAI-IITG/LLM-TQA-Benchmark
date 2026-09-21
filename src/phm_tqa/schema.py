"""Canonical, provenance-aware schemas for PHM temporal QA."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


Scalar = str | int | float | bool


class StrictModel(BaseModel):
    """Base model that rejects misspelled or undeclared fields."""

    model_config = ConfigDict(extra="forbid")


class EvidenceStatus(str, Enum):
    OBSERVED = "observed"
    DERIVED = "derived"
    PREDICTED = "predicted"


class SourceSplit(str, Enum):
    TRAIN = "train"
    TEST = "test"
    SYNTHETIC = "synthetic"


class EventType(str, Enum):
    OBSERVATION = "observation"
    OPERATING_REGIME = "operating_regime"
    REGIME_CHANGE = "regime_change"
    THRESHOLD_CROSSING = "threshold_crossing"
    DEGRADATION_ONSET = "degradation_onset"
    FAULT = "fault"
    FAILURE = "failure"
    TRUNCATION = "truncation"
    MAINTENANCE = "maintenance"


class Provenance(StrictModel):
    dataset: str = Field(min_length=1)
    subset: str = Field(min_length=1)
    source_file: str = Field(min_length=1)
    source_row_start: int | None = Field(default=None, ge=1)
    source_row_end: int | None = Field(default=None, ge=1)
    extraction_method: str = Field(min_length=1)
    extraction_version: str = Field(min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    source_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    model_id: str | None = None

    @model_validator(mode="after")
    def rows_are_ordered(self) -> "Provenance":
        if (
            self.source_row_start is not None
            and self.source_row_end is not None
            and self.source_row_end < self.source_row_start
        ):
            raise ValueError("source_row_end must be >= source_row_start")
        return self


class EventRecord(StrictModel):
    benchmark_version: str = Field(min_length=1)
    event_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_.:-]+$")
    domain: str = Field(min_length=1)
    dataset: str = Field(min_length=1)
    subset: str = Field(min_length=1)
    source_split: SourceSplit
    unit_id: str = Field(min_length=1)
    event_type: EventType
    cycle_start: int = Field(ge=0)
    cycle_end: int | None = Field(default=None, ge=0)
    attributes: dict[str, Any] = Field(default_factory=dict)
    evidence_status: EvidenceStatus
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    provenance: Provenance

    @model_validator(mode="after")
    def check_event_semantics(self) -> "EventRecord":
        end = self.cycle_start if self.cycle_end is None else self.cycle_end
        if end < self.cycle_start:
            raise ValueError("cycle_end must be >= cycle_start")
        if self.dataset != self.provenance.dataset or self.subset != self.provenance.subset:
            raise ValueError("event dataset/subset must match provenance")
        if self.evidence_status is EvidenceStatus.PREDICTED and not self.provenance.model_id:
            raise ValueError("predicted events require provenance.model_id")
        if self.evidence_status is not EvidenceStatus.PREDICTED and self.provenance.model_id:
            raise ValueError("provenance.model_id is reserved for predicted events")
        return self

    @property
    def effective_cycle_end(self) -> int:
        return self.cycle_start if self.cycle_end is None else self.cycle_end


class SelectorMode(str, Enum):
    ONLY = "only"
    FIRST = "first"
    LAST = "last"
    ALL = "all"


class EventSelector(StrictModel):
    event_id: str | None = None
    unit_id: str | None = None
    event_type: EventType | None = None
    selector: SelectorMode = SelectorMode.ONLY
    cycle_contains: int | None = Field(default=None, ge=0)
    filters: dict[str, Scalar] = Field(default_factory=dict)

    @model_validator(mode="after")
    def has_selection_constraint(self) -> "EventSelector":
        if self.event_id is None and self.event_type is None:
            raise ValueError("selector requires event_id or event_type")
        if self.event_id is not None and self.selector is SelectorMode.ALL:
            raise ValueError("event_id cannot be combined with selector='all'")
        return self


class LiteralValue(StrictModel):
    kind: Literal["literal"] = "literal"
    value: Scalar


class EventFieldValue(StrictModel):
    kind: Literal["event_field"] = "event_field"
    event: EventSelector
    field: str = Field(min_length=1)


ValueExpression = Annotated[
    Union[LiteralValue, EventFieldValue], Field(discriminator="kind")
]


class LookupProgram(StrictModel):
    op: Literal["lookup"] = "lookup"
    target: ValueExpression


class SubtractProgram(StrictModel):
    op: Literal["subtract"] = "subtract"
    left: ValueExpression
    right: ValueExpression
    output_unit: str | None = None


class CompareProgram(StrictModel):
    op: Literal["compare"] = "compare"
    left: ValueExpression
    right: ValueExpression
    relation: Literal["lt", "le", "gt", "ge", "eq", "ne"]


class LabelledCandidate(StrictModel):
    label: Scalar
    value: ValueExpression


class ArgExtremeProgram(StrictModel):
    op: Literal["argmin", "argmax"]
    candidates: list[LabelledCandidate] = Field(min_length=1)


class CountProgram(StrictModel):
    op: Literal["count"] = "count"
    events: EventSelector
    distinct_by: Literal["event", "unit"] = "event"

    @model_validator(mode="after")
    def count_requires_all_matches(self) -> "CountProgram":
        if self.events.selector is not SelectorMode.ALL:
            raise ValueError("count requires events.selector='all'")
        return self


GoldProgram = Annotated[
    Union[
        LookupProgram,
        SubtractProgram,
        CompareProgram,
        ArgExtremeProgram,
        CountProgram,
    ],
    Field(discriminator="op"),
]


class QuestionType(str, Enum):
    POINT_STATE = "point_state"
    BEFORE_AFTER = "before_after"
    DURATION = "duration"
    ORDERING = "ordering"
    AGGREGATION = "aggregation"
    RUL = "rul"
    RELATIVE_TREND = "relative_trend"
    IMPLICIT_TIME = "implicit_time"


class Difficulty(str, Enum):
    SINGLE_HOP = "single_hop"
    MULTI_HOP = "multi_hop"
    LONG_HORIZON = "long_horizon"


class BenchmarkPartition(str, Enum):
    DEV = "dev"
    TEST = "test"
    HARD = "hard"


class ContextRepresentation(str, Enum):
    EVENT_LOG = "event_log"
    RAW_WINDOW = "raw_window"
    TEXT = "text"
    KG = "kg"


class ContextSpec(StrictModel):
    representation: ContextRepresentation
    event_ids: list[str] = Field(default_factory=list)
    trajectory_ref: str | None = None
    cutoff_cycle: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def context_is_resolvable(self) -> "ContextSpec":
        if not self.event_ids and self.trajectory_ref is None:
            raise ValueError("context requires event_ids or trajectory_ref")
        return self


class GoldAnswer(StrictModel):
    value_type: Literal["boolean", "integer", "float", "categorical", "list"]
    canonical_value: Scalar | list[Scalar]
    unit: str | None = None
    tolerance: float | None = Field(default=None, ge=0.0)
    acceptable_text: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def type_matches_value(self) -> "GoldAnswer":
        value = self.canonical_value
        valid = {
            "boolean": isinstance(value, bool),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "float": isinstance(value, (int, float)) and not isinstance(value, bool),
            "categorical": isinstance(value, str),
            "list": isinstance(value, list),
        }[self.value_type]
        if not valid:
            raise ValueError("canonical_value does not match value_type")
        if self.tolerance is not None and self.value_type != "float":
            raise ValueError("tolerance is only valid for float answers")
        return self


class GenerationProvenance(StrictModel):
    method: Literal["template", "llm_paraphrase", "human"]
    template_id: str = Field(min_length=1)
    template_family_id: str = Field(min_length=1)
    paraphrase_family_id: str = Field(min_length=1)
    generator_version: str = Field(min_length=1)
    paraphrase_model: str | None = None
    verified_by: Literal["oracle", "human_and_oracle"]

    @model_validator(mode="after")
    def llm_paraphrase_has_model(self) -> "GenerationProvenance":
        if self.method == "llm_paraphrase" and not self.paraphrase_model:
            raise ValueError("llm_paraphrase requires paraphrase_model")
        if self.method != "llm_paraphrase" and self.paraphrase_model:
            raise ValueError("paraphrase_model is only valid for llm_paraphrase")
        return self


class LeakageControls(StrictModel):
    answer_string_absent_from_context: bool
    future_facts_hidden_from_context: bool
    unit_grouped_split: bool
    template_family_stratified: bool
    paraphrases_grouped_split: bool


class QuestionRecord(StrictModel):
    benchmark_version: str = Field(min_length=1)
    question_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9_.:-]+$")
    domain: str = Field(min_length=1)
    dataset: str = Field(min_length=1)
    subset: str = Field(min_length=1)
    partition: BenchmarkPartition
    unit_ids: list[str] = Field(min_length=1)
    question_type: QuestionType
    temporal_operators: list[str] = Field(min_length=1)
    difficulty: Difficulty
    question_text: str = Field(min_length=1)
    context: ContextSpec
    answer: GoldAnswer
    program: GoldProgram
    gold_fact_ids: list[str] = Field(min_length=1)
    reasoning_steps: list[str] = Field(min_length=1)
    generation: GenerationProvenance
    leakage_controls: LeakageControls

    @model_validator(mode="after")
    def record_is_internally_consistent(self) -> "QuestionRecord":
        if len(set(self.unit_ids)) != len(self.unit_ids):
            raise ValueError("unit_ids must be unique")
        if len(set(self.gold_fact_ids)) != len(self.gold_fact_ids):
            raise ValueError("gold_fact_ids must be unique")
        if len(set(self.context.event_ids)) != len(self.context.event_ids):
            raise ValueError("context.event_ids must be unique")
        return self
