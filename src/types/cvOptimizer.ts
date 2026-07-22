import type { ExternalJobPosting } from './job';

export type CVOptimizerProvider = ExternalJobPosting['source'];

export type CVOptimizeRequest = {
  analysis_id: string;
  job_external_id: string;
  provider: CVOptimizerProvider;
};

export type CVOptimizeResponse = {
  analysis_id: string;
  job_external_id: string;
  provider: CVOptimizerProvider;
  match_before: number;
  estimated_match_after: number;
  changes: string[];
  optimized_cv: Record<string, unknown>;
};
