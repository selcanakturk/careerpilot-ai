import { CheckCircle2, Gauge, ListChecks, TrendingUp } from 'lucide-react';
import type { DashboardOverview } from '../../types/dashboard';
import ProgressMetricCard from './ProgressMetricCard';

type ProgressOverviewProps = {
  overview: DashboardOverview;
};

function getRoadmapProgress(overview: DashboardOverview) {
  const totalSteps = overview.roadmapSteps.length;
  const completedSteps = overview.roadmapSteps.filter((step) => step.status === 'completed').length;
  const percentage = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;

  return { completedSteps, percentage, totalSteps };
}

export default function ProgressOverview({ overview }: ProgressOverviewProps) {
  const progress = getRoadmapProgress(overview);
  const completedTasks = overview.roadmapTasks.filter((task) => task.status === 'completed').length;

  return (
    <section>
      <h2 className="mb-4 text-xl font-bold tracking-tight text-slate-950">Progress Overview</h2>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <ProgressMetricCard
          icon={Gauge}
          label="CV Score"
          value={overview.latestAnalysis ? `${overview.latestAnalysis.overallScore} / 100` : '—'}
        />
        <ProgressMetricCard
          icon={TrendingUp}
          label="Job Readiness"
          value={
            overview.activeRoadmap
              ? `${overview.activeRoadmap.readinessBefore} → ${overview.activeRoadmap.readinessAfter}`
              : '—'
          }
        />
        <ProgressMetricCard
          helper={`${progress.completedSteps} / ${progress.totalSteps} weeks completed`}
          icon={ListChecks}
          label="Roadmap Progress"
          value={overview.activeRoadmap ? `${progress.percentage}%` : '—'}
        />
        <ProgressMetricCard
          icon={CheckCircle2}
          label="Completed Tasks"
          value={completedTasks.toString()}
        />
      </div>
    </section>
  );
}
