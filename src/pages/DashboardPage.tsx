import { useEffect, useState } from 'react';
import { Gauge } from 'lucide-react';
import CurrentRoadmapCard from '../components/dashboard/CurrentRoadmapCard';
import DashboardHero from '../components/dashboard/DashboardHero';
import ProgressOverview from '../components/dashboard/ProgressOverview';
import TodaysFocusCard from '../components/dashboard/TodaysFocusCard';
import TodaysTasksCard from '../components/dashboard/TodaysTasksCard';
import Card from '../components/ui/Card';
import { useAuth } from '../hooks/useAuth';
import { ApiError } from '../services/apiService';
import { getDashboardOverview } from '../services/dashboardService';
import { updateRoadmapStepStatus } from '../services/roadmapService';
import type { DashboardOverview, DashboardRoadmapStep } from '../types/dashboard';

export default function DashboardPage() {
  const { user } = useAuth();
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isStartingWeek, setIsStartingWeek] = useState(false);
  const [error, setError] = useState('');
  const [startWeekError, setStartWeekError] = useState('');

  useEffect(() => {
    let isMounted = true;

    const loadDashboard = async () => {
      setIsLoading(true);
      setError('');

      try {
        const dashboardOverview = await getDashboardOverview();

        if (isMounted) {
          setOverview(dashboardOverview);
        }
      } catch {
        if (isMounted) {
          setError('Unable to load your dashboard.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void loadDashboard();

    return () => {
      isMounted = false;
    };
  }, []);

  if (isLoading) {
    return (
      <Card className="p-8 text-center">
        <div className="mx-auto size-10 animate-pulse rounded-full bg-brand-100" />
        <h1 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">Loading dashboard</h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
          Loading your career overview...
        </p>
      </Card>
    );
  }

  if (error || !overview) {
    return (
      <Card className="p-8 text-center">
        <Gauge className="mx-auto size-10 text-rose-500" />
        <h1 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">
          Unable to load your dashboard.
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
          Please try again in a moment.
        </p>
      </Card>
    );
  }

  const handleStartWeek = async (step: DashboardRoadmapStep) => {
    if (!overview.activeRoadmap || isStartingWeek) {
      return;
    }

    setStartWeekError('');
    setIsStartingWeek(true);

    try {
      const updatedStep = await updateRoadmapStepStatus(overview.activeRoadmap.id, step.id, 'in_progress');

      setOverview((currentOverview) => {
        if (!currentOverview) {
          return currentOverview;
        }

        return {
          ...currentOverview,
          roadmapSteps: currentOverview.roadmapSteps.map((roadmapStep) =>
            roadmapStep.id === updatedStep.id
              ? {
                  ...roadmapStep,
                  status: updatedStep.status,
                }
              : roadmapStep,
          ),
        };
      });
    } catch (startError) {
      if (startError instanceof ApiError) {
        if (startError.status === 401) {
          setStartWeekError('Your session has expired. Please sign in again.');
        } else if (startError.status === 404) {
          setStartWeekError('This roadmap week could not be found.');
        } else {
          setStartWeekError('We could not start this week. Please try again.');
        }
      } else {
        setStartWeekError('We could not start this week. Please try again.');
      }
    } finally {
      setIsStartingWeek(false);
    }
  };

  return (
    <div className="space-y-7">
      <DashboardHero fullName={user?.fullName} overview={overview} />
      <TodaysFocusCard overview={overview} />
      <TodaysTasksCard
        errorMessage={startWeekError}
        isStartingWeek={isStartingWeek}
        onStartWeek={(step) => void handleStartWeek(step)}
        overview={overview}
      />
      <ProgressOverview overview={overview} />
      <CurrentRoadmapCard overview={overview} />
    </div>
  );
}
