import type { RoadmapStepStatus, RoadmapTaskStatus } from './roadmap';

export type DashboardAnalysis = {
  id: string;
  targetRole: string;
  overallScore: number;
  createdAt: string;
};

export type DashboardRoadmap = {
  id: string;
  targetRole: string;
  durationWeeks: number;
  readinessBefore: number;
  readinessAfter: number;
  createdAt: string;
};

export type DashboardRoadmapStep = {
  id: string;
  weekNumber: number;
  title: string;
  estimatedHours: number;
  status: RoadmapStepStatus;
};

export type DashboardRoadmapTask = {
  id: string;
  stepId: string;
  dayName: string;
  title: string;
  estimatedMinutes: number;
  status: RoadmapTaskStatus;
  taskOrder: number;
};

export type DashboardOverview = {
  latestAnalysis: DashboardAnalysis | null;
  activeRoadmap: DashboardRoadmap | null;
  roadmapSteps: DashboardRoadmapStep[];
  roadmapTasks: DashboardRoadmapTask[];
};
