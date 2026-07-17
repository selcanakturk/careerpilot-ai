import type { DashboardOverview, DashboardRoadmapStep } from '../types/dashboard';

export function getCurrentDashboardStep(steps: DashboardRoadmapStep[]) {
  return (
    steps.find((step) => step.status === 'in_progress') ??
    steps.find((step) => step.status === 'not_started') ??
    steps[steps.length - 1] ??
    null
  );
}

export function isDashboardRoadmapCompleted(overview: DashboardOverview) {
  return overview.roadmapSteps.length > 0 && overview.roadmapSteps.every((step) => step.status === 'completed');
}

export function getCurrentDayName() {
  const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  return dayNames[new Date().getDay()];
}

export function formatMinutes(minutes: number) {
  const safeMinutes = Math.max(0, minutes);

  if (safeMinutes < 60) {
    return `${safeMinutes} min`;
  }

  const hours = Math.floor(safeMinutes / 60);
  const remainingMinutes = safeMinutes % 60;

  if (remainingMinutes === 0) {
    return `${hours}h`;
  }

  return `${hours}h ${remainingMinutes}m`;
}

export function getDashboardTaskStats(overview: DashboardOverview) {
  const totalTasks = overview.roadmapTasks.length;
  const completedTasks = overview.roadmapTasks.filter((task) => task.status === 'completed').length;
  const remainingTasks = Math.max(0, totalTasks - completedTasks);
  const progressPercent = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  return {
    completedTasks,
    progressPercent,
    remainingTasks,
    totalTasks,
  };
}

export function getStepTaskStats(overview: DashboardOverview, stepId: string) {
  const stepTasks = overview.roadmapTasks.filter((task) => task.stepId === stepId);
  const completedTasks = stepTasks.filter((task) => task.status === 'completed').length;
  const remainingTasks = Math.max(0, stepTasks.length - completedTasks);
  const remainingMinutes = stepTasks
    .filter((task) => task.status !== 'completed')
    .reduce((sum, task) => sum + task.estimatedMinutes, 0);
  const progressPercent = stepTasks.length > 0 ? Math.round((completedTasks / stepTasks.length) * 100) : 0;

  return {
    completedTasks,
    progressPercent,
    remainingMinutes,
    remainingTasks,
    totalTasks: stepTasks.length,
  };
}

export function getNextDashboardMilestoneStep(overview: DashboardOverview) {
  return (
    overview.roadmapSteps.find((step) => step.status === 'in_progress') ??
    overview.roadmapSteps.find((step) => step.status === 'not_started') ??
    null
  );
}
