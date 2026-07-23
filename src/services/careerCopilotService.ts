import { ApiError, apiRequest } from './apiService';
import type { CareerCopilotRequest, CareerCopilotResponse } from '../types/careerCopilot';

function normalizeCareerCopilotError(error: unknown): Error {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return new Error('Your session has expired. Please sign in again.');
    }

    if (error.status === 404) {
      return new Error('CV analysis could not be found.');
    }

    if (error.status === 503) {
      return new Error('Career Copilot is temporarily unavailable. Please try again shortly.');
    }
  }

  if (error instanceof Error) {
    return error;
  }

  return new Error('Something went wrong.');
}

export async function sendCareerCopilotMessage(
  input: CareerCopilotRequest,
): Promise<CareerCopilotResponse> {
  try {
    return await apiRequest<CareerCopilotResponse>('/api/career-copilot/chat', {
      method: 'POST',
      body: JSON.stringify(input),
      timeoutMs: 60000,
    });
  } catch (error) {
    throw normalizeCareerCopilotError(error);
  }
}
