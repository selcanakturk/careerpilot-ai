import type { CVOptimizeResponse, CVOptimizerProvider } from './cvOptimizer';

export type CareerCopilotRequest = {
  analysis_id: string;
  message: string;
  job_external_id?: string | null;
  provider?: CVOptimizerProvider | null;
};

export type CareerCopilotActionType =
  | 'open_cv_optimizer'
  | 'open_jobs'
  | 'open_roadmap'
  | 'open_profile'
  | 'open_upload_cv'
  | 'open_history';

export type CareerCopilotSuggestedAction = {
  type: CareerCopilotActionType;
  label: string;
  target: string;
};

export type CareerCopilotResponse = {
  reply: string;
  suggested_action: CareerCopilotSuggestedAction | null;
  tool_result: CareerCopilotToolResult | null;
};

export type CareerCopilotCVOptimizationToolData = {
  current_match: number;
  estimated_match: number;
  changes: string[];
  major_changes?: string[];
  optimization_summary?: string;
  before_professional_summary?: string;
  optimized_professional_summary?: string;
  optimized_skills?: string[];
  explanation?: string;
  optimized_cv: CVOptimizeResponse['optimized_cv'];
};

export type CareerCopilotToolResult = {
  type: 'cv_optimization';
  status: 'completed' | 'requires_input' | 'failed';
  data: CareerCopilotCVOptimizationToolData | null;
};

export type CareerCopilotMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
  suggestedAction?: CareerCopilotSuggestedAction | null;
  toolResult?: CareerCopilotToolResult | null;
};
