import { CalendarDays, Target, TrendingUp } from 'lucide-react';
import Card from '../ui/Card';
import type { RoadmapGenerateResponse } from '../../types/roadmap';
import JobReadinessBar from './JobReadinessBar';

type RoadmapHeroProps = {
  roadmap: RoadmapGenerateResponse;
};

export default function RoadmapHero({ roadmap }: RoadmapHeroProps) {
  const estimatedMonths = roadmap.estimated_months || `${Math.max(1, Math.round(roadmap.roadmap.duration_weeks / 4))}`;
  const overallProgress = Math.max(0, Math.min(100, roadmap.overall_progress ?? 0));

  return (
    <Card className="overflow-hidden p-6 sm:p-7">
      <div className="grid gap-6 lg:grid-cols-[1fr_0.9fr] lg:items-end">
        <div>
          <p className="text-sm font-semibold text-brand-700">AI Career Roadmap</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">
            Career Roadmap
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
            A weekly plan for improving your readiness for the target role.
          </p>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
            Follow the weekly plan to steadily improve your readiness for your target role.
          </p>
          <div className="mt-6 max-w-xl">
            <div className="flex items-center justify-between gap-4">
              <p className="text-sm font-bold text-slate-950">Overall progress</p>
              <p className="text-sm font-bold text-brand-700">{overallProgress}%</p>
            </div>
            <div
              className="mt-2 h-3 overflow-hidden rounded-full bg-slate-100"
              role="progressbar"
              aria-label="Overall roadmap progress"
              aria-valuenow={overallProgress}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className="h-full rounded-full bg-brand-600 transition-all"
                style={{ width: `${overallProgress}%` }}
              />
            </div>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
          <div className="rounded-md bg-slate-50 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-500">
              <Target className="size-4 text-brand-700" />
              Goal
            </div>
            <p className="mt-2 font-bold text-slate-950">{roadmap.goal || roadmap.target_role}</p>
            <p className="mt-1 text-xs font-semibold text-slate-500">
              Estimated {estimatedMonths} {estimatedMonths === '1' ? 'month' : 'months'}
            </p>
          </div>
          <div className="rounded-md bg-slate-50 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-500">
              <CalendarDays className="size-4 text-brand-700" />
              Duration
            </div>
            <p className="mt-2 font-bold text-slate-950">{roadmap.roadmap.duration_weeks} weeks</p>
          </div>
          <div className="rounded-md bg-slate-50 p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-500">
              <TrendingUp className="size-4 text-brand-700" />
              Job Readiness
            </div>
            <p className="mb-3 text-2xl font-bold text-slate-950">
              {roadmap.roadmap.estimated_job_readiness_before} → {roadmap.roadmap.estimated_job_readiness_after}
            </p>
            <JobReadinessBar
              before={roadmap.roadmap.estimated_job_readiness_before}
              after={roadmap.roadmap.estimated_job_readiness_after}
            />
          </div>
        </div>
      </div>
    </Card>
  );
}
