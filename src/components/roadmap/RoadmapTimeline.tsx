import type { RoadmapStep } from '../../types/roadmap';
import RoadmapStepCard from './RoadmapStepCard';

type RoadmapTimelineProps = {
  steps: RoadmapStep[];
};

export default function RoadmapTimeline({ steps }: RoadmapTimelineProps) {
  return (
    <section>
      <h2 className="mb-5 text-xl font-bold tracking-tight text-slate-950">Weekly Timeline</h2>
      <div className="relative space-y-5 before:absolute before:bottom-0 before:left-4 before:top-0 before:w-px before:bg-slate-200">
        {steps.map((step) => (
          <div key={step.week_number} className="relative grid gap-4 pl-10">
            <span className="absolute left-0 top-6 flex size-8 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white ring-4 ring-white">
              {step.week_number}
            </span>
            <RoadmapStepCard step={step} />
          </div>
        ))}
      </div>
    </section>
  );
}
