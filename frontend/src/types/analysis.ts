export interface AnalysisOverview {
  overall_score: number;
  grade: string;
  strengths: string[];
  weaknesses: string[];
  section_analysis: {
    contact?: SectionScore;
    skills?: SectionScore;
    experience?: SectionScore;
    projects?: SectionScore;
    education?: SectionScore;
  };
  improvements: {
    priority_improvements: Improvement[];
    optional_enhancements: Improvement[];
    ats_optimization: string[];
    content_suggestions: Improvement[];
  };
  metrics: {
    word_count: number;
    section_counts: Record<string, { item_count: number; word_count: number }>;
    completeness_scores: Record<string, number>;
    diversity_metrics: Record<string, number>;
  };
}

export interface SectionScore {
  score: number;
  max_score?: number;
  completeness?: string;
  total_skills?: number;
  total_positions?: number;
  total_projects?: number;
  total_degrees?: number;
  breakdown?: Record<string, number>;
  has_details?: number;
  has_tech_stack?: number;
  has_gpa?: number;
}

export interface Improvement {
  section: string;
  suggestion: string;
  impact: string;
}

export interface ATSScore {
  ats_score: number;
  keyword_suggestions: string[];
  optimization_tips: string[];
  semantic_analysis?: string;
  format_score?: number;
  content_score?: number;
  keyword_density?: number;
}

export interface SkillsGap {
  target_role: string;
  current_skills: string[];
  missing_required: string[];
  missing_recommended: string[];
  matching_skills: string[];
  gap_score: number;
  recommendations: string[];
}

export interface JobMatch {
  role: string;
  match_score: number;
  skills_match: number;
  resume_quality: number;
  missing_skills: string[];
  recommendations: string[];
}

export interface CareerPath {
  current_focus: string;
  career_paths: CareerPathItem[];
  next_steps: string[];
}

export interface CareerPathItem {
  title: string;
  timeline: string;
  required_skills: string[];
  description: string;
}

export interface JobRecommendation {
  title: string;
  url: string;
  content?: string;
  description?: string;
  company?: string;
  location?: string;
  job_type?: string;
  salary_min?: number;
  salary_max?: number;
  source?: string;
  posted_date?: string;
  score?: number;
}

export interface JobRecommendations {
  jobs: JobRecommendation[];
  role_focus: string;
  total_found: number;
  source?: string;
}

export interface SalaryRange {
  level: string;
  range: string;
  median: string;
  note: string;
}

export interface SalaryInsights {
  role: string;
  years_experience: number;
  location: string;
  salary_ranges: SalaryRange[];
  sources?: string[];
  error?: string;
}

export interface Keywords {
  missing_technical: string[];
  missing_common: string[];
  recommended_keywords: string[];
}

export interface InterviewPrep {
  role: string;
  tips: string;
  preparation_checklist: string[];
}

export interface InterviewQuestions {
  questions: string;
  categories: string[];
  total_questions: number;
}

export interface STARExample {
  situation: string;
  task: string;
  action: string;
  result: string;
}

export interface STARExamples {
  examples: STARExample[];
  total: number;
  format: string;
}

export interface ResumeProfile {
  id: string;
  user_id: string;
  name: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  socials: Record<string, string> | null;
  summary: string | null;
  raw_data: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
}

export interface ResumeComparison {
  profile_id: string;
  comparison: {
    skills: ComparisonItem;
    experience: ComparisonItem;
    education: ComparisonItem;
    contact_completeness: ComparisonItem;
  };
  industry_standards: Record<string, unknown>;
}

export interface ComparisonItem {
  your_count: number;
  industry_average: number;
  status: string;
  required?: number;
}

// ── Job Application Tracking ───────────────────────────────────────────────

export type ApplicationStatus =
  | "applied"
  | "interviewing"
  | "offer"
  | "rejected"
  | "withdrawn";

export interface JobApplication {
  id: string;
  user_id: string;
  job_title: string;
  company: string | null;
  job_url: string | null;
  source: string | null;
  location: string | null;
  status: ApplicationStatus;
  notes: string | null;
  job_data: Record<string, unknown> | null;
  applied_at: string | null;
  updated_at: string | null;
}

export interface JobApplicationsResponse {
  applications: JobApplication[];
  total: number;
  by_status: Record<ApplicationStatus, number>;
}

// ── Recommendation Feedback ────────────────────────────────────────────────

export type FeedbackValue = "helpful" | "not_helpful";
export type FeedbackItemType = "job" | "course";

