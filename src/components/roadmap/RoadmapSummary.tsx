import Card from '../ui/Card';

type RoadmapSummaryProps = {
  summary: string;
};

export default function RoadmapSummary({ summary }: RoadmapSummaryProps) {
  return (
    <Card className="p-5 sm:p-6">
      <h2 className="text-xl font-bold tracking-tight text-slate-950">Career Summary</h2>
      <p className="mt-3 text-sm leading-6 text-slate-600">{summary}</p>
    </Card>
  );
}
