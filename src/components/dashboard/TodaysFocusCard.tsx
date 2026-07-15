import { ArrowRight, CalendarCheck, Clock } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { DashboardOverview } from '../../types/dashboard';
import { getCurrentDashboardStep, isDashboardRoadmapCompleted } from '../../utils/dashboardOverview';
import Button from '../ui/Button';
import Card from '../ui/Card';

type TodaysFocusCardProps = {
  overview: DashboardOverview;
};

export default function TodaysFocusCard({ overview }: TodaysFocusCardProps) {
  const currentStep = getCurrentDashboardStep(overview.roadmapSteps);
  const isCompletedRoadmap = isDashboardRoadmapCompleted(overview);

  if (!overview.activeRoadmap) {
    return (
      <Card className="p-6">
        <CalendarCheck className="size-7 text-brand-700" />
        <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">No active roadmap yet</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Analyze a CV and generate your career roadmap.
        </p>
      </Card>
    );
  }

  if (!currentStep || isCompletedRoadmap) {
    return (
      <Card className="p-6">
        <CalendarCheck className="size-7 text-emerald-600" />
        <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">Roadmap completed</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">You completed all planned weeks.</p>
      </Card>
    );
  }

  const stepTasks = overview.roadmapTasks.filter((task) => task.stepId === currentStep.id);
  const completedTasks = stepTasks.filter((task) => task.status === 'completed').length;

  return (
    <Card className="p-6">
      <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
        <div>
          <p className="text-sm font-bold text-brand-700">Today’s Focus</p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">
            Week {currentStep.weekNumber}
          </h2>
          <p className="mt-1 text-lg font-semibold text-slate-800">{currentStep.title}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="rounded-md bg-brand-50 px-3 py-1 text-xs font-bold text-brand-700 ring-1 ring-brand-100">
              {currentStep.status.replace('_', ' ')}
            </span>
            <span className="inline-flex items-center gap-1 rounded-md bg-slate-50 px-3 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-100">
              <Clock className="size-3.5" />
              {currentStep.estimatedHours}h weekly effort
            </span>
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-600">
            {completedTasks} of {stepTasks.length} tasks completed
          </p>
        </div>

        <Link to={`/roadmaps/${overview.activeRoadmap.id}/weeks/${currentStep.id}`}>
          <Button className="w-full sm:w-auto" aria-label="Continue today’s plan">
            Continue Today’s Plan
            <ArrowRight className="size-4" />
          </Button>
        </Link>
      </div>
    </Card>
  );
}
