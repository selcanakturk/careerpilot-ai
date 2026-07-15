import { ArrowRight, CalendarDays, Play } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { DashboardOverview, DashboardRoadmapStep } from '../../types/dashboard';
import {
  formatMinutes,
  getCurrentDashboardStep,
  getCurrentDayName,
  isDashboardRoadmapCompleted,
} from '../../utils/dashboardOverview';
import Button from '../ui/Button';
import Card from '../ui/Card';
import DashboardTaskItem from './DashboardTaskItem';

type TodaysTasksCardProps = {
  errorMessage: string;
  isStartingWeek: boolean;
  onStartWeek: (step: DashboardRoadmapStep) => void;
  overview: DashboardOverview;
};

export default function TodaysTasksCard({
  errorMessage,
  isStartingWeek,
  onStartWeek,
  overview,
}: TodaysTasksCardProps) {
  const today = getCurrentDayName();
  const currentStep = getCurrentDashboardStep(overview.roadmapSteps);
  const isCompletedRoadmap = isDashboardRoadmapCompleted(overview);

  if (!overview.activeRoadmap) {
    return null;
  }

  if (isCompletedRoadmap) {
    return (
      <Card className="p-6">
        <CalendarDays className="size-7 text-emerald-600" />
        <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">Your roadmap is complete.</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Review your progress or generate a new roadmap from a fresh CV analysis.
        </p>
        <Link to={`/roadmaps/${overview.activeRoadmap.id}`} className="mt-5 inline-flex">
          <Button>
            Open Roadmap
            <ArrowRight className="size-4" />
          </Button>
        </Link>
      </Card>
    );
  }

  if (!currentStep) {
    return null;
  }

  if (currentStep.status === 'not_started') {
    return (
      <Card className="p-6">
        <p className="text-sm font-bold text-brand-700">Today’s Tasks</p>
        <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">
          Your current week has not started yet.
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Start Week {currentStep.weekNumber} to unlock today’s planned tasks.
        </p>
        {errorMessage && (
          <div role="alert" className="mt-4 rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {errorMessage}
          </div>
        )}
        <Button
          className="mt-5 w-full sm:w-auto"
          disabled={isStartingWeek}
          onClick={() => onStartWeek(currentStep)}
          aria-label={`Start week ${currentStep.weekNumber}`}
        >
          <Play className="size-4" />
          {isStartingWeek ? 'Starting week...' : 'Start Week'}
        </Button>
      </Card>
    );
  }

  const todaysTasks = overview.roadmapTasks
    .filter((task) => task.stepId === currentStep.id && task.dayName === today)
    .sort((firstTask, secondTask) => firstTask.taskOrder - secondTask.taskOrder);
  const completedTasks = todaysTasks.filter((task) => task.status === 'completed').length;
  const totalMinutes = todaysTasks.reduce((sum, task) => sum + task.estimatedMinutes, 0);
  const progressPercent = todaysTasks.length > 0 ? Math.round((completedTasks / todaysTasks.length) * 100) : 0;

  return (
    <Card className="p-6">
      <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
        <div>
          <p className="text-sm font-bold text-brand-700">Today’s Tasks</p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">
            Week {currentStep.weekNumber} · {today}
          </h2>
          {todaysTasks.length > 0 ? (
            <>
              <p className="mt-3 text-sm leading-6 text-slate-600">
                {completedTasks} / {todaysTasks.length} tasks completed · {formatMinutes(totalMinutes)}
              </p>
              <div
                className="mt-4 h-3 overflow-hidden rounded-full bg-slate-100"
                role="progressbar"
                aria-label={`Today’s task progress is ${progressPercent} percent`}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={progressPercent}
              >
                <div className="h-full rounded-full bg-brand-600" style={{ width: `${progressPercent}%` }} />
              </div>
            </>
          ) : (
            <div className="mt-3">
              <p className="text-sm font-semibold text-slate-700">No tasks are scheduled for today.</p>
              <p className="mt-1 text-sm leading-6 text-slate-500">
                Use today as a review, catch-up, or rest day.
              </p>
            </div>
          )}
        </div>
        <Link to={`/roadmaps/${overview.activeRoadmap.id}/weeks/${currentStep.id}`}>
          <Button variant={todaysTasks.length > 0 ? 'primary' : 'secondary'} className="w-full sm:w-auto">
            {todaysTasks.length > 0 ? 'Open Today’s Plan' : 'Review Weekly Plan'}
            <ArrowRight className="size-4" />
          </Button>
        </Link>
      </div>

      {todaysTasks.length > 0 && (
        <ul className="mt-5 grid gap-3">
          {todaysTasks.map((task) => (
            <DashboardTaskItem key={task.id} task={task} />
          ))}
        </ul>
      )}
    </Card>
  );
}
