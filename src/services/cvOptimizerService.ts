import { ApiError, apiRequest } from './apiService';
import type { CVOptimizeRequest, CVOptimizeResponse } from '../types/cvOptimizer';

function normalizeOptimizerError(error: unknown): Error {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return new Error('Job or CV analysis could not be found.');
    }

    if (error.status === 502) {
      return new Error('AI service is temporarily unavailable.');
    }

    if (error.status === 500) {
      return new Error('Something went wrong.');
    }
  }

  if (error instanceof Error) {
    return error;
  }

  return new Error('Something went wrong.');
}

export async function optimizeCVForJob(input: CVOptimizeRequest): Promise<CVOptimizeResponse> {
  try {
    return await apiRequest<CVOptimizeResponse>('/api/cv/optimize', {
      method: 'POST',
      body: JSON.stringify(input),
    });
  } catch (error) {
    throw normalizeOptimizerError(error);
  }
}
