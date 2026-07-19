import { ArrowRight, CheckCircle2, Clock, Play } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Card from '../ui/Card';
import Button from '../ui/Button';
import type { RoadmapPriority, RoadmapStep, RoadmapStepStatus } from '../../types/roadmap';

type RoadmapStepCardProps = {
  roadmapId: string;
  step: RoadmapStep;
  isUpdating: boolean;
  onStatusChange: (stepId: string, status: RoadmapStepStatus) => void;
};

const priorityClasses: Record<RoadmapPriority, string> = {
  critical: 'bg-rose-50 text-rose-700 ring-rose-100',
  high: 'bg-amber-50 text-amber-700 ring-amber-100',
  medium: 'bg-brand-50 text-brand-700 ring-brand-100',
  low: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
};

const statusClasses: Record<RoadmapStepStatus, string> = {
  completed: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
  in_progress: 'bg-brand-50 text-brand-700 ring-brand-100',
  not_started: 'bg-slate-50 text-slate-600 ring-slate-100',
};

const statusLabels: Record<RoadmapStepStatus, string> = {
  completed: 'Completed',
  in_progress: 'Current Week',
  not_started: 'Upcoming',
};

export default function RoadmapStepCard({
  roadmapId,
  step,
  isUpdating,
  onStatusChange,
}: RoadmapStepCardProps) {
  const navigate = useNavigate();
  const canUpdate = Boolean(step.id);
  const isCompleted = step.status === 'completed';
  const isInProgress = step.status === 'in_progress';
  const tasks = step.days.flatMap((day) => day.tasks);
  const totalTasks = tasks.length;
  const completedTasks = tasks.filter((task) => task.status === 'completed').length;
  const taskProgressPercentage = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;
  const hasDailyPlan = totalTasks > 0;
  const detailButtonLabel = isInProgress ? 'Continue This Week' : isCompleted ? 'Review Week Plan' : 'Open Week Plan';

  const handleStart = () => {
    if (step.id) {
      onStatusChange(step.id, 'in_progress');
    }
  };

  const handleComplete = () => {
    if (step.id) {
      onStatusChange(step.id, 'completed');
    }
  };

  const handleViewDailyPlan = () => {
    if (step.id) {
      navigate(`/roadmaps/${roadmapId}/weeks/${step.id}`);
    }
  };

  return (
    <Card
      className={`p-5 transition sm:p-6 ${
        isCompleted
          ? 'border-emerald-200 bg-emerald-50/30'
          : isInProgress
            ? 'border-brand-200 bg-brand-50/20'
            : ''
      }`}
    >
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div>
          <p className="text-sm font-bold text-brand-700">Week {step.week_number}</p>
          <h3 className="mt-1 text-xl font-bold tracking-tight text-slate-950">{step.title}</h3>
        </div>
        <div className="flex flex-wrap gap-2 sm:justify-end">
          <span className={`rounded-md px-3 py-1 text-xs font-bold ring-1 ${statusClasses[step.status]}`}>
            {statusLabels[step.status]}
          </span>
          <span className={`rounded-md px-3 py-1 text-xs font-bold ring-1 ${priorityClasses[step.priority]}`}>
            {step.priority}
          </span>
          <span className="inline-flex items-center gap-1 rounded-md bg-slate-50 px-3 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-100">
            <Clock className="size-3.5" />
            {step.estimated_hours}h
          </span>
          {hasDailyPlan && (
            <span className="rounded-md bg-white px-3 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-100">
              {totalTasks} tasks
            </span>
          )}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {step.status === 'not_started' && (
          <Button
            type="button"
            variant="secondary"
            onClick={handleStart}
            disabled={!canUpdate || isUpdating}
            className="w-full sm:w-auto"
          >
            <Play className="size-4" />
            {isUpdating ? 'Starting...' : 'Start week'}
          </Button>
        )}
        {isInProgress && (
          <Button
            type="button"
            onClick={handleComplete}
            disabled={!canUpdate || isUpdating}
            className="w-full sm:w-auto"
          >
            <CheckCircle2 className="size-4" />
            {isUpdating ? 'Completing...' : 'Mark complete'}
          </Button>
        )}
        {isCompleted && (
          <span className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white sm:w-auto">
            <CheckCircle2 className="size-4" />
            Completed
          </span>
        )}
        {hasDailyPlan && (
          <Button
            type="button"
            variant="secondary"
            onClick={handleViewDailyPlan}
            disabled={!canUpdate}
            className="w-full sm:w-auto"
            aria-label={`${detailButtonLabel} for week ${step.week_number}`}
          >
            {detailButtonLabel}
            <ArrowRight className="size-4" />
          </Button>
        )}
      </div>

      {hasDailyPlan && (
        <div className="mt-5 rounded-md bg-white p-4 ring-1 ring-slate-100">
          <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
            <div>
              <p className="text-sm font-bold text-slate-950">
                {completedTasks} / {totalTasks} tasks completed
              </p>
              <p className="mt-1 text-xs font-semibold text-slate-500">{taskProgressPercentage}%</p>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 sm:w-44">
              <div
                className="h-full rounded-full bg-brand-600 transition-all"
                style={{ width: `${taskProgressPercentage}%` }}
              />
            </div>
          </div>
        </div>
      )}

      <div className="mt-5 grid gap-4">
        <section>
          <h4 className="text-sm font-bold text-slate-950">Objective</h4>
          <p className="mt-2 text-sm leading-6 text-slate-600">{step.description}</p>
        </section>
        {step.mini_project && (
          <section>
            <h4 className="text-sm font-bold text-slate-950">Mini Project</h4>
            <p className="mt-2 text-sm leading-6 text-slate-600">{step.mini_project}</p>
          </section>
        )}
        {step.resources.length > 0 && (
          <section>
            <h4 className="text-sm font-bold text-slate-950">Resources</h4>
            <div className="mt-2 flex flex-wrap gap-2">
              {step.resources.map((resource) => (
                <a
                  key={`${resource.title}-${resource.url}`}
                  href={resource.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-md bg-slate-50 px-2.5 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200 transition hover:bg-white hover:text-brand-700"
                >
                  {resource.title}
                </a>
              ))}
            </div>
          </section>
        )}
      </div>
    </Card>
  );
}
