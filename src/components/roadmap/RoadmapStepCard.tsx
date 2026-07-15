import { Clock, Hammer } from 'lucide-react';
import Card from '../ui/Card';
import type { RoadmapPriority, RoadmapStep } from '../../types/roadmap';
import ResourceList from './ResourceList';

type RoadmapStepCardProps = {
  step: RoadmapStep;
};

const priorityClasses: Record<RoadmapPriority, string> = {
  critical: 'bg-rose-50 text-rose-700 ring-rose-100',
  high: 'bg-amber-50 text-amber-700 ring-amber-100',
  medium: 'bg-brand-50 text-brand-700 ring-brand-100',
  low: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
};

export default function RoadmapStepCard({ step }: RoadmapStepCardProps) {
  return (
    <Card className="p-5 sm:p-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div>
          <p className="text-sm font-bold text-brand-700">Week {step.week_number}</p>
          <h3 className="mt-1 text-xl font-bold tracking-tight text-slate-950">{step.title}</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className={`rounded-md px-3 py-1 text-xs font-bold ring-1 ${priorityClasses[step.priority]}`}>
            {step.priority}
          </span>
          <span className="inline-flex items-center gap-1 rounded-md bg-slate-50 px-3 py-1 text-xs font-bold text-slate-600 ring-1 ring-slate-100">
            <Clock className="size-3.5" />
            {step.estimated_hours}h
          </span>
        </div>
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
