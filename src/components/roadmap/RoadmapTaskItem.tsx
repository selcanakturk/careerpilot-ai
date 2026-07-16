import { CheckCircle2, Circle } from 'lucide-react';
import type { RoadmapTask } from '../../types/roadmap';

type RoadmapTaskItemProps = {
  isUpdating?: boolean;
  onToggle?: (task: RoadmapTask) => void;
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

export default function RoadmapTaskItem({ isUpdating = false, onToggle, task }: RoadmapTaskItemProps) {
  const isCompleted = task.status === 'completed';

  return (
    <li className="flex items-start gap-3 rounded-md bg-white px-3 py-3 ring-1 ring-slate-100">
      <button
        type="button"
        aria-label={`${isCompleted ? 'Mark not started' : 'Mark complete'}: ${task.title}`}
        aria-pressed={isCompleted}
        disabled={isUpdating || !onToggle}
        onClick={() => onToggle?.(task)}
        className="mt-0.5 shrink-0 rounded-full text-slate-300 transition hover:text-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isUpdating ? (
          <span className="block size-5 animate-pulse rounded-full bg-brand-100" />
        ) : isCompleted ? (
          <CheckCircle2 className="size-5 text-emerald-600" />
        ) : (
          <Circle className="size-5" />
        )}
      </button>
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
