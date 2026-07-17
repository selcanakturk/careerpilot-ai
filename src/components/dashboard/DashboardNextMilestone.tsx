import { Flag, TimerReset } from 'lucide-react';
import type { DashboardOverview } from '../../types/dashboard';
import {
  formatMinutes,
  getNextDashboardMilestoneStep,
  getStepTaskStats,
  isDashboardRoadmapCompleted,
} from '../../utils/dashboardOverview';
import Card from '../ui/Card';

type DashboardNextMilestoneProps = {
  overview: DashboardOverview;
};

export default function DashboardNextMilestone({ overview }: DashboardNextMilestoneProps) {
  if (!overview.activeRoadmap) {
    return null;
  }

  if (isDashboardRoadmapCompleted(overview)) {
    return (
      <Card className="p-6">
        <Flag className="size-7 text-emerald-600" />
        <p className="mt-4 text-sm font-bold text-brand-700">Next Milestone</p>
        <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">Roadmap Completed</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          You&apos;ve completed your AI Career Roadmap.
        </p>
      </Card>
    );
  }

  const milestoneStep = getNextDashboardMilestoneStep(overview);

  if (!milestoneStep) {
    return null;
  }

  const stepStats = getStepTaskStats(overview, milestoneStep.id);

  return (
    <Card className="p-6">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
        <div>
          <p className="text-sm font-bold text-brand-700">Next Milestone</p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">
            Finish Week {milestoneStep.weekNumber}
          </h2>
          <p className="mt-1 text-sm font-semibold text-slate-700">{milestoneStep.title}</p>
          <div className="mt-4 grid gap-3 text-sm text-slate-600 sm:grid-cols-2">
            <div className="rounded-md bg-slate-50 p-3">
              <p className="font-semibold text-slate-500">Tasks remaining</p>
              <p className="mt-1 font-bold text-slate-950">{stepStats.remainingTasks}</p>
            </div>
            <div className="rounded-md bg-slate-50 p-3">
              <p className="font-semibold text-slate-500">Estimated remaining effort</p>
              <p className="mt-1 font-bold text-slate-950">
                About {formatMinutes(stepStats.remainingMinutes)} remaining
              </p>
            </div>
          </div>
        </div>
        <span className="flex size-12 shrink-0 items-center justify-center rounded-md bg-brand-50 text-brand-700">
          <TimerReset className="size-6" />
        </span>
      </div>
    </Card>
  );
}
