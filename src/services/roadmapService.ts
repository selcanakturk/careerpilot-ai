import { ApiError, apiRequest } from './apiService';
import { supabase } from '../lib/supabase';
import type {
  CareerRoadmap,
  RoadmapGenerateResponse,
  RoadmapDay,
  RoadmapPhase,
  RoadmapPhaseStatus,
  RoadmapPriority,
  RoadmapResource,
  RoadmapStep,
  RoadmapStepProgressResponse,
  RoadmapStepStatus,
  RoadmapTask,
  RoadmapTaskProgressResponse,
  RoadmapTaskStatus,
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

type RoadmapTaskRow = {
  id: string;
  step_id: string;
  day_name: string;
  task_order: number;
  title: string;
  estimated_minutes: number;
  status: string | null;
};

const dayOrder = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

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

function isRoadmapTaskStatus(value: string | null): value is RoadmapTaskStatus {
  return value === 'not_started' || value === 'completed';
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

function mapRoadmapStep(row: RoadmapStepRow, days: RoadmapDay[] = []): RoadmapStep {
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
    days,
    updated_at: row.updated_at,
  };
}

function mapRoadmapTask(row: RoadmapTaskRow): RoadmapTask {
  return {
    id: row.id,
    title: row.title,
    estimated_minutes: row.estimated_minutes,
    status: isRoadmapTaskStatus(row.status) ? row.status : 'not_started',
    task_order: row.task_order,
  };
}

function groupTasksByStep(tasks: RoadmapTaskRow[]): Record<string, RoadmapDay[]> {
  const groupedByStep: Record<string, Record<string, RoadmapTask[]>> = {};

  tasks.forEach((task) => {
    groupedByStep[task.step_id] ??= {};
    groupedByStep[task.step_id][task.day_name] ??= [];
    groupedByStep[task.step_id][task.day_name].push(mapRoadmapTask(task));
  });

  return Object.fromEntries(
    Object.entries(groupedByStep).map(([stepId, days]) => [
      stepId,
      dayOrder
        .filter((dayName) => (days[dayName]?.length ?? 0) > 0)
        .map((dayName) => ({
          day_name: dayName,
          tasks: [...days[dayName]].sort((firstTask, secondTask) => {
            const firstOrder = firstTask.task_order ?? 0;
            const secondOrder = secondTask.task_order ?? 0;
            return firstOrder - secondOrder;
          }),
        })),
    ]),
  );
}

function chunkStepsIntoPhases(steps: RoadmapStep[]): RoadmapStep[][] {
  if (steps.length === 0) {
    return [[], [], []];
  }

  const baseSize = Math.floor(steps.length / 3);
  const remainder = steps.length % 3;
  const groups: RoadmapStep[][] = [];
  let cursor = 0;

  for (let index = 0; index < 3; index += 1) {
    const groupSize = baseSize + (index < remainder ? 1 : 0);
    groups.push(steps.slice(cursor, cursor + groupSize));
    cursor += groupSize;
  }

  return groups;
}

function getPhaseStatus(group: RoadmapStep[], previousGroupsCompleted: boolean): RoadmapPhaseStatus {
  if (group.length === 0) {
    return 'locked';
  }

  if (group.every((step) => step.status === 'completed')) {
    return 'completed';
  }

  if (previousGroupsCompleted || group.some((step) => step.status === 'in_progress')) {
    return 'current';
  }

  return 'locked';
}

function appendUniqueSkill(skills: string[], value: string) {
  const normalizedValue = value.replace(/\s+/g, ' ').trim();

  if (!normalizedValue) {
    return;
  }

  if (skills.some((skill) => skill.toLowerCase() === normalizedValue.toLowerCase())) {
    return;
  }

  skills.push(normalizedValue);
}

function getPhaseSkills(group: RoadmapStep[]): string[] {
  const skills: string[] = [];

  group.forEach((step) => {
    appendUniqueSkill(skills, step.title);

    step.resources.forEach((resource) => {
      appendUniqueSkill(skills, resource.title);
    });
  });

  return skills.slice(0, 6);
}

function calculateOverallProgress(steps: RoadmapStep[]): number {
  const tasks = steps.flatMap((step) => step.days.flatMap((day) => day.tasks));

  if (tasks.length > 0) {
    const completedTasks = tasks.filter((task) => task.status === 'completed').length;
    return Math.round((completedTasks / tasks.length) * 100);
  }

  if (steps.length === 0) {
    return 0;
  }

  const completedSteps = steps.filter((step) => step.status === 'completed').length;
  return Math.round((completedSteps / steps.length) * 100);
}

function getEstimatedMonths(durationWeeks: number): string {
  const minimumMonths = Math.max(1, Math.round(durationWeeks / 4));
  const maximumMonths = Math.max(minimumMonths, Math.round(durationWeeks / 3));

  return minimumMonths === maximumMonths ? `${minimumMonths}` : `${minimumMonths}-${maximumMonths}`;
}

function buildRoadmapPhases(steps: RoadmapStep[]): RoadmapPhase[] {
  let previousGroupsCompleted = true;

  return chunkStepsIntoPhases(steps).map((group, index) => {
    const status = getPhaseStatus(group, previousGroupsCompleted);
    previousGroupsCompleted = previousGroupsCompleted && status === 'completed';

    return {
      title: `Phase ${index + 1}`,
      status,
      skills: getPhaseSkills(group),
    };
  });
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

export async function updateRoadmapTaskStatus(
  roadmapId: string,
  taskId: string,
  status: RoadmapTaskStatus,
): Promise<RoadmapTaskProgressResponse> {
  return apiRequest<RoadmapTaskProgressResponse>(`/api/roadmaps/${roadmapId}/tasks/${taskId}`, {
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
    goal: row.target_role,
    estimated_months: getEstimatedMonths(row.duration_weeks),
    overall_progress: calculateOverallProgress(steps),
    phases: buildRoadmapPhases(steps),
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

  const { data: taskRows, error: tasksError } = await supabase
    .from('roadmap_tasks')
    .select('id,step_id,day_name,task_order,title,estimated_minutes,status')
    .eq('roadmap_id', safeRoadmapId)
    .returns<RoadmapTaskRow[]>();

  if (tasksError) {
    throw new Error('Unable to load roadmap.');
  }

  const daysByStepId = groupTasksByStep(taskRows ?? []);

  return mapRoadmapResponse(
    roadmap,
    (stepRows ?? []).map((step) => mapRoadmapStep(step, step.id ? (daysByStepId[step.id] ?? []) : [])),
  );
}
