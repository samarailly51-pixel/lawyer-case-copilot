from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class SourceAnchoredPayload(BaseModel):
    document_id: str = Field(min_length=1)
    quote: str = Field(min_length=2, max_length=800)
    confidence: float = Field(ge=0, le=1)


class AccidentInfoPayload(SourceAnchoredPayload):
    accident_date: date | None = None
    location: str = Field(default="", max_length=240)
    parties: list[str] = Field(default_factory=list, max_length=20)
    vehicles: list[str] = Field(default_factory=list, max_length=20)
    responsibility_text: str = Field(default="", max_length=1200)
    police_handling: str = Field(default="", max_length=500)
    special_flags: list[str] = Field(default_factory=list, max_length=20)


class InjuryPayload(SourceAnchoredPayload):
    body_part: str = Field(default="待律师核对", max_length=120)
    diagnosis_text: str = Field(min_length=2, max_length=1200)
    diagnosis_date: date | None = None
    has_conflict: bool = False


class TreatmentPayload(SourceAnchoredPayload):
    institution: str = Field(default="", max_length=200)
    treatment_type: str = Field(default="待核对", max_length=60)
    start_date: date | None = None
    end_date: date | None = None
    description: str = Field(min_length=2, max_length=1200)


class MedicalExpensePayload(SourceAnchoredPayload):
    invoice_number: str = Field(default="", max_length=100)
    expense_date: date | None = None
    amount: float = Field(ge=0)
    institution: str = Field(default="", max_length=200)
    linked_statement: bool = False
    duplicate_warning: bool = False
    conflict_note: str = Field(default="", max_length=800)


class InsurancePayload(SourceAnchoredPayload):
    insurer: str = Field(default="待律师核对", max_length=200)
    insurance_type: str = Field(default="待核实", max_length=120)
    policy_number_masked: str = Field(default="", max_length=120)
    coverage_text: str = Field(default="", max_length=1000)
    materials_complete: bool = False


class DisabilityAppraisalPayload(SourceAnchoredPayload):
    institution: str = Field(default="", max_length=200)
    appraisal_date: date | None = None
    projects: list[str] = Field(default_factory=list, max_length=30)
    opinion_text: str = Field(default="", max_length=1200)
    materials_complete: bool = False


class TrafficInjuryExtractionPayload(BaseModel):
    accident_info: AccidentInfoPayload | None = None
    injuries: list[InjuryPayload] = Field(default_factory=list, max_length=50)
    treatments: list[TreatmentPayload] = Field(default_factory=list, max_length=100)
    medical_expenses: list[MedicalExpensePayload] = Field(default_factory=list, max_length=300)
    insurance: list[InsurancePayload] = Field(default_factory=list, max_length=20)
    disability_appraisals: list[DisabilityAppraisalPayload] = Field(default_factory=list, max_length=20)
    warnings: list[str] = Field(default_factory=list, max_length=100)


TRAFFIC_INJURY_EXTRACTION_JSON_SCHEMA = TrafficInjuryExtractionPayload.model_json_schema()
