from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UserProfileSnapshot(BaseModel):
    id: UUID
    skills: List[str]
    experience_years: float
    target_roles: List[str]
    target_salary_min: Optional[int] = None


class JobDocument(BaseModel):
    job_id: str
    title: str
    company_name: str
    description: str
    inferred_skills: List[str]
    relevance_score: float


class CareerPilotState(BaseModel):
    thread_id: str
    user_id: UUID
    user_profile: UserProfileSnapshot
    user_input_query: str
    retrieved_jobs: List[JobDocument] = Field(default_factory=list)
    research_signals: Dict[str, Any] = Field(default_factory=dict)
    intelligence_report: Optional[Dict[str, Any]] = None
    next_node_override: Optional[str] = None
    approved_by_user: bool = False
    audit_trail: List[str] = Field(default_factory=list)
    repair_counter: Dict[str, int] = Field(default_factory=dict)
    last_evaluation_feedback: Optional[str] = None
    evaluation_scores: Dict[str, float] = Field(default_factory=dict)


class RoutingDecision(BaseModel):
    next_node: str = Field(description="The key of the node to route to. Allowed: 'research_agent', 'intelligence_agent', 'human_gate', 'end'.")
    reasoning: str = Field(description="Structured explanation for this routing path decision.")
    required_context: List[str] = Field(description="List of fields required in state before executing next node.")


class DecisionLogEntry(BaseModel):
    id: UUID
    thread_id: str
    run_id: UUID
    current_node: str
    routing_decision: str
    reasoning_explanation: str
    created_at: datetime


class ResearchSource(BaseModel):
    source_type: str = Field(description="Type of source: 'job_posting', 'news_article', 'sec_filing', 'company_page'")
    reference_id: Optional[str] = None
    url: Optional[str] = None
    snippet: Optional[str] = None
    verified_at: datetime


class RequirementsMap(BaseModel):
    critical: List[str] = Field(description="Must-have competencies or tools.")
    preferred: List[str] = Field(description="Strong positive indicators.")
    bonus: List[str] = Field(description="Nice-to-have or peripheral skills.")


class CompanySignals(BaseModel):
    hiring_velocity: str = Field(description="Hiring pace: 'stagnant', 'moderate', 'high'")
    tech_stack: List[str] = Field(description="Verified technologies used by the team.")
    organizational_notes: Optional[str] = None


class ResearchReport(BaseModel):
    company_name: str
    company_domain: Optional[str] = None
    role_category: str
    requirements: RequirementsMap
    signals: CompanySignals
    sources: List[ResearchSource]
    confidence_score: float = Field(ge=0.0, le=1.0)


class EvidenceBlock(BaseModel):
    claim: str
    source_reference: str = Field(description="The specific ID, posting, or document source backing this claim.")
    source_type: str = Field(description="Type of source: e.g. 'job_post', 'peer_benchmark', 'resume_experience'")
    confidence_rating: str = Field(description="E.g., 'high', 'medium', 'low'")


class RoadmapItem(BaseModel):
    priority_order: int
    actionable_task: str = Field(description="Concrete step the user must take (e.g., 'Add Python design patterns under projects').")
    estimated_impact: str = Field(description="Expected fit improvement or career score impact.")
    associated_gaps: List[str] = Field(description="Which gaps this task resolves.")


class CompensationAnalysis(BaseModel):
    market_percentile: float
    salary_range_min: int
    salary_range_max: int
    negotiation_advice: str


class IntelligenceReportPayload(BaseModel):
    overall_health_score: float = Field(ge=0.0, le=100.0)
    position_delta_score: float = Field(ge=0.0, le=100.0)
    fit_score: float = Field(ge=0.0, le=100.0)
    summary_explanation: str
    evidence_trail: List[EvidenceBlock]
    profile_roadmap: List[RoadmapItem]
    compensation_context: CompensationAnalysis


class MessageModel(BaseModel):
    id: UUID
    role: str = Field(description="Role identifier: 'user', 'assistant', or 'system'")
    content: str
    tokens_count: int
    created_at: datetime


class ThreadMemory(BaseModel):
    thread_id: str
    user_id: UUID
    summary: Optional[str] = None
    messages: List[MessageModel] = Field(default_factory=list)


class RetrievalCandidate(BaseModel):
    job_id: UUID
    title: str
    company_name: str
    bm25_rank: Optional[int] = None
    vector_rank: Optional[int] = None
    rrf_score: Optional[float] = None
    final_score: float = Field(description="The final score output by the Cross-Encoder reranker.")
    retrieval_sources: List[str] = Field(description="List containing retrieval paths, e.g. ['vector', 'bm25']")


class HybridRetrievalRequest(BaseModel):
    query: str
    user_id: Optional[UUID] = None
    limit: int = 10
    rerank_top_k: int = 30


class ApprovalRequestPayload(BaseModel):
    job_title: str
    company_name: str
    resume_url: str
    proposed_answers: Dict[str, str] = Field(default_factory=dict)
    additional_metadata: Dict[str, Any] = Field(default_factory=dict)


class ApprovalActionRequest(BaseModel):
    action: str = Field(description="Action must be 'approved', 'rejected', or 'modified'")
    edited_payload: Optional[Dict[str, Any]] = None


class ApprovalSummary(BaseModel):
    id: UUID
    thread_id: str
    action_type: str
    payload: ApprovalRequestPayload
    status: str
    created_at: datetime
