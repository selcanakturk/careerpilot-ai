import { CalendarDays, CheckCircle2, Gauge, ListChecks, TimerReset, TrendingUp } from 'lucide-react';
import type { DashboardOverview } from '../../types/dashboard';
import { getCurrentDashboardStep, getDashboardTaskStats } from '../../utils/dashboardOverview';
import ProgressMetricCard from './ProgressMetricCard';

type ProgressOverviewProps = {
  overview: DashboardOverview;
};

export default function ProgressOverview({ overview }: ProgressOverviewProps) {
  const taskStats = getDashboardTaskStats(overview);
  const currentStep = getCurrentDashboardStep(overview.roadmapSteps);
  const hasRoadmap = Boolean(overview.activeRoadmap);

  return (
    <section>
      <h2 className="mb-4 text-xl font-bold tracking-tight text-slate-950">Progress Overview</h2>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <ProgressMetricCard
          icon={Gauge}
          label="CV Score"
          value={overview.latestAnalysis ? `${overview.latestAnalysis.overallScore} / 100` : '—'}
        />
        <ProgressMetricCard
          icon={TrendingUp}
          label="Job Readiness"
          value={
            hasRoadmap && overview.activeRoadmap
              ? `${overview.activeRoadmap.readinessBefore} → ${overview.activeRoadmap.readinessAfter}`
              : '—'
          }
          helper={hasRoadmap ? 'Before → after roadmap estimate' : 'Generate a roadmap to track readiness'}
        />
        <ProgressMetricCard
          helper={hasRoadmap ? `${currentStep?.title ?? 'No active week'}` : 'No active roadmap yet'}
          icon={CalendarDays}
          label="Current Week"
          value={hasRoadmap && currentStep ? `Week ${currentStep.weekNumber}` : '—'}
        />
        <ProgressMetricCard
          helper={`${taskStats.completedTasks} / ${taskStats.totalTasks} tasks completed`}
          icon={ListChecks}
          label="Roadmap Progress"
          value={hasRoadmap ? `${taskStats.progressPercent}%` : '—'}
        />
        <ProgressMetricCard
          icon={CheckCircle2}
          label="Completed Tasks"
          value={hasRoadmap ? taskStats.completedTasks.toString() : '—'}
        />
        <ProgressMetricCard
          icon={TimerReset}
          label="Remaining Tasks"
          value={hasRoadmap ? taskStats.remainingTasks.toString() : '—'}
        />
      </div>
    </section>
  );
}