export interface RecommendationFeedback {
  id: string;
  user_id: string;
  item_type: FeedbackItemType;
  item_identifier: string;
  feedback: FeedbackValue;
  is_helpful: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface FeedbackResponse {
  feedback: RecommendationFeedback[];
  total: number;
}

// ── Playwright Auto-Fill ───────────────────────────────────────────────────

export type AutoFillStatus =
  | "filled"
  | "unsupported"
  | "no_fields_found"
  | "error";

/** Legacy: blocking response (kept for compat) */
export interface AutoFillResult {
  status: AutoFillStatus;
  portal: string | null;
  fields_filled: string[];
  screenshot: string | null; // base64 PNG
  message: string;
}

// ── Task-based autofill (non-blocking + polling) ───────────────────────────

/** Returned immediately by POST /auto-fill */
export interface AutoFillStartResult {
  task_id: string;
  status: "started";
  portal: string | null;
  poll_url: string;
}

/** A single progress step captured during autofill */
export interface AutoFillStep {
  step: "navigating" | "loaded" | "analyzing" | "filling" | "done" | "no_fields" | "error" | "session_missing" | "awaiting_confirmation";
  message: string;
  screenshot: string | null; // base64 JPEG, null for some steps
  timestamp: string;         // ISO
}

export type AutoFillTaskStatus = "pending" | "running" | "done" | "error" | "awaiting_confirmation";

export interface AutoFillConfirmDetails {
  job: string;
  portal: string | null;
  fields_filled: string[];
  filling_summary: string[];
}

/** Returned by GET /auto-fill/{task_id} */
export interface AutoFillTask {
  task_id: string;
  status: AutoFillTaskStatus;
  user_id: string;
  job_url: string;
  portal: string | null;
  steps: AutoFillStep[];
  fields_filled: string[];
  result_status: AutoFillStatus | "unsupported" | "submitted" | "cancelled" | null;
  error: string | null;
  started_at: string;
  finished_at: string | null;
  confirm_details?: AutoFillConfirmDetails;
}

// ── Wave 10 Future Scale Features (Strategy, digests, reviews) ────────────────

export interface UserDigestBrief {
  id: string;
  sent_at: string | null;
  health_score: {
    score: number;
    delta: number;
    primary_insight?: string;
  };
  delivery_status: string;
}

export interface DigestJobBrief {
  id: string;
  title: string;
  company_name: string;
}

export interface UserDigestDetail {
  id: string;
  sent_at: string | null;
  content: {
    health_score: {
      score: number;
      delta: number;
      primary_insight: string;
    };
    market_insights: string;
    position_delta: {
      resolved_gaps: (string | { name: string; frequency?: number })[];
      remaining_gaps: (string | { name: string; frequency?: number })[];
    };
    recommendations: DigestJobBrief[];
  };
  delivery_status: string;
}

export interface StrategyReviewBrief {
  id: string;
  created_at: string;
  status: "PENDING_REVIEW" | "COMPLETED" | "SKIPPED";
  health_score_start: number;
  health_score_end: number;
  completed_at: string | null;
}

export interface StrategyActionItem {
  id: string;
  description: string;
  difficulty: "EASY" | "MODERATE" | "HARD";
  status: "TODO" | "COMPLETED" | "CANCELLED";
  target_date: string | null;
}

export interface StrategyReviewDetail {
  id: string;
  status: "PENDING_REVIEW" | "COMPLETED" | "SKIPPED";
  goals: {
    target_role: string;
    timeline_months?: number;
    [key: string]: unknown;
  };
  metrics: {
    health_score_start: number;
    current_health_score: number;
  };
  insights_summary: string;
  action_items: StrategyActionItem[];
}

// ── Wave 6 Agent HITL Approvals ──────────────────────────────────────────────
export interface AgentApprovalRequest {
  id: string;
  thread_id: string;
  action_type: string;
  payload: Record<string, any>;
  status: "pending" | "approved" | "rejected" | "modified";
  created_at: string;
}

export interface AgentDecisionLog {
  id: string;
  current_node: string;
  routing_decision: string;
  reasoning_explanation: string;
  created_at: string;
}

// ── Wave 7 Workflow Execution ────────────────────────────────────────────────
export interface WorkflowExecutionLog {
  workflow_id: string;
  run_id: string;
  workflow_type: string;
  status: string;
  task_queue: string;
  created_at: string;
  updated_at: string;
}

export interface BrowserExecutionLog {
  id: string;
  application_id: string;
  step_index: number;
  action_type: string;
  target_selector: string | null;
  value_entered: string | null;
  screenshot_path: string | null;
  html_archive_path: string | null;
  status: string;
  error_details: string | null;
  created_at: string;
}

export interface ApplicationExecutionLogs {
  checkpoints: {
    id: string;
    current_state: string;
    checkpoint_data: Record<string, any>;
    saved_at: string;
  }[];
  form_logs: {
    id: string;
    step_number: number;
    step_name: string;
    request_payload: Record<string, any>;
    response_status: number;
    error_captured: string | null;
    created_at: string;
  }[];
  browser_logs: BrowserExecutionLog[];
}

// ── Wave 8 Calibration & Evaluations ────────────────────────────────────────
export interface EvaluationRunBrief {
  id: string;
  component_name: string;
  environment: string;
  status: string;
  commit_sha: string | null;
  started_at: string;
}

export interface AgentEvaluationResult {
  is_hallucinating: boolean;
  faithfulness_score: number;
  unattributed_statements: string[];
  reasoning: string;
}

export interface MetricDefinition {
  name: string;
  value: number;
  status: "pass" | "fail" | "warn";
  description?: string;
}

export interface EvaluationReport {
  run_id: string;
  component_name: string;
  environment: string;
  status: string;
  commit_sha: string | null;
  metrics: MetricDefinition[];
  results: Record<string, any>;
  created_at: string;
}

export interface BenchmarkReport {
  user_id: string;
  cohort_id: string;
  peer_count: number;
  percentiles: {
    skill_alignment: number;
    positioning: number;
    compensation: number;
    overall: number;
  };
  averages: {
    skill_alignment: number;
    positioning: number;
    compensation: number;
    overall: number;
  };
  recommendations: string[];
}

export interface ModelRegistrationInfo {
  model_name: string;
  version_tag: string;
  run_id: string;
  stage: string;
  registered_at: string;
  metrics: Record<string, number>;
}
