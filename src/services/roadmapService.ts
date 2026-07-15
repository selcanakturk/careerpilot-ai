import { ApiError, apiRequest } from './apiService';
import { supabase } from '../lib/supabase';
import type {
  CareerRoadmap,
  RoadmapGenerateResponse,
  RoadmapPriority,
  RoadmapResource,
  RoadmapStep,
  RoadmapStepProgressResponse,
  RoadmapStepStatus,
} from '../types/roadmap';

type RoadmapRow = {
  id: string;
  user_id: string;
  analysis_id: string;
  target_role: string;
  status: string;
  duration_weeks: number;
  summary: string;
  estimated_job_readiness_before: number;
  estimated_job_readiness_after: number;
  created_at: string | null;
  updated_at: string | null;
};

type RoadmapStepRow = {
  id: string | null;
  week_number: number;
  title: string;
  description: string;
  reason: string;
  estimated_hours: number;
  priority: string;
  status: string | null;
  resources: unknown;
  mini_project: string;
  updated_at: string | null;
};

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

function isRoadmapPriority(value: string): value is RoadmapPriority {
  return ['low', 'medium', 'high', 'critical'].includes(value);
}

function isRoadmapStepStatus(value: string | null): value is RoadmapStepStatus {
  return value === 'not_started' || value === 'in_progress' || value === 'completed';
}

function isRoadmapResource(value: unknown): value is RoadmapResource {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const resource = value as Partial<RoadmapResource>;
  return typeof resource.title === 'string' && typeof resource.url === 'string';
}

function normalizeResources(value: unknown): RoadmapResource[] {
  return Array.isArray(value) ? value.filter(isRoadmapResource) : [];
}

function mapRoadmapStep(row: RoadmapStepRow): RoadmapStep {
  return {
    id: row.id,
    week_number: row.week_number,
    title: row.title,
    description: row.description,
    reason: row.reason,
    estimated_hours: row.estimated_hours,
    priority: isRoadmapPriority(row.priority) ? row.priority : 'medium',
    status: isRoadmapStepStatus(row.status) ? row.status : 'not_started',
    resources: normalizeResources(row.resources),
    mini_project: row.mini_project,
    updated_at: row.updated_at,
  };
}

export async function updateRoadmapStepStatus(
  roadmapId: string,
  stepId: string,
  status: RoadmapStepStatus,
): Promise<RoadmapStepProgressResponse> {
  return apiRequest<RoadmapStepProgressResponse>(`/api/roadmaps/${roadmapId}/steps/${stepId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

function mapRoadmapResponse(row: RoadmapRow, steps: RoadmapStep[]): RoadmapGenerateResponse {
  const roadmap: CareerRoadmap = {
    summary: row.summary,
    duration_weeks: row.duration_weeks,
    estimated_job_readiness_before: row.estimated_job_readiness_before,
    estimated_job_readiness_after: row.estimated_job_readiness_after,
    steps,
  };

  return {
    id: row.id,
    user_id: row.user_id,
    analysis_id: row.analysis_id,
    target_role: row.target_role,
    status: row.status,
    roadmap,
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}

export async function getRoadmap(roadmapId: string): Promise<RoadmapGenerateResponse | null> {
  const safeRoadmapId = roadmapId.trim();

  if (!safeRoadmapId) {
    return null;
  }

  const { data: sessionData, error: sessionError } = await supabase.auth.getSession();

  if (sessionError || !sessionData.session?.user.id) {
    throw new Error('Your session has expired. Please sign in again.');
  }

  const userId = sessionData.session.user.id;
  const { data: roadmapRows, error: roadmapError } = await supabase
    .from('career_roadmaps')
    .select(
      'id,user_id,analysis_id,target_role,status,duration_weeks,summary,estimated_job_readiness_before,estimated_job_readiness_after,created_at,updated_at',
    )
    .eq('id', safeRoadmapId)
    .eq('user_id', userId)
    .limit(1)
    .returns<RoadmapRow[]>();

  if (roadmapError) {
    throw new Error('Unable to load roadmap.');
  }

  const roadmap = roadmapRows?.[0];

  if (!roadmap) {
    return null;
  }

  const { data: stepRows, error: stepsError } = await supabase
    .from('roadmap_steps')
    .select('id,week_number,title,description,reason,estimated_hours,priority,status,resources,mini_project,updated_at')
    .eq('roadmap_id', safeRoadmapId)
    .order('week_number', { ascending: true })
    .returns<RoadmapStepRow[]>();

  if (stepsError) {
    throw new Error('Unable to load roadmap.');
  }

  return mapRoadmapResponse(roadmap, (stepRows ?? []).map(mapRoadmapStep));
}
