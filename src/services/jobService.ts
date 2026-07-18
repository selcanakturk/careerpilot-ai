import { supabase } from '../lib/supabase';
import { ApiError, apiRequest } from './apiService';
import type {
  CompletedAnalysisOption,
  CreateJobPostingInput,
  JobMatch,
  JobPosting,
  JobSearchResponse,
} from '../types/job';

type DiscoverJobsInput = {
  query?: string;
  location?: string;
  page?: number;
  resultsPerPage?: number;
};

function normalizeJobError(error: unknown): Error {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return new Error('Your session has expired. Please sign in again.');
    }

    if (error.status === 404) {
      return new Error('The job posting or CV analysis could not be found.');
    }

    if (error.status === 503) {
      return new Error('The AI job matching service is busy. Please try again shortly.');
    }
  }

  if (error instanceof Error) {
    return error;
  }

  return new Error('Unable to complete the job matching request.');
}

function nullableText(value: string | null | undefined) {
  const normalizedValue = value?.trim();
  return normalizedValue ? normalizedValue : null;
}

export async function createJobPosting(input: CreateJobPostingInput): Promise<JobPosting> {
  try {
    return await apiRequest<JobPosting>('/api/jobs', {
      method: 'POST',
      body: JSON.stringify({
        ...input,
        location: nullableText(input.location),
        source_url: nullableText(input.source_url),
      }),
    });
  } catch (error) {
    throw normalizeJobError(error);
  }
}

export async function listJobPostings(): Promise<JobPosting[]> {
  try {
    return await apiRequest<JobPosting[]>('/api/jobs');
  } catch (error) {
    throw normalizeJobError(error);
  }
}

export async function discoverJobs({
  query,
  location,
  page = 1,
  resultsPerPage = 20,
}: DiscoverJobsInput = {}): Promise<JobSearchResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    results_per_page: resultsPerPage.toString(),
  });

  if (query?.trim()) {
    params.set('query', query.trim());
  }

  if (location?.trim()) {
    params.set('location', location.trim());
  }

  try {
    if (import.meta.env.DEV) {
      console.info('Job discovery request', {
        hasQuery: Boolean(query?.trim()),
        hasLocation: Boolean(location?.trim()),
        page,
        resultsPerPage,
      });
    }

    const response = await apiRequest<JobSearchResponse>(`/api/jobs/discover?${params.toString()}`);

    if (import.meta.env.DEV) {
      console.info('Job discovery response', {
        jobs: response.jobs.length,
        providersUsed: response.providers_used,
        providersFailed: response.providers_failed,
        profileUsed: response.profile_used,
        resolvedQuery: response.resolved_query ?? response.query,
        resolvedLocation: response.resolved_location ?? response.location,
      });
    }

    return response;
  } catch (error) {
    if (error instanceof ApiError) {
      if (
        error.status === 503 &&
        error.message === 'Job recommendations are not connected yet. You can still analyze a job manually.'
      ) {
        throw new Error('Job recommendations are not connected yet. You can still analyze a job manually.');
      }

      if (error.status === 503) {
        throw new Error('We could not load job recommendations right now.');
      }
    }

    throw normalizeJobError(error);
  }
}

export async function getJobPosting(jobPostingId: string): Promise<JobPosting> {
  try {
    return await apiRequest<JobPosting>(`/api/jobs/${jobPostingId}`);
  } catch (error) {
    throw normalizeJobError(error);
  }
}

export async function generateJobMatch(jobPostingId: string, analysisId: string): Promise<JobMatch> {
  try {
    return await apiRequest<JobMatch>(`/api/jobs/${jobPostingId}/match/${analysisId}`, {
      method: 'POST',
    });
  } catch (error) {
    throw normalizeJobError(error);
  }
}

export async function listCompletedAnalyses(): Promise<CompletedAnalysisOption[]> {
  const { data: sessionData, error: sessionError } = await supabase.auth.getSession();

  if (sessionError || !sessionData.session?.user.id) {
    throw new Error('Your session has expired. Please sign in again.');
  }

  const { data, error } = await supabase
    .from('cv_analyses')
    .select('id,target_role,created_at')
    .eq('user_id', sessionData.session.user.id)
    .eq('status', 'completed')
    .order('created_at', { ascending: false })
    .returns<CompletedAnalysisOption[]>();

  if (error) {
    throw new Error('Unable to load completed CV analyses.');
  }

  return data ?? [];
}
