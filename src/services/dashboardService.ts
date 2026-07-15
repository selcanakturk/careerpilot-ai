import { supabase } from '../lib/supabase';
import type {
  DashboardAnalysis,
  DashboardOverview,
  DashboardRoadmap,
  DashboardRoadmapStep,
  DashboardRoadmapTask,
} from '../types/dashboard';
import type { RoadmapStepStatus, RoadmapTaskStatus } from '../types/roadmap';

type AnalysisRow = {
  id: string;
  target_role: string;
  overall_score: number;
  created_at: string;
};

type RoadmapRow = {
  id: string;
  target_role: string;
  duration_weeks: number;
  estimated_job_readiness_before: number;
  estimated_job_readiness_after: number;
  created_at: string;
};

type RoadmapStepRow = {
  id: string;
  week_number: number;
  title: string;
  estimated_hours: number;
  status: string | null;
};

type RoadmapTaskRow = {
  id: string;
  step_id: string;
  day_name: string;
  title: string;
  estimated_minutes: number;
  status: string | null;
  task_order: number;
};

function isRoadmapStepStatus(value: string | null): value is RoadmapStepStatus {
  return value === 'not_started' || value === 'in_progress' || value === 'completed';
}

function isRoadmapTaskStatus(value: string | null): value is RoadmapTaskStatus {
  return value === 'not_started' || value === 'completed';
}

function mapAnalysis(row: AnalysisRow): DashboardAnalysis {
  return {
    id: row.id,
    targetRole: row.target_role,
    overallScore: row.overall_score,
    createdAt: row.created_at,
  };
}

function mapRoadmap(row: RoadmapRow): DashboardRoadmap {
  return {
    id: row.id,
    targetRole: row.target_role,
    durationWeeks: row.duration_weeks,
    readinessBefore: row.estimated_job_readiness_before,
    readinessAfter: row.estimated_job_readiness_after,
    createdAt: row.created_at,
  };
}

function mapStep(row: RoadmapStepRow): DashboardRoadmapStep {
  return {
    id: row.id,
    weekNumber: row.week_number,
    title: row.title,
    estimatedHours: row.estimated_hours,
    status: isRoadmapStepStatus(row.status) ? row.status : 'not_started',
  };
}

function mapTask(row: RoadmapTaskRow): DashboardRoadmapTask {
  return {
    id: row.id,
    stepId: row.step_id,
    dayName: row.day_name,
    title: row.title,
    estimatedMinutes: row.estimated_minutes,
    status: isRoadmapTaskStatus(row.status) ? row.status : 'not_started',
    taskOrder: row.task_order,
  };
}

export async function getDashboardOverview(): Promise<DashboardOverview> {
  const { data: sessionData, error: sessionError } = await supabase.auth.getSession();

  if (sessionError || !sessionData.session?.user.id) {
    throw new Error('Your session has expired. Please sign in again.');
  }

  const userId = sessionData.session.user.id;

  const [analysisResult, roadmapResult] = await Promise.all([
    supabase
      .from('cv_analyses')
      .select('id,target_role,overall_score,created_at')
      .eq('user_id', userId)
      .eq('status', 'completed')
      .order('created_at', { ascending: false })
      .limit(1)
      .returns<AnalysisRow[]>(),
    supabase
      .from('career_roadmaps')
      .select('id,target_role,duration_weeks,estimated_job_readiness_before,estimated_job_readiness_after,created_at')
      .eq('user_id', userId)
      .eq('status', 'active')
      .order('created_at', { ascending: false })
      .limit(1)
      .returns<RoadmapRow[]>(),
  ]);

  if (analysisResult.error || roadmapResult.error) {
    throw new Error('Unable to load your dashboard.');
  }

  const latestAnalysis = analysisResult.data?.[0] ? mapAnalysis(analysisResult.data[0]) : null;
  const activeRoadmap = roadmapResult.data?.[0] ? mapRoadmap(roadmapResult.data[0]) : null;

  if (!activeRoadmap) {
    return {
      latestAnalysis,
      activeRoadmap: null,
      roadmapSteps: [],
      roadmapTasks: [],
    };
  }

  const [stepsResult, tasksResult] = await Promise.all([
    supabase
      .from('roadmap_steps')
      .select('id,week_number,title,estimated_hours,status')
      .eq('roadmap_id', activeRoadmap.id)
      .order('week_number', { ascending: true })
      .returns<RoadmapStepRow[]>(),
    supabase
      .from('roadmap_tasks')
      .select('id,step_id,day_name,title,estimated_minutes,status,task_order')
      .eq('roadmap_id', activeRoadmap.id)
      .returns<RoadmapTaskRow[]>(),
  ]);

  if (stepsResult.error || tasksResult.error) {
    throw new Error('Unable to load your dashboard.');
  }

  return {
    latestAnalysis,
    activeRoadmap,
    roadmapSteps: (stepsResult.data ?? []).map(mapStep),
    roadmapTasks: (tasksResult.data ?? []).map(mapTask),
  };
}
