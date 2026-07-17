export type EmploymentType = 'full_time' | 'part_time' | 'internship' | 'contract' | 'freelance';
export type WorkMode = 'onsite' | 'hybrid' | 'remote';
export type ApplicationReadiness = 'low' | 'medium' | 'high';

export type JobPosting = {
  id: string;
  user_id: string;
  title: string;
  company_name: string;
  location: string | null;
  employment_type: EmploymentType | null;
  work_mode: WorkMode | null;
  source_url: string | null;
  description: string;
  status: 'saved' | 'analyzing' | 'analyzed' | 'archived';
  created_at: string;
  updated_at: string;
};

export type ExternalJobPosting = {
  external_id: string;
  source: 'jsearch' | 'jooble' | 'adzuna';
  title: string;
  company_name: string;
  location: string | null;
  description: string;
  source_url: string;
  created_at: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  employment_type: EmploymentType | null;
  work_mode: WorkMode | null;
  category: string | null;
};

export type JobSearchResponse = {
  jobs: ExternalJobPosting[];
  page: number;
  results_per_page: number;
  total_results: number | null;
  query: string;
  location: string | null;
  providers_used?: string[];
  providers_failed?: string[];
};

export type CreateJobPostingInput = {
  title: string;
  company_name: string;
  location?: string | null;
  employment_type?: EmploymentType | null;
  work_mode?: WorkMode | null;
  source_url?: string | null;
  description: string;
};

export type JobMatch = {
  id: string;
  user_id: string;
  job_posting_id: string;
  analysis_id: string;
  match_score: number;
  summary: string;
  matched_skills: string[];
  missing_skills: string[];
  strengths: string[];
  risks: string[];
  recommendations: string[];
  application_readiness: ApplicationReadiness;
  created_at: string;
  updated_at: string;
};

export type CompletedAnalysisOption = {
  id: string;
  target_role: string;
  created_at: string;
};
