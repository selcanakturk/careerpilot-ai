import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, Calendar, FileText, Filter, Search, UploadCloud, WandSparkles } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import Input from '../components/ui/Input';
import { useAuth } from '../hooks/useAuth';
import { ApiError } from '../services/apiService';
import { analyzeCV, getCompletedAnalysesForUploadIds } from '../services/analysisService';
import { getUserCVUploads, type CVUploadRecord } from '../services/cvUploadService';
import type { CVAnalysis } from '../types/analysis';

const filters = ['All', 'Entry-level', 'Mid-level', 'Senior', 'Lead or Manager'];

const experienceLabels: Record<string, string> = {
  entry: 'Entry-level',
  mid: 'Mid-level',
  senior: 'Senior',
  lead: 'Lead or Manager',
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));
}

function getExperienceLabel(value: string) {
  return experienceLabels[value] ?? value;
}

function getAnalyzeErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return 'Your session has expired. Please sign in again.';
    }

    if (error.status === 404) {
      return 'The uploaded CV could not be found.';
    }

    if (error.status === 415) {
      return 'Only PDF files can be analyzed right now.';
    }

    if (error.status === 502) {
      return 'The AI analysis service is temporarily unavailable.';
    }
  }

  return 'The analysis could not be completed. Please try again.';
}

