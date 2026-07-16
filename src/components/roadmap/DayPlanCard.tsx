import type { RoadmapDay, RoadmapTask } from '../../types/roadmap';
import RoadmapTaskItem from './RoadmapTaskItem';

type DayPlanCardProps = {
  day: RoadmapDay;
  onToggleTask?: (task: RoadmapTask) => void;
  updatingTaskId?: string | null;
};

function formatDuration(minutes: number) {
  if (minutes < 60) {
    return `${minutes} min`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  if (remainingMinutes === 0) {
    return `${hours}h`;
  }

  return `${hours}h ${remainingMinutes}m`;
}

export default function DayPlanCard({ day, onToggleTask, updatingTaskId }: DayPlanCardProps) {
  const totalMinutes = day.tasks.reduce((sum, task) => sum + task.estimated_minutes, 0);
  const sortedTasks = [...day.tasks].sort((firstTask, secondTask) => {
    const firstOrder = firstTask.task_order ?? 0;
    const secondOrder = secondTask.task_order ?? 0;
    return firstOrder - secondOrder;
  });

  return (
    <section className="rounded-md border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <h5 className="text-sm font-bold text-slate-950">{day.day_name}</h5>
        <div className="flex flex-wrap gap-2 text-xs font-bold text-slate-500">
          <span>{day.tasks.length} tasks</span>
          <span>{formatDuration(totalMinutes)}</span>
        </div>
      </div>
      {sortedTasks.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {sortedTasks.map((task) => (
            <RoadmapTaskItem
              key={task.id}
              isUpdating={updatingTaskId === task.id}
              onToggle={onToggleTask}
              task={task}
            />
          ))}
        </ul>
      ) : (
        <p className="mt-3 rounded-md bg-white px-3 py-3 text-sm leading-6 text-slate-500 ring-1 ring-slate-100">
          Rest, review, or catch-up day. No scheduled tasks.
        </p>
      )}
    </section>
  );
}
