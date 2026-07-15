import { ApiError, apiRequest } from './apiService';
import type { RoadmapGenerateResponse } from '../types/roadmap';

function createRoadmapError(error: unknown): Error {
  if (error instanceof ApiError) {
    if (error.status === 503) {
      return new Error('The AI roadmap service is currently busy. Please try again in a moment.');
    }

    if (error.status === 500) {
      return new Error('Unable to generate roadmap.');
    }
  }

  if (error instanceof Error) {
    return error;
  }

  return new Error('Unable to generate roadmap.');
}

export async function generateRoadmap(analysisId: string): Promise<RoadmapGenerateResponse> {
  const safeAnalysisId = analysisId.trim();

  if (!safeAnalysisId) {
    throw new Error('A valid analysis id is required to generate a roadmap.');
  }

  try {
    return await apiRequest<RoadmapGenerateResponse>(`/api/roadmaps/generate/${safeAnalysisId}`, {
      method: 'POST',
    });
  } catch (error) {
    throw createRoadmapError(error);
  }
}
