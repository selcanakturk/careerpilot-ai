export type RoadmapPriority = 'low' | 'medium' | 'high' | 'critical';
export type RoadmapStepStatus = 'not_started' | 'in_progress' | 'completed';
export type RoadmapTaskStatus = 'not_started' | 'completed';

export type RoadmapResource = {
  title: string;
  url: string;
};

export type RoadmapTask = {
  id: string;
  title: string;
  estimated_minutes: number;
  status: RoadmapTaskStatus;
  task_order?: number | null;
};

export type RoadmapDay = {
  day_name: string;
  tasks: RoadmapTask[];
};

export type RoadmapStep = {
  id: string | null;
  week_number: number;
  title: string;
  description: string;
  reason: string;
  estimated_hours: number;
  priority: RoadmapPriority;
  status: RoadmapStepStatus;
  resources: RoadmapResource[];
  mini_project: string;
  days: RoadmapDay[];
  updated_at: string | null;
};

export type CareerRoadmap = {
  summary: string;
  duration_weeks: number;
  estimated_job_readiness_before: number;
  estimated_job_readiness_after: number;
  steps: RoadmapStep[];
};

export type RoadmapGenerateResponse = {
  id: string;
  user_id: string;
  analysis_id: string;
  target_role: string;
  status: string;
  roadmap: CareerRoadmap;
  created_at: string | null;
  updated_at: string | null;
};

export type RoadmapStepProgressResponse = {
  id: string;
  roadmap_id: string;
  week_number: number;
  status: RoadmapStepStatus;
  updated_at: string;
};
