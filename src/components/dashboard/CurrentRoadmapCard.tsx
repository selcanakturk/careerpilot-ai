import { ArrowRight, Map } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { DashboardOverview } from '../../types/dashboard';
import Button from '../ui/Button';
import Card from '../ui/Card';
import DashboardEmptyState from './DashboardEmptyState';

type CurrentRoadmapCardProps = {
  overview: DashboardOverview;
};

function getCurrentWeek(overview: DashboardOverview) {
  return (
    overview.roadmapSteps.find((step) => step.status === 'in_progress') ??
    overview.roadmapSteps.find((step) => step.status === 'not_started') ??
    overview.roadmapSteps[overview.roadmapSteps.length - 1] ??
    null
  );
}

export default function CurrentRoadmapCard({ overview }: CurrentRoadmapCardProps) {
  if (!overview.activeRoadmap) {
    return <DashboardEmptyState analysisId={overview.latestAnalysis?.id} />;
  }

  const totalSteps = overview.roadmapSteps.length;
  const completedSteps = overview.roadmapSteps.filter((step) => step.status === 'completed').length;
  const progressPercent = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;
  const currentWeek = getCurrentWeek(overview);

  return (
    <Card className="p-6">
      <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
        <div>
          <p className="text-sm font-bold text-brand-700">Current Roadmap</p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">
            {overview.activeRoadmap.targetRole}
          </h2>
          <div className="mt-4 grid gap-3 text-sm text-slate-600 sm:grid-cols-2">
            <div className="rounded-md bg-slate-50 p-3">
              <p className="font-semibold text-slate-500">Duration</p>
              <p className="mt-1 font-bold text-slate-950">{overview.activeRoadmap.durationWeeks} weeks</p>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <p className="font-semibold text-slate-500">Current week</p>
              <p className="mt-1 font-bold text-slate-950">
                {currentWeek ? `Week ${currentWeek.weekNumber} of ${totalSteps}` : '—'}
              </p>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <p className="font-semibold text-slate-500">Completed weeks</p>
              <p className="mt-1 font-bold text-slate-950">
                {completedSteps} / {totalSteps}
              </p>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <p className="font-semibold text-slate-500">Job readiness</p>
              <p className="mt-1 font-bold text-slate-950">
                {overview.activeRoadmap.readinessBefore} → {overview.activeRoadmap.readinessAfter}
              </p>
            </div>
          </div>
        </div>
        <span className="flex size-12 items-center justify-center rounded-md bg-brand-50 text-brand-700">
          <Map className="size-6" />
        </span>
      </div>

      <div className="mt-6">
        <div className="flex items-center justify-between text-sm font-semibold text-slate-600">
          <span>{progressPercent}% complete</span>
          <span>{completedSteps} weeks done</span>
        </div>
        <div
          className="mt-3 h-3 overflow-hidden rounded-full bg-slate-100"
          role="progressbar"
          aria-label={`Roadmap progress is ${progressPercent} percent`}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progressPercent}
        >
          <div className="h-full rounded-full bg-brand-600" style={{ width: `${progressPercent}%` }} />
        </div>
      </div>

      <Link to={`/roadmaps/${overview.activeRoadmap.id}`} className="mt-6 inline-flex">
        <Button aria-label="Open current roadmap">
          Open Roadmap
          <ArrowRight className="size-4" />
        </Button>
      </Link>
    </Card>
  );
}
