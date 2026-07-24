import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, ExternalLink, Gauge, Loader2, MessageCircle, Sparkles, Trash2 } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import CvOptimizerPanel from '../components/jobs/CvOptimizerPanel';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import { useAuth } from '../hooks/useAuth';
import { optimizeCVForJob } from '../services/cvOptimizerService';
import {
  deleteJobPosting,
  generateJobMatch,
  getExistingJobMatch,
  getJobPosting,
  listCompletedAnalyses,
} from '../services/jobService';
import type { CVOptimizeResponse } from '../types/cvOptimizer';
import type { CompletedAnalysisOption, JobMatch, JobPosting } from '../types/job';
import {
  getCachedCVOptimizerResult,
  removeCachedCVOptimizerResultsForJob,
  saveCachedCVOptimizerResult,
} from '../utils/cvOptimizerCache';
import { getJobSourceMetadata, removeJobSourceMetadata } from '../utils/jobSourceMetadata';

const SELECTED_ANALYSIS_STORAGE_PREFIX = 'careerpilot:selected-analysis:';

function formatOption(value: string | null) {
  return value ? value.replace(/_/g, ' ') : 'Not specified';
}

function formatDate(value: string | null) {
  if (!value) {
    return 'Date not available';
  }

  return new Intl.DateTimeFormat('en', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(value));
}

