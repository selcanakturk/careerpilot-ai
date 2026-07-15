import { CheckCircle2, Circle } from 'lucide-react';
import type { RoadmapTask } from '../../types/roadmap';

type RoadmapTaskItemProps = {
  task: RoadmapTask;
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

export default function RoadmapTaskItem({ task }: RoadmapTaskItemProps) {
  const isCompleted = task.status === 'completed';

  return (
    <li className="flex items-start gap-3 rounded-md bg-white px-3 py-3 ring-1 ring-slate-100">
      <span className="mt-0.5 shrink-0" aria-hidden="true">
        {isCompleted ? (
          <CheckCircle2 className="size-5 text-emerald-600" />
        ) : (
          <Circle className="size-5 text-slate-300" />
        )}
      </span>
      <span className="sr-only">{isCompleted ? 'Completed task' : 'Not started task'}</span>
      <span className="min-w-0 flex-1">
        <span
          className={`block text-sm leading-6 ${
            isCompleted ? 'text-slate-400 line-through' : 'text-slate-700'
          }`}
        >
          {task.title}
        </span>
      </span>
      <span className="shrink-0 whitespace-nowrap text-xs font-bold text-slate-500">
        {formatDuration(task.estimated_minutes)}
      </span>
    </li>
  );
}
