export type CaseItem = {
  id: string; title: string; case_type: string; stage: string; status: string;
  client_name: string; opposing_party: string; lead_lawyer: string; summary: string;
  risk_level: string; progress: number; is_demo: boolean; updated_at: string;
}

export type Source = { document_id: string; filename: string; page_number?: number; quote: string }
export type Reviewable = { id: string; review_status: string; confidence?: number; version?: number; sources?: Source[] }
export type DocumentItem = { id: string; filename: string; category: string; parse_status: string; parse_warning: string; page_count: number; created_at: string }
export type Fact = Reviewable & { fact_type: string; content: string; event_date?: string; has_conflict: boolean }
export type TimelineEvent = Reviewable & { event_date?: string; title: string; description: string; has_conflict: boolean; needs_verification: boolean }
export type Evidence = Reviewable & { name: string; evidence_type: string; fact_to_prove: string; support_status: string }
export type MissingMaterial = Reviewable & { name: string; reason: string; priority: string; suggested_action: string; rule_id?: string }
export type Risk = Reviewable & { risk_type: string; description: string; trigger_basis: string; level: string; suggested_review: string; mandatory_human_review: boolean }
export type Compensation = Reviewable & { name: string; evidence_summary: string; missing_evidence: string; required_parameters: string[]; risk_note: string }

export type Workspace = {
  case: CaseItem; documents: DocumentItem[]; facts: Fact[]; timeline: TimelineEvent[];
  evidence: Evidence[]; issues: Array<Reviewable & { title: string; analysis: string; information_gap: string; lawyer_question: string }>;
  missing_materials: MissingMaterial[]; risks: Risk[]; tasks: Array<Reviewable & { name: string; trigger_reason: string; priority: string; status: string }>;
  compensation_items: Compensation[]; traffic_risks: Risk[]; injuries: Array<Reviewable & { body_part: string; diagnosis_text: string; has_conflict: boolean }>;
  treatments: Array<Reviewable & { institution: string; treatment_type: string; start_date: string; end_date: string; description: string }>;
  medical_expenses: Array<Reviewable & { invoice_number: string; expense_date: string; amount: number; linked_statement: boolean; conflict_note: string }>;
  insurance: Array<Reviewable & { insurer: string; insurance_type: string; coverage_text: string; materials_complete: boolean }>;
  traffic_accident: Array<Reviewable & { accident_date: string; location: string; responsibility_text: string; police_handling: string }>;
  reports: Array<Reviewable & { title: string; content: string; disclaimer: string; citation_complete: boolean }>;
  legal_citations: Array<Reviewable & { title: string; excerpt: string; source_name: string; source_url: string; published_or_updated_at: string; jurisdiction: string; scope: string; stale_risk: boolean }>;
  document_quality: Array<{ id: string; document_id: string; text_quality_score: number; injection_risk: boolean; security_flags: string[]; warnings: string[]; requires_human_review: boolean; ocr_provider: string }>;
  parties: Array<{ id: string; name: string; role: string; party_type: string }>;
  relationships: Array<Reviewable & { from_party_id: string; to_party_id: string; relationship_type: string; description: string }>;
}

export type DocumentPreview = {
  id: string; filename: string; mime_type: string; page_number: number; page_count: number;
  text: string; highlight: string; requested_highlight?: string; highlight_exact?: boolean; highlight_start: number; highlight_end: number;
  has_original: boolean; parse_warning: string;
}

export type Member = { id: string; email: string; display_name: string; role: string; status: string }

export type QualityReport = {
  overall_score: number; document_parse_rate: number; document_quality_score: number;
  fact_source_coverage: number; fact_review_completion: number; mandatory_risk_review_completion: number;
  citation_freshness_rate?: number; unsupported_model_outputs_rejected: number;
  counts: Record<string, number>; warnings: string[];
}

export type CurrentUser = {
  user: { id: string; email: string; display_name: string };
  workspace: { id: string; name: string; role: string };
  auth_disabled: boolean;
}

export type KnowledgeSource = {
  id: string; scope: string; title: string; excerpt: string; source_name: string; source_url: string;
  published_or_updated_at: string; jurisdiction: string; applicability_scope: string;
  effective_status: string; verified_by: string; stale_risk: boolean;
}
