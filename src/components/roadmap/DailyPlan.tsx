import type { RoadmapDay, RoadmapTask } from '../../types/roadmap';
import DayPlanCard from './DayPlanCard';

type DailyPlanProps = {
  days: RoadmapDay[];
  onToggleTask?: (task: RoadmapTask) => void;
  updatingTaskId?: string | null;
};

const dayOrder = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export default function DailyPlan({ days, onToggleTask, updatingTaskId }: DailyPlanProps) {
  const sortedDays = dayOrder.map(
    (dayName) => days.find((day) => day.day_name === dayName) ?? { day_name: dayName, tasks: [] },
  );

  return (
    <section className="rounded-md border border-brand-100 bg-white p-4">
      <div>
        <h4 className="text-sm font-bold text-slate-950">Daily Planner</h4>
        <p className="mt-1 text-sm leading-6 text-slate-500">
          A read-only daily breakdown for this week. Task completion will be tracked in a later sprint.
        </p>
      </div>
      <div className="mt-4 grid gap-3">
        {sortedDays.map((day) => (
          <DayPlanCard
            key={day.day_name}
            day={day}
            onToggleTask={onToggleTask}
            updatingTaskId={updatingTaskId}
          />
        ))}
      </div>
    </section>
  );
}
