import { CheckCircle2, Circle } from 'lucide-react';
import type { DashboardRoadmapTask } from '../../types/dashboard';
import { formatMinutes } from '../../utils/dashboardOverview';

type DashboardTaskItemProps = {
  task: DashboardRoadmapTask;
};

export default function DashboardTaskItem({ task }: DashboardTaskItemProps) {
  const isCompleted = task.status === 'completed';

  return (
    <li className="flex items-start gap-3 rounded-md bg-slate-50 px-4 py-3">
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
        <span className="mt-1 block text-xs font-semibold text-slate-400">
          {isCompleted ? 'Completed' : 'Not started'}
        </span>
      </span>
      <span className="shrink-0 whitespace-nowrap text-xs font-bold text-slate-500">
        {formatMinutes(task.estimatedMinutes)}
      </span>
    </li>
  );
}
