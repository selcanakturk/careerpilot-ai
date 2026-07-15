import { ArrowLeft, Clock, Map, Target } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import DailyPlan from '../components/roadmap/DailyPlan';
import ResourceList from '../components/roadmap/ResourceList';
import { getRoadmap } from '../services/roadmapService';
import type { RoadmapGenerateResponse, RoadmapPriority, RoadmapStep, RoadmapStepStatus } from '../types/roadmap';

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

function getTaskProgress(step: RoadmapStep) {
  const tasks = step.days.flatMap((day) => day.tasks);
  const totalTasks = tasks.length;
  const completedTasks = tasks.filter((task) => task.status === 'completed').length;
  const percentage = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  return { completedTasks, percentage, totalTasks };
}

export default function RoadmapWeekPage() {
  const { roadmapId, stepId } = useParams();
  const [roadmap, setRoadmap] = useState<RoadmapGenerateResponse | null>(null);
  const [step, setStep] = useState<RoadmapStep | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;

    const loadWeek = async () => {
      if (!roadmapId || !stepId) {
        setError('Week not found.');
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError('');

      try {
        const record = await getRoadmap(roadmapId);

        if (!isMounted) {
          return;
        }

        if (!record) {
          setRoadmap(null);
          setStep(null);
          setError('Roadmap not found.');
          return;
        }

        const matchedStep = record.roadmap.steps.find((roadmapStep) => roadmapStep.id === stepId) ?? null;

        setRoadmap(record);
        setStep(matchedStep);
        setError(matchedStep ? '' : 'Week not found.');
      } catch {
        if (isMounted) {
          setError('Unable to load weekly plan.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void loadWeek();

    return () => {
      isMounted = false;
    };
  }, [roadmapId, stepId]);

  if (isLoading) {
    return (
      <Card className="p-8 text-center">
        <div className="mx-auto size-10 animate-pulse rounded-full bg-brand-100" />
        <h1 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">Loading weekly plan</h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
          Loading your daily planner securely.
        </p>
      </Card>
    );
  }

  if (error || !roadmap || !step) {
    return (
      <Card className="p-8 text-center">
        <Map className="mx-auto size-10 text-brand-700" />
        <h1 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">
          {error || 'Week not found.'}
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
          {error === 'Roadmap not found.'
            ? 'The roadmap could not be found or you do not have access to it.'
            : error === 'Unable to load weekly plan.'
              ? 'Please try again in a moment.'
              : 'The selected week could not be found in this roadmap.'}
        </p>
        {roadmapId && (
          <Link to={`/roadmaps/${roadmapId}`} className="mt-6 inline-flex">
            <Button variant="secondary">
              <ArrowLeft className="size-4" />
              Back to roadmap
            </Button>
          </Link>
        )}
      </Card>
    );
  }

  const progress = getTaskProgress(step);

  return (
    <div className="space-y-6">
      <Link to={`/roadmaps/${roadmap.id}`} className="inline-flex">
        <Button variant="secondary" aria-label="Back to roadmap">
          <ArrowLeft className="size-4" />
          Back to roadmap
        </Button>
      </Link>

      <Card className="p-6 sm:p-7">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
          <div>
            <p className="text-sm font-bold text-brand-700">Week {step.week_number}</p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">{step.title}</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">{step.description}</p>
          </div>
          <div className="flex flex-wrap gap-2 lg:justify-end">
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

        <div className="mt-6 rounded-md bg-slate-50 p-4">
          <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
            <div>
              <p className="text-sm font-bold text-slate-950">Weekly task progress</p>
              <p className="mt-1 text-sm text-slate-600">
                {progress.completedTasks} / {progress.totalTasks} tasks completed
              </p>
            </div>
            <p className="text-2xl font-bold text-slate-950">{progress.percentage}%</p>
          </div>
          <div
            className="mt-4 h-3 overflow-hidden rounded-full bg-white"
            aria-label={`Weekly task progress is ${progress.percentage} percent`}
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress.percentage}
          >
            <div
              className="h-full rounded-full bg-brand-600 transition-all"
              style={{ width: `${progress.percentage}%` }}
            />
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1fr_0.9fr]">
        <Card className="p-5 sm:p-6">
          <h2 className="flex items-center gap-2 text-lg font-bold text-slate-950">
            <Target className="size-5 text-brand-700" />
            Week Context
          </h2>
          <div className="mt-4 grid gap-4">
            <section>
              <h3 className="text-sm font-bold text-slate-950">Full Description</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{step.description}</p>
            </section>
            <section>
              <h3 className="text-sm font-bold text-slate-950">Reason</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{step.reason}</p>
            </section>
            <section className="rounded-md bg-slate-50 p-4">
              <h3 className="text-sm font-bold text-slate-950">Mini Project</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{step.mini_project}</p>
            </section>
          </div>
        </Card>

        <Card className="p-5 sm:p-6">
          <h2 className="text-lg font-bold text-slate-950">Resources</h2>
          <div className="mt-4">
            <ResourceList resources={step.resources} />
          </div>
        </Card>
      </div>

      <DailyPlan days={step.days} />
    </div>
  );
}
