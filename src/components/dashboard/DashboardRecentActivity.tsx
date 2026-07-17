import { Activity, CheckCircle2, Flag, Map } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { DashboardOverview } from '../../types/dashboard';
import Card from '../ui/Card';

type DashboardRecentActivityProps = {
  overview: DashboardOverview;
};

type ActivityItem = {
  id: string;
  label: string;
  timestamp: string;
  icon: LucideIcon;
};

function getActivityDateLabel(timestamp: string) {
  const date = new Date(timestamp);

  if (Number.isNaN(date.getTime())) {
    return '';
  }

  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);

  if (date.toDateString() === today.toDateString()) {
    return 'Today';
  }

  if (date.toDateString() === yesterday.toDateString()) {
    return 'Yesterday';
  }

  return new Intl.DateTimeFormat('en', {
    day: 'numeric',
    month: 'short',
  }).format(date);
}

function toSortableTime(timestamp: string) {
  const time = new Date(timestamp).getTime();
  return Number.isNaN(time) ? 0 : time;
}

function getRecentActivities(overview: DashboardOverview) {
  const activities: ActivityItem[] = [];

  if (overview.activeRoadmap?.createdAt) {
    activities.push({
      icon: Map,
      id: `roadmap-${overview.activeRoadmap.id}`,
      label: 'Generated AI Career Roadmap',
      timestamp: overview.activeRoadmap.createdAt,
    });
  }

  overview.roadmapSteps.forEach((step) => {
    if (!step.updatedAt || step.status === 'not_started') {
      return;
    }

    activities.push({
      icon: step.status === 'completed' ? Flag : Activity,
      id: `step-${step.id}-${step.status}`,
      label: step.status === 'completed' ? `Completed Week ${step.weekNumber}` : `Started Week ${step.weekNumber}`,
      timestamp: step.updatedAt,
    });
  });

  overview.roadmapTasks.forEach((task) => {
    if (task.status !== 'completed' || !task.updatedAt) {
      return;
    }

    activities.push({
      icon: CheckCircle2,
      id: `task-${task.id}`,
      label: `Completed "${task.title}"`,
      timestamp: task.updatedAt,
    });
  });

  return activities
    .sort((firstActivity, secondActivity) => toSortableTime(secondActivity.timestamp) - toSortableTime(firstActivity.timestamp))
    .slice(0, 5);
}

export default function DashboardRecentActivity({ overview }: DashboardRecentActivityProps) {
  const activities = getRecentActivities(overview);

  return (
    <Card className="p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-bold text-brand-700">Recent Activity</p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">Latest progress updates</h2>
        </div>
        <span className="flex size-12 shrink-0 items-center justify-center rounded-md bg-brand-50 text-brand-700">
          <Activity className="size-6" />
        </span>
      </div>

      {activities.length > 0 ? (
        <ul className="mt-5 divide-y divide-slate-100">
          {activities.map((activity) => {
            const Icon = activity.icon;

            return (
              <li key={activity.id} className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
                <div className="flex min-w-0 items-center gap-3">
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-slate-50 text-brand-700">
                    <Icon className="size-4" />
                  </span>
                  <p className="truncate text-sm font-semibold text-slate-800">{activity.label}</p>
                </div>
                <time className="shrink-0 text-xs font-bold text-slate-400" dateTime={activity.timestamp}>
                  {getActivityDateLabel(activity.timestamp)}
                </time>
              </li>
            );
          })}
        </ul>
      ) : (
        <div className="mt-5 rounded-md bg-slate-50 p-4">
          <p className="text-sm font-semibold text-slate-700">No recent activity yet.</p>
          <p className="mt-1 text-sm leading-6 text-slate-500">
            Your roadmap activity will appear here as you make progress.
          </p>
        </div>
      )}
    </Card>
  );
}
