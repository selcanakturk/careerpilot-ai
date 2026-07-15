import { useEffect, useState } from 'react';
import { Map } from 'lucide-react';
import { useParams } from 'react-router-dom';
import Card from '../components/ui/Card';
import RoadmapHero from '../components/roadmap/RoadmapHero';
import RoadmapSummary from '../components/roadmap/RoadmapSummary';
import RoadmapTimeline from '../components/roadmap/RoadmapTimeline';
import { ApiError } from '../services/apiService';
import { getRoadmap, updateRoadmapStepStatus } from '../services/roadmapService';
import type { RoadmapGenerateResponse, RoadmapStepStatus } from '../types/roadmap';

export default function RoadmapPage() {
  const { roadmapId } = useParams();
  const [roadmap, setRoadmap] = useState<RoadmapGenerateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [stepError, setStepError] = useState('');
  const [updatingStepId, setUpdatingStepId] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const loadRoadmap = async () => {
      if (!roadmapId) {
        setRoadmap(null);
        setError('Roadmap not found.');
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError('');

      try {
        const record = await getRoadmap(roadmapId);

        if (isMounted) {
          setRoadmap(record);
          setError(record ? '' : 'Roadmap not found.');
        }
      } catch {
        if (isMounted) {
          setError('Unable to load roadmap.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void loadRoadmap();

    return () => {
      isMounted = false;
    };
  }, [roadmapId]);

  if (isLoading) {
    return (
      <Card className="p-8 text-center">
        <div className="mx-auto size-10 animate-pulse rounded-full bg-brand-100" />
        <h1 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">Loading roadmap</h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
          Loading your personalized AI roadmap...
        </p>
      </Card>
    );
  }

  if (error || !roadmap) {
    return (
      <Card className="p-8 text-center">
        <Map className="mx-auto size-10 text-brand-700" />
        <h1 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">
          {error === 'Roadmap not found.' ? 'Roadmap not found.' : 'Unable to load roadmap.'}
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
          {error === 'Roadmap not found.'
            ? 'The roadmap could not be found or you do not have access to it.'
            : 'Please try again in a moment.'}
        </p>
      </Card>
    );
  }

  const totalSteps = roadmap.roadmap.steps.length;
  const completedSteps = roadmap.roadmap.steps.filter((step) => step.status === 'completed').length;
  const progressPercent = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;

  const handleStepStatusChange = async (stepId: string, status: RoadmapStepStatus) => {
    if (updatingStepId) {
      return;
    }

    setStepError('');
    setUpdatingStepId(stepId);

    try {
      const updatedStep = await updateRoadmapStepStatus(roadmap.id, stepId, status);

      setRoadmap((currentRoadmap) => {
        if (!currentRoadmap) {
          return currentRoadmap;
        }

        return {
          ...currentRoadmap,
          roadmap: {
            ...currentRoadmap.roadmap,
            steps: currentRoadmap.roadmap.steps.map((step) =>
              step.id === updatedStep.id
                ? {
                    ...step,
                    status: updatedStep.status,
                    updated_at: updatedStep.updated_at,
                  }
                : step,
            ),
          },
        };
      });
    } catch (updateError) {
      if (updateError instanceof ApiError) {
        if (updateError.status === 401) {
          setStepError('Your session has expired. Please sign in again.');
        } else if (updateError.status === 404) {
          setStepError('This roadmap step could not be found.');
        } else {
          setStepError('We could not update this roadmap step. Please try again.');
        }
      } else {
        setStepError('We could not update this roadmap step. Please try again.');
      }
    } finally {
      setUpdatingStepId(null);
    }
  };

  return (
    <div className="space-y-6">
      <RoadmapHero roadmap={roadmap} />
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
          <div>
            <p className="text-sm font-bold text-brand-700">Roadmap Progress</p>
            <h2 className="mt-1 text-2xl font-bold tracking-tight text-slate-950">
              {completedSteps} / {totalSteps} weeks completed
            </h2>
          </div>
          <p className="text-3xl font-bold text-slate-950">{progressPercent}%</p>
        </div>
        <div className="mt-4 h-3 overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-brand-600 transition-all"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        {stepError && (
          <div role="alert" className="mt-4 rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {stepError}
          </div>
        )}
      </Card>
      <RoadmapSummary summary={roadmap.roadmap.summary} />
      <RoadmapTimeline
        roadmapId={roadmap.id}
        steps={roadmap.roadmap.steps}
        updatingStepId={updatingStepId}
        onStepStatusChange={(stepId, status) => void handleStepStatusChange(stepId, status)}
      />
    </div>
  );
}
