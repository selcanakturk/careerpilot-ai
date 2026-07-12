export type CVAnalysis = {
  id: string;
  user_id: string;
  cv_upload_id: string;
  target_role: string;
  status: string;
  overall_score: number;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  skill_gaps: string[];
  cv_suggestions: string[];
  created_at: string;
  updated_at: string;
};
