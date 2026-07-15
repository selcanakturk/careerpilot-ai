import type { RoadmapStep, RoadmapStepStatus } from '../../types/roadmap';
import RoadmapStepCard from './RoadmapStepCard';

type RoadmapTimelineProps = {
  roadmapId: string;
  steps: RoadmapStep[];
  updatingStepId: string | null;
  onStepStatusChange: (stepId: string, status: RoadmapStepStatus) => void;
};

const dotClasses: Record<RoadmapStepStatus, string> = {
  completed: 'bg-emerald-600 text-white',
  in_progress: 'bg-brand-600 text-white',
  not_started: 'bg-white text-slate-500 ring-slate-200',
};

export default function RoadmapTimeline({
  roadmapId,
  steps,
  updatingStepId,
  onStepStatusChange,
}: RoadmapTimelineProps) {
  return (
    <section>
      <h2 className="mb-5 text-xl font-bold tracking-tight text-slate-950">Weekly Timeline</h2>
      <div className="relative space-y-5 before:absolute before:bottom-0 before:left-4 before:top-0 before:w-px before:bg-slate-200">
        {steps.map((step) => (
          <div key={step.week_number} className="relative grid gap-4 pl-10">
            <span
              className={`absolute left-0 top-6 flex size-8 items-center justify-center rounded-full text-xs font-bold ring-4 ring-white ${dotClasses[step.status]}`}
            >
              {step.week_number}
            </span>
            <RoadmapStepCard
              roadmapId={roadmapId}
              step={step}
              isUpdating={Boolean(step.id) && updatingStepId === step.id}
              onStatusChange={onStepStatusChange}
            />
          </div>
        ))}
      </div>
    </section>
  );
}
