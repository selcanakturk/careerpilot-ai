import { CheckCircle2, Clock, Hammer, Play } from 'lucide-react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import type { RoadmapPriority, RoadmapStep, RoadmapStepStatus } from '../../types/roadmap';
import ResourceList from './ResourceList';

type RoadmapStepCardProps = {
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
  in_progress: 'In progress',
  not_started: 'Not started',
};

export default function RoadmapStepCard({
  step,
  isUpdating,
  onStatusChange,
}: RoadmapStepCardProps) {
  const canUpdate = Boolean(step.id);
  const isCompleted = step.status === 'completed';
  const isInProgress = step.status === 'in_progress';

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
      </div>

      <div className="mt-5 grid gap-4">
        <section>
          <h4 className="text-sm font-bold text-slate-950">Description</h4>
          <p className="mt-2 text-sm leading-6 text-slate-600">{step.description}</p>
        </section>
        <section>
          <h4 className="text-sm font-bold text-slate-950">Reason</h4>
          <p className="mt-2 text-sm leading-6 text-slate-600">{step.reason}</p>
        </section>
        <section className="rounded-md bg-slate-50 p-4">
          <h4 className="inline-flex items-center gap-2 text-sm font-bold text-slate-950">
            <Hammer className="size-4 text-brand-700" />
            Mini Project
          </h4>
          <p className="mt-2 text-sm leading-6 text-slate-600">{step.mini_project}</p>
        </section>
        <section>
          <h4 className="mb-3 text-sm font-bold text-slate-950">Resources</h4>
          <ResourceList resources={step.resources} />
        </section>
      </div>
    </Card>
  );
}
