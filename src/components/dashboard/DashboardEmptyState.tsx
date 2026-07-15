import { ArrowRight, UploadCloud } from 'lucide-react';
import { Link } from 'react-router-dom';
import Button from '../ui/Button';
import Card from '../ui/Card';

type DashboardEmptyStateProps = {
  analysisId?: string;
};

export default function DashboardEmptyState({ analysisId }: DashboardEmptyStateProps) {
  return (
    <Card className="p-6 text-center">
      <UploadCloud className="mx-auto size-10 text-brand-700" />
      <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">No roadmap yet</h2>
      <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
        Generate a roadmap from your latest CV analysis.
      </p>
      <div className="mt-6 inline-flex">
        {analysisId ? (
          <Link to={`/analysis/${analysisId}`}>
            <Button>
              View Analysis
              <ArrowRight className="size-4" />
            </Button>
          </Link>
        ) : (
          <Link to="/upload-cv">
            <Button>
              Upload CV
              <UploadCloud className="size-4" />
            </Button>
          </Link>
        )}
      </div>
    </Card>
  );
}
