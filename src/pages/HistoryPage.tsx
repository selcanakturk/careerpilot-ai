import { Calendar, Filter, Search, UploadCloud } from 'lucide-react';
import { Link } from 'react-router-dom';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import Input from '../components/ui/Input';
import { recentAnalyses } from '../data/mockData';
import { useAuth } from '../hooks/useAuth';

const filters = ['All', 'Ready', 'Needs refinement', 'High match'];

export default function HistoryPage() {
  const { hasAnalysis } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold text-brand-700">Saved Reviews</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950">Analysis History</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Review previous CV analyses, compare role fit, and continue improving your application
          strategy.
        </p>
      </div>

      {!hasAnalysis ? (
        <Card className="p-8 text-center">
          <UploadCloud className="mx-auto size-10 text-brand-700" />
          <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">No analyses yet</h2>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
            Upload your CV and choose a target role to create your first saved career readiness
            report.
          </p>
          <Link to="/upload-cv" className="mt-6 inline-flex">
            <Button>
              <UploadCloud className="size-4" />
              Upload CV
            </Button>
          </Link>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
            <Input label="Search Analyses" name="search" placeholder="Search by role, status, or keyword" />
            <div className="flex flex-wrap gap-2">
              {filters.map((filter) => (
                <button
                  key={filter}
                  type="button"
                  className="inline-flex min-h-11 items-center gap-2 rounded-md border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 transition hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700"
                >
                  <Filter className="size-4" />
                  {filter}
                </button>
              ))}
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            {recentAnalyses.map((item) => (
              <Link key={item.id} to={`/analysis/${item.id}`}>
                <Card className="h-full p-5 transition hover:-translate-y-1 hover:shadow-lg">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-lg font-semibold text-slate-950">{item.role}</p>
                      <p className="mt-2 text-sm leading-6 text-slate-600">{item.summary}</p>
                    </div>
                    <span className="rounded-md bg-brand-50 px-3 py-1 text-sm font-bold text-brand-700">
                      {item.score}%
                    </span>
                  </div>
                  <div className="mt-5 flex items-center justify-between gap-4 border-t border-slate-200 pt-4 text-sm text-slate-500">
                    <span className="flex items-center gap-2">
                      <Calendar className="size-4" />
                      {item.date}
                    </span>
                    <span className="font-medium text-slate-700">{item.status}</span>
                  </div>
                </Card>
              </Link>
            ))}
          </div>

          <Card className="border-dashed p-6 text-center">
            <Search className="mx-auto size-8 text-slate-400" />
            <h2 className="mt-3 font-semibold text-slate-950">No archived analyses found</h2>
            <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-600">
              This empty state is ready for future filters or searches that return no matching
              results.
            </p>
          </Card>
        </>
      )}
    </div>
  );
}