function formatAnalysisOption(option: CompletedAnalysisOption) {
  return `${option.filename} - ${option.target_role} - ${option.overall_score}% - ${formatDate(option.analyzed_at)}`;
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
  const navigate = useNavigate();
  const { user } = useAuth();
  const [job, setJob] = useState<JobPosting | null>(null);
  const [analyses, setAnalyses] = useState<CompletedAnalysisOption[]>([]);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState('');
  const [match, setMatch] = useState<JobMatch | null>(null);
  const [optimizedCV, setOptimizedCV] = useState<CVOptimizeResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [isDeletingJob, setIsDeletingJob] = useState(false);
  const [error, setError] = useState('');
  const [matchError, setMatchError] = useState('');
  const [optimizerError, setOptimizerError] = useState('');
  const [deleteError, setDeleteError] = useState('');
  const isGeneratingMatchRef = useRef(false);

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
          const storageKey = user?.id ? `${SELECTED_ANALYSIS_STORAGE_PREFIX}${user.id}` : '';
          const storedAnalysisId = storageKey ? localStorage.getItem(storageKey) : null;
          const nextSelectedAnalysisId =
            completedAnalyses.find((analysis) => analysis.analysis_id === storedAnalysisId)?.analysis_id ??
            completedAnalyses[0]?.analysis_id ??
            '';

          setSelectedAnalysisId(nextSelectedAnalysisId);
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
  }, [jobPostingId, user?.id]);

  useEffect(() => {
    let isMounted = true;

    const loadStoredResults = async () => {
      if (!job?.id || !jobPostingId || !selectedAnalysisId || !user?.id) {
        setMatch(null);
        setOptimizedCV(null);
        return;
      }

      setMatchError('');
      setOptimizerError('');
      setMatch(null);
      setOptimizedCV(
        getCachedCVOptimizerResult({
          userId: user.id,
          jobPostingId,
          analysisId: selectedAnalysisId,
        }),
      );

      try {
        const existingMatch = await getExistingJobMatch(job.id, selectedAnalysisId);

        if (isMounted) {
          setMatch(existingMatch);
        }
      } catch (loadMatchError) {
        if (isMounted) {
          setMatchError(
            loadMatchError instanceof Error ? loadMatchError.message : 'Unable to load the saved job match.',
          );
        }
      }
    };

    void loadStoredResults();

    return () => {
      isMounted = false;
    };
  }, [job?.id, jobPostingId, selectedAnalysisId, user?.id]);

  const handleGenerateMatch = async () => {
    if (!job || !selectedAnalysisId || isGeneratingMatchRef.current) {
      return;
    }

    isGeneratingMatchRef.current = true;
    setIsAnalyzing(true);
    setMatchError('');

    try {
      const generatedMatch = await generateJobMatch(job.id, selectedAnalysisId);
      setMatch(generatedMatch);
    } catch (generateError) {
      setMatchError(generateError instanceof Error ? generateError.message : 'Unable to complete the job matching request.');
    } finally {
      isGeneratingMatchRef.current = false;
      setIsAnalyzing(false);
    }
  };

  const handleOptimizeCV = async () => {
    if (!job || !jobPostingId || !selectedAnalysisId || !user?.id || isOptimizing) {
      return;
    }

    const metadata = getJobSourceMetadata(user.id, jobPostingId);

    if (!metadata) {
      setOptimizerError('Job or CV analysis could not be found.');
      return;
    }

    setIsOptimizing(true);
    setOptimizerError('');

    try {
      const result = await optimizeCVForJob({
        analysis_id: selectedAnalysisId,
        job_external_id: metadata.externalId,
        provider: metadata.provider,
      });
      saveCachedCVOptimizerResult(
        {
          userId: user.id,
          jobPostingId,
          analysisId: selectedAnalysisId,
        },
        result,
      );
      setOptimizedCV(result);
    } catch (optimizeError) {
      setOptimizerError(optimizeError instanceof Error ? optimizeError.message : 'Something went wrong.');
    } finally {
      setIsOptimizing(false);
    }
  };

  const handleDeleteJob = async () => {
    if (!jobPostingId || !user?.id || isDeletingJob) {
      return;
    }

    const confirmed = window.confirm('Are you sure you want to remove this saved job?');

    if (!confirmed) {
      return;
    }

    setIsDeletingJob(true);
    setDeleteError('');

    try {
      await deleteJobPosting(jobPostingId);
      removeJobSourceMetadata(user.id, jobPostingId);
      removeCachedCVOptimizerResultsForJob(user.id, jobPostingId);
      navigate('/jobs');
    } catch (removeError) {
      setDeleteError(removeError instanceof Error ? removeError.message : 'Something went wrong.');
    } finally {
      setIsDeletingJob(false);
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

  const copilotMetadata = user?.id && jobPostingId ? getJobSourceMetadata(user.id, jobPostingId) : null;
  const copilotPath =
    copilotMetadata && selectedAnalysisId
      ? `/career-copilot?job_external_id=${encodeURIComponent(copilotMetadata.externalId)}&provider=${
          copilotMetadata.provider
        }&job_posting_id=${encodeURIComponent(jobPostingId ?? '')}&analysis_id=${encodeURIComponent(selectedAnalysisId)}`
      : '/career-copilot';

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
          <div className="flex flex-col gap-2 sm:flex-row lg:flex-col">
            {job.source_url && (
              <a href={job.source_url} target="_blank" rel="noreferrer">
                <Button variant="secondary" className="w-full">
                  Open original posting
                  <ExternalLink className="size-4" />
                </Button>
              </a>
            )}
            <Button
              variant="secondary"
              disabled={isDeletingJob}
              onClick={() => void handleDeleteJob()}
              className="w-full"
            >
              <Trash2 className="size-4" />
              {isDeletingJob ? 'Removing...' : 'Remove from Saved Jobs'}
            </Button>
          </div>
        </div>
        {deleteError && (
          <div role="alert" className="mt-5 rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {deleteError}
          </div>
        )}
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
                onChange={(event) => {
                  const nextAnalysisId = event.target.value;
                  setSelectedAnalysisId(nextAnalysisId);

                  if (user?.id) {
                    localStorage.setItem(`${SELECTED_ANALYSIS_STORAGE_PREFIX}${user.id}`, nextAnalysisId);
                  }
                }}
              >
                {analyses.length === 0 ? (
                  <option value="">No completed analyses available</option>
                ) : (
                  analyses.map((analysis) => (
                    <option key={analysis.analysis_id} value={analysis.analysis_id}>
                      {formatAnalysisOption(analysis)}
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

      <Card className="p-6">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
          <div>
            <p className="text-sm font-bold text-brand-700">CV optimization</p>
            <h2 className="mt-2 text-xl font-bold tracking-tight text-slate-950">Tailor your CV for this job</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              Use your selected CV analysis and this job posting to generate a focused, ATS-friendly rewrite.
            </p>
          </div>
          <Button
            disabled={!selectedAnalysisId || isOptimizing}
            onClick={() => void handleOptimizeCV()}
            className="w-full lg:w-auto"
            aria-label="Optimize my CV for this job"
          >
            {isOptimizing ? (
              <>
                <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                Optimizing CV...
              </>
            ) : (
              <>
                <Sparkles className="size-4" aria-hidden="true" />
                Optimize My CV
              </>
            )}
          </Button>
          <Link to={copilotPath} className="w-full lg:w-auto">
            <Button variant="secondary" className="w-full">
              <MessageCircle className="size-4" />
              Ask Copilot
            </Button>
          </Link>
        </div>
        {optimizerError && (
          <div role="alert" className="mt-5 rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {optimizerError}
          </div>
        )}
      </Card>

      {optimizedCV && <CvOptimizerPanel result={optimizedCV} />}

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
