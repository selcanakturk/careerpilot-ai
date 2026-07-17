import { useEffect, useState } from 'react';
import { ArrowLeft, ExternalLink, Gauge } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import {
  generateJobMatch,
  getJobPosting,
  listCompletedAnalyses,
} from '../services/jobService';
import type { CompletedAnalysisOption, JobMatch, JobPosting } from '../types/job';

function formatOption(value: string | null) {
  return value ? value.replace(/_/g, ' ') : 'Not specified';
}

function readinessLabel(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function SkillList({ items }: { items: string[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">No items returned.</p>;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <span key={item} className="rounded-md bg-slate-50 px-3 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-100">
          {item}
        </span>
      ))}
    </div>
  );
}

export default function JobDetailPage() {
  const { jobPostingId } = useParams();
  const [job, setJob] = useState<JobPosting | null>(null);
  const [analyses, setAnalyses] = useState<CompletedAnalysisOption[]>([]);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState('');
  const [match, setMatch] = useState<JobMatch | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState('');
  const [matchError, setMatchError] = useState('');

  useEffect(() => {
    let isMounted = true;

    const loadJob = async () => {
      if (!jobPostingId) {
        setError('The job posting could not be found.');
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setError('');

      try {
        const [jobPosting, completedAnalyses] = await Promise.all([
          getJobPosting(jobPostingId),
          listCompletedAnalyses(),
        ]);

        if (isMounted) {
          setJob(jobPosting);
          setAnalyses(completedAnalyses);
          setSelectedAnalysisId(completedAnalyses[0]?.id ?? '');
        }
      } catch (loadError) {
        if (isMounted) {
          setError(loadError instanceof Error ? loadError.message : 'Unable to load job posting.');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void loadJob();

    return () => {
      isMounted = false;
    };
  }, [jobPostingId]);

  const handleGenerateMatch = async () => {
    if (!job || !selectedAnalysisId || isAnalyzing) {
      return;
    }

    setIsAnalyzing(true);
    setMatchError('');

    try {
      const generatedMatch = await generateJobMatch(job.id, selectedAnalysisId);
      setMatch(generatedMatch);
    } catch (generateError) {
      setMatchError(generateError instanceof Error ? generateError.message : 'Unable to complete the job matching request.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  if (isLoading) {
    return (
      <Card className="p-8 text-center">
        <div className="mx-auto size-10 animate-pulse rounded-full bg-brand-100" />
        <h1 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">Loading job posting</h1>
      </Card>
    );
  }

  if (error || !job) {
    return (
      <Card className="p-8 text-center">
        <h1 className="text-2xl font-bold tracking-tight text-slate-950">Job posting not found</h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
          {error || 'The job posting or CV analysis could not be found.'}
        </p>
        <Link to="/jobs" className="mt-5 inline-flex">
          <Button variant="secondary">
            <ArrowLeft className="size-4" />
            Back to jobs
          </Button>
        </Link>
      </Card>
    );
  }

  return (
    <div className="space-y-7">
      <Link to="/jobs" className="inline-flex text-sm font-semibold text-slate-600 hover:text-slate-950">
        <ArrowLeft className="mr-2 size-4" />
        Back to Job Center
      </Link>

      <Card className="p-6">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
          <div>
            <p className="text-sm font-bold text-brand-700">Job opportunity</p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">{job.title}</h1>
            <p className="mt-1 text-lg font-semibold text-slate-700">{job.company_name}</p>
            <p className="mt-3 text-sm text-slate-500">
              {job.location || 'Location not specified'} · {formatOption(job.work_mode)} ·{' '}
              {formatOption(job.employment_type)}
            </p>
          </div>
          {job.source_url && (
            <a href={job.source_url} target="_blank" rel="noreferrer">
              <Button variant="secondary" className="w-full lg:w-auto">
                Open original posting
                <ExternalLink className="size-4" />
              </Button>
            </a>
          )}
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="text-xl font-bold tracking-tight text-slate-950">Job description</h2>
        <p className="mt-4 whitespace-pre-wrap break-words text-sm leading-6 text-slate-600">{job.description}</p>
      </Card>

      <Card className="p-6">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div className="flex-1">
            <h2 className="text-xl font-bold tracking-tight text-slate-950">CV match analysis</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Select a completed CV analysis and compare it with this job posting.
            </p>
            <label className="mt-4 block text-sm font-medium text-slate-700">
              <span className="mb-2 block">Completed CV analysis</span>
              <select
                className="min-h-11 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition hover:border-slate-300 focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
                value={selectedAnalysisId}
                onChange={(event) => setSelectedAnalysisId(event.target.value)}
              >
                {analyses.length === 0 ? (
                  <option value="">No completed analyses available</option>
                ) : (
                  analyses.map((analysis) => (
                    <option key={analysis.id} value={analysis.id}>
                      {analysis.target_role}
                    </option>
                  ))
                )}
              </select>
            </label>
          </div>
          <Button
            disabled={!selectedAnalysisId || isAnalyzing}
            onClick={() => void handleGenerateMatch()}
            className="w-full lg:w-auto"
          >
            {isAnalyzing ? 'Analyzing match...' : 'Analyze Job Match'}
          </Button>
        </div>
        {matchError && (
          <div role="alert" className="mt-5 rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {matchError}
          </div>
        )}
      </Card>

      {match && (
        <Card className="p-6">
          <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
            <div className="rounded-md bg-brand-50 p-5 text-center text-brand-800">
              <Gauge className="mx-auto size-8" />
              <p className="mt-3 text-sm font-bold">Match Score</p>
              <p className="mt-1 text-5xl font-bold tracking-tight">{match.match_score}</p>
              <p className="mt-3 rounded-md bg-white px-3 py-2 text-sm font-bold capitalize text-slate-800">
                Readiness: {readinessLabel(match.application_readiness)}
              </p>
            </div>
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-slate-950">AI job match result</h2>
              <p className="mt-3 text-sm leading-6 text-slate-600">{match.summary}</p>
              <div className="mt-6 grid gap-5 md:grid-cols-2">
                <section>
                  <h3 className="mb-3 text-sm font-bold text-slate-950">Matched Skills</h3>
                  <SkillList items={match.matched_skills} />
                </section>
                <section>
                  <h3 className="mb-3 text-sm font-bold text-slate-950">Missing Skills</h3>
                  <SkillList items={match.missing_skills} />
                </section>
                <section>
                  <h3 className="mb-3 text-sm font-bold text-slate-950">Strengths</h3>
                  <SkillList items={match.strengths} />
                </section>
                <section>
                  <h3 className="mb-3 text-sm font-bold text-slate-950">Risks</h3>
                  <SkillList items={match.risks} />
                </section>
              </div>
              <section className="mt-6">
                <h3 className="mb-3 text-sm font-bold text-slate-950">Recommendations</h3>
                <ul className="grid gap-2">
                  {match.recommendations.map((recommendation) => (
                    <li key={recommendation} className="rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-700">
                      {recommendation}
                    </li>
                  ))}
                </ul>
              </section>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
