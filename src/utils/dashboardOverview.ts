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
  if (minutes < 60) {
    return `${minutes} min`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  if (remainingMinutes === 0) {
    return `${hours}h`;
  }

  return `${hours}h ${remainingMinutes}m`;
}
