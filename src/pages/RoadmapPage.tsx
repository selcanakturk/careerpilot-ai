import { useParams } from 'react-router-dom';
import Card from '../components/ui/Card';

export default function RoadmapPage() {
  const { roadmapId } = useParams();

  return (
    <Card className="p-8">
      <p className="text-sm font-semibold text-brand-700">Career Roadmap</p>
      <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950">Career Roadmap</h1>
      <p className="mt-4 break-words text-sm font-medium text-slate-600">
        Roadmap ID: <span className="text-slate-950">{roadmapId ?? 'Not found'}</span>
      </p>
      <p className="mt-3 text-sm leading-6 text-slate-600">Roadmap details will be added next.</p>
    </Card>
  );
}