export default function HistoryPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [uploads, setUploads] = useState<CVUploadRecord[]>([]);
  const [analysesByUploadId, setAnalysesByUploadId] = useState<Record<string, CVAnalysis>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [analyzingUploadId, setAnalyzingUploadId] = useState('');
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState('All');

  useEffect(() => {
    let isMounted = true;

    const loadUploads = async () => {
      if (!user) {
        setError('Please sign in to view your CV uploads.');
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError('');

      try {
        const records = await getUserCVUploads(user.id);
        const analyses = await getCompletedAnalysesForUploadIds(records.map((record) => record.id));

        if (isMounted) {
          setUploads(records);
          setAnalysesByUploadId(analyses);
        }
      } catch (loadError) {
        console.error('Unable to load CV uploads:', loadError);

        if (isMounted) {
          setError('We could not load your CV uploads. Please try again.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void loadUploads();

    return () => {
      isMounted = false;
    };
  }, [user]);

  const filteredUploads = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLowerCase();

    return uploads.filter((upload) => {
      const experienceLabel = getExperienceLabel(upload.experience_level);
      const matchesSearch =
        !normalizedQuery ||
        upload.target_role.toLowerCase().includes(normalizedQuery) ||
        upload.file_name.toLowerCase().includes(normalizedQuery) ||
        experienceLabel.toLowerCase().includes(normalizedQuery);

      const matchesFilter = activeFilter === 'All' || experienceLabel === activeFilter;

      return matchesSearch && matchesFilter;
    });
  }, [activeFilter, searchQuery, uploads]);

  const handleAnalyzeUpload = async (uploadId: string) => {
    if (analyzingUploadId) {
      return;
    }

    setActionError('');
    setAnalyzingUploadId(uploadId);

    try {
      const analysis = await analyzeCV(uploadId);
      navigate(`/analysis/${analysis.id}`);
    } catch (analyzeError) {
      console.error('Unable to analyze CV upload:', analyzeError);
      setActionError(getAnalyzeErrorMessage(analyzeError));
    } finally {
      setAnalyzingUploadId('');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold text-brand-700">Saved Uploads</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950">CV Upload History</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Review your uploaded CV files, start AI analysis, and reopen completed career readiness
          reports.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
        <Input
          label="Search Uploads"
          name="search"
          placeholder="Search by role, file name, or experience level"
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          {filters.map((filter) => (
            <button
              key={filter}
              type="button"
              onClick={() => setActiveFilter(filter)}
              className={`inline-flex min-h-11 items-center gap-2 rounded-md border px-4 text-sm font-semibold transition ${
                activeFilter === filter
                  ? 'border-brand-200 bg-brand-50 text-brand-700'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700'
              }`}
            >
              <Filter className="size-4" />
              {filter}
            </button>
          ))}
        </div>
      </div>

      {actionError && (
        <div role="alert" className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {actionError}
        </div>
      )}

      {isLoading ? (
        <Card className="p-8 text-center">
          <div className="mx-auto size-10 animate-pulse rounded-full bg-brand-100" />
          <h2 className="mt-4 text-xl font-bold tracking-tight text-slate-950">Loading uploads</h2>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
            Fetching your saved CV upload records securely.
          </p>
        </Card>
      ) : error ? (
        <Card className="p-8 text-center">
          <Search className="mx-auto size-10 text-rose-500" />
          <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">Unable to load uploads</h2>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">{error}</p>
        </Card>
      ) : uploads.length === 0 ? (
        <Card className="p-8 text-center">
          <UploadCloud className="mx-auto size-10 text-brand-700" />
          <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">No CV uploads yet</h2>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
            Upload your CV and choose a target role to create your first saved upload record.
          </p>
          <Link to="/upload-cv" className="mt-6 inline-flex">
            <Button>
              <UploadCloud className="size-4" />
              Upload CV
            </Button>
          </Link>
        </Card>
      ) : filteredUploads.length === 0 ? (
        <Card className="border-dashed p-6 text-center">
          <Search className="mx-auto size-8 text-slate-400" />
          <h2 className="mt-3 font-semibold text-slate-950">No matching uploads found</h2>
          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-600">
            Try adjusting your search or experience level filter.
          </p>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          {filteredUploads.map((upload) => {
            const analysis = analysesByUploadId[upload.id];
            const isAnalyzingCurrentUpload = analyzingUploadId === upload.id;

            return (
              <Card key={upload.id} className="h-full p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="break-words text-lg font-semibold text-slate-950">
                      {upload.target_role}
                    </p>
                    <p className="mt-2 flex items-start gap-2 break-words text-sm leading-6 text-slate-600">
                      <FileText className="mt-1 size-4 shrink-0 text-brand-700" />
                      {upload.file_name}
                    </p>
                  </div>
                  <span
                    className={`shrink-0 rounded-md px-3 py-1 text-xs font-bold ${
                      analysis ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
                    }`}
                  >
                    {analysis ? 'Completed' : 'AI analysis not generated yet'}
                  </span>
                </div>

                <div className="mt-5 space-y-3 border-t border-slate-200 pt-4 text-sm text-slate-600">
                  <div className="flex items-center justify-between gap-4">
                    <span className="font-medium text-slate-500">Experience level</span>
                    <span className="font-semibold text-slate-800">
                      {getExperienceLabel(upload.experience_level)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <span className="font-medium text-slate-500">File type</span>
                    <span className="font-semibold text-slate-800">{upload.file_type}</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-500">
                    <Calendar className="size-4" />
                    {formatDate(upload.created_at)}
                  </div>
                  {analysis && (
                    <div className="flex items-center justify-between gap-4">
                      <span className="font-medium text-slate-500">Overall score</span>
                      <span className="font-bold text-slate-950">{analysis.overall_score}%</span>
                    </div>
                  )}
                </div>

                <div className="mt-5 flex items-center justify-between gap-3">
                  <span className="rounded-md bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">
                    CV uploaded
                  </span>
                  {analysis ? (
                    <Link
                      to={`/analysis/${analysis.id}`}
                      className="inline-flex min-h-9 items-center justify-center gap-2 rounded-md border border-brand-200 bg-brand-50 px-3 text-sm font-semibold text-brand-700 transition hover:bg-brand-100"
                    >
                      View analysis
                      <ArrowRight className="size-4" />
                    </Link>
                  ) : (
                    <button
                      type="button"
                      onClick={() => void handleAnalyzeUpload(upload.id)}
                      disabled={Boolean(analyzingUploadId)}
                      className="inline-flex min-h-9 items-center justify-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 transition hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <WandSparkles className="size-4" />
                      {isAnalyzingCurrentUpload ? 'Analyzing...' : 'Analyze CV'}
                    </button>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
