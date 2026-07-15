import { useEffect, useState } from 'react';
import { Map } from 'lucide-react';
import { useParams } from 'react-router-dom';
import Card from '../components/ui/Card';
import RoadmapHero from '../components/roadmap/RoadmapHero';
import RoadmapSummary from '../components/roadmap/RoadmapSummary';
import RoadmapTimeline from '../components/roadmap/RoadmapTimeline';
import { getRoadmap } from '../services/roadmapService';
import type { RoadmapGenerateResponse } from '../types/roadmap';

export default function RoadmapPage() {
  const { roadmapId } = useParams();
  const [roadmap, setRoadmap] = useState<RoadmapGenerateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

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

  return (
    <div className="space-y-6">
      <RoadmapHero roadmap={roadmap} />
      <RoadmapSummary summary={roadmap.roadmap.summary} />
      <RoadmapTimeline steps={roadmap.roadmap.steps} />
    </div>
  );
}
