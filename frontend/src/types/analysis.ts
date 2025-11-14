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


