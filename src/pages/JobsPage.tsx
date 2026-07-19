import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { BrainCircuit, BriefcaseBusiness, Check, ExternalLink, Plus, Search } from 'lucide-react';
import { Link } from 'react-router-dom';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import Input from '../components/ui/Input';
import Textarea from '../components/ui/Textarea';
import { useAuth } from '../hooks/useAuth';
import { createJobPosting, discoverJobs, listCompletedAnalyses, listJobPostings } from '../services/jobService';
import type {
  CompletedAnalysisOption,
  CreateJobPostingInput,
  EmploymentType,
  ExternalJobPosting,
  JobSearchCareerProfile,
  JobPosting,
  WorkMode,
} from '../types/job';

const RESULTS_PER_PAGE = 10;
const SELECTED_ANALYSIS_STORAGE_PREFIX = 'careerpilot:selected-analysis:';

const employmentTypeOptions: Array<{ label: string; value: EmploymentType }> = [
  { label: 'Full-time', value: 'full_time' },
  { label: 'Part-time', value: 'part_time' },
  { label: 'Internship', value: 'internship' },
  { label: 'Contract', value: 'contract' },
  { label: 'Freelance', value: 'freelance' },
];

const workModeOptions: Array<{ label: string; value: WorkMode }> = [
  { label: 'Onsite', value: 'onsite' },
  { label: 'Hybrid', value: 'hybrid' },
  { label: 'Remote', value: 'remote' },
];

const initialForm: CreateJobPostingInput = {
  title: '',
  company_name: '',
  location: '',
  employment_type: null,
  work_mode: null,
  source_url: '',
  description: '',
};

type RecommendationContext = {
  profileUsed: boolean;
  analysisId: string | null;
  resolvedQuery: string | null;
  resolvedLocation: string | null;
  careerProfile: JobSearchCareerProfile | null;
};

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

function formatOption(value: string | null) {
  return value ? value.replace(/_/g, ' ') : 'Not specified';
}

function formatExperienceLevel(value: string | null) {
  if (!value) {
    return 'Not specified';
  }

  const normalizedValue = value.trim().toLowerCase().replace(/-/g, '_');
  const labels: Record<string, string> = {
    entry: 'Entry Level',
    entry_level: 'Entry Level',
    junior: 'Junior',
    mid: 'Mid-level',
    mid_level: 'Mid-level',
    senior: 'Senior',
    lead: 'Lead',
    principal: 'Principal',
  };

  if (labels[normalizedValue]) {
    return labels[normalizedValue];
  }

  return normalizedValue
    .split('_')
    .filter(Boolean)
    .map((word) => `${word.charAt(0).toUpperCase()}${word.slice(1)}`)
    .join(' ');
}

function formatSalary(job: ExternalJobPosting) {
  if (job.salary_min === null && job.salary_max === null) {
    return null;
  }

  const currency = job.salary_currency ?? '';
  const min = job.salary_min ? `${currency}${Math.round(job.salary_min).toLocaleString()}` : null;
  const max = job.salary_max ? `${currency}${Math.round(job.salary_max).toLocaleString()}` : null;

  return [min, max].filter(Boolean).join(' - ');
}

function getDescriptionPreview(description: string) {
  const normalizedDescription = description.replace(/\s+/g, ' ').trim();
  return normalizedDescription.length > 220
    ? `${normalizedDescription.slice(0, 220)}...`
    : normalizedDescription;
}

function mapExternalJobToInput(job: ExternalJobPosting): CreateJobPostingInput {
  return {
    title: job.title,
    company_name: job.company_name,
    location: job.location,
    employment_type: job.employment_type,
    work_mode: job.work_mode,
    source_url: job.source_url,
    description: job.description,
  };
}

export default function JobsPage() {
  const { user } = useAuth();
  const [jobs, setJobs] = useState<JobPosting[]>([]);
  const [recommendedJobs, setRecommendedJobs] = useState<ExternalJobPosting[]>([]);
  const [analysisOptions, setAnalysisOptions] = useState<CompletedAnalysisOption[]>([]);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState('');
  const [form, setForm] = useState<CreateJobPostingInput>(initialForm);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isLoadingSavedJobs, setIsLoadingSavedJobs] = useState(true);
  const [isLoadingAnalyses, setIsLoadingAnalyses] = useState(true);
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [savingExternalId, setSavingExternalId] = useState<string | null>(null);
  const [savedJobsError, setSavedJobsError] = useState('');
  const [analysisOptionsError, setAnalysisOptionsError] = useState('');
  const [discoveryError, setDiscoveryError] = useState('');
  const [providerUnavailable, setProviderUnavailable] = useState(false);
  const [formError, setFormError] = useState('');
  const [saveMessage, setSaveMessage] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchLocation, setSearchLocation] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalResults, setTotalResults] = useState<number | null>(null);
  const [recommendationContext, setRecommendationContext] = useState<RecommendationContext>({
    profileUsed: false,
    analysisId: null,
    resolvedQuery: null,
    resolvedLocation: null,
    careerProfile: null,
  });

  const runDiscovery = async (
    page: number,
    query = searchQuery,
    location = searchLocation,
    analysisId = selectedAnalysisId,
  ) => {
    setIsDiscovering(true);
    setDiscoveryError('');
    setProviderUnavailable(false);

    const trimmedQuery = query.trim();
    const trimmedLocation = location.trim();

    try {
      const result = await discoverJobs({
        query: trimmedQuery,
        location: trimmedLocation,
        analysisId,
        page,
        resultsPerPage: RESULTS_PER_PAGE,
      });
      setRecommendedJobs(result.jobs);
      setCurrentPage(result.page);
      setTotalResults(result.total_results);
      setProviderUnavailable(result.provider_unavailable === true);
      setRecommendationContext({
        profileUsed: result.profile_used === true,
        analysisId: result.analysis_id ?? null,
        resolvedQuery: result.resolved_query ?? result.query,
        resolvedLocation: result.resolved_location ?? result.location,
        careerProfile: result.career_profile ?? null,
      });
    } catch (discoverError) {
      setRecommendedJobs([]);
      setProviderUnavailable(false);
      setRecommendationContext({
        profileUsed: false,
        analysisId: null,
        resolvedQuery: null,
        resolvedLocation: null,
        careerProfile: null,
      });
      setDiscoveryError(
        discoverError instanceof Error
          ? discoverError.message
          : 'We could not load job recommendations right now.',
      );
    } finally {
      setIsDiscovering(false);
    }
  };

  useEffect(() => {
    let isMounted = true;

    const loadJobs = async () => {
      setIsLoadingSavedJobs(true);
      setIsLoadingAnalyses(true);
      setSavedJobsError('');
      setAnalysisOptionsError('');

      const [savedJobsResult, completedAnalysesResult] = await Promise.allSettled([
        listJobPostings(),
        listCompletedAnalyses(),
      ]);

      if (isMounted) {
        if (savedJobsResult.status === 'fulfilled') {
          setJobs(savedJobsResult.value);
        } else {
          setSavedJobsError('Unable to load saved jobs.');
        }

        if (completedAnalysesResult.status === 'fulfilled') {
          const completedAnalyses = completedAnalysesResult.value;
          setAnalysisOptions(completedAnalyses);

          const storageKey = user?.id ? `${SELECTED_ANALYSIS_STORAGE_PREFIX}${user.id}` : '';
          const storedAnalysisId = storageKey ? localStorage.getItem(storageKey) : null;
          const nextSelectedAnalysisId =
            completedAnalyses.find((analysis) => analysis.analysis_id === storedAnalysisId)?.analysis_id ??
            completedAnalyses[0]?.analysis_id ??
            '';

          setSelectedAnalysisId(nextSelectedAnalysisId);
          void runDiscovery(1, '', '', nextSelectedAnalysisId);
        } else {
          setAnalysisOptionsError('Unable to load completed CV analyses.');
          void runDiscovery(1, '', '', '');
        }
      }

      if (isMounted) {
        setIsLoadingSavedJobs(false);
        setIsLoadingAnalyses(false);
      }
    };

    void loadJobs();

    return () => {
      isMounted = false;
    };
    // Initial discovery intentionally uses backend career context when available.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  const handleSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmedQuery = searchQuery.trim();
    const trimmedLocation = searchLocation.trim();

    setSearchQuery(trimmedQuery);
    setSearchLocation(trimmedLocation);
    void runDiscovery(1, trimmedQuery, trimmedLocation, selectedAnalysisId);
  };

  const handleSelectedAnalysisChange = (analysisId: string) => {
    setSelectedAnalysisId(analysisId);

    if (user?.id) {
      localStorage.setItem(`${SELECTED_ANALYSIS_STORAGE_PREFIX}${user.id}`, analysisId);
    }

    void runDiscovery(1, searchQuery, searchLocation, analysisId);
  };

  const handleSaveExternalJob = async (job: ExternalJobPosting) => {
    const existingJob = jobs.find((savedJob) => savedJob.source_url === job.source_url);

    if (existingJob) {
      setSaveMessage('Job saved.');
      return;
    }

    setSavingExternalId(job.external_id);
    setSaveMessage('');

    try {
      const savedJob = await createJobPosting(mapExternalJobToInput(job));
      setJobs((currentJobs) => [savedJob, ...currentJobs]);
      setSaveMessage('Job saved.');
    } catch (saveError) {
      setSaveMessage(saveError instanceof Error ? saveError.message : 'Unable to save job posting.');
    } finally {
      setSavingExternalId(null);
    }
  };

  const handleSubmitManualJob = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!form.title.trim() || !form.company_name.trim() || !form.description.trim()) {
      setFormError('Job title, company, and description are required.');
      return;
    }

    setIsSaving(true);
    setFormError('');

    try {
      const savedJob = await createJobPosting(form);
      setJobs((currentJobs) => [savedJob, ...currentJobs]);
      setForm(initialForm);
      setIsFormOpen(false);
    } catch (saveError) {
      setFormError(saveError instanceof Error ? saveError.message : 'Unable to save job posting.');
    } finally {
      setIsSaving(false);
    }
  };

  const canGoNext = totalResults !== null
    ? currentPage * RESULTS_PER_PAGE < totalResults
    : recommendedJobs.length === RESULTS_PER_PAGE;
  const careerProfile = recommendationContext.careerProfile;
  const topSkills = careerProfile?.skills.slice(0, 5) ?? [];
  const showCareerProfile = recommendationContext.profileUsed && careerProfile !== null;

  return (
    <div className="space-y-7">
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
        <div>
          <p className="text-sm font-semibold text-brand-700">Job Center</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950">Jobs For You</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Personalized opportunities based on your latest CV analysis, with manual search controls when you
            want to refine the results.
          </p>
        </div>
      </section>

      <Card className="p-6">
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(280px,420px)] lg:items-end">
          <div>
            <p className="text-sm font-bold text-brand-700">Using CV</p>
            <h2 className="mt-1 text-xl font-bold tracking-tight text-slate-950">Select the CV analysis for jobs</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Recommendations and match scores are based on this CV.
            </p>
            {analysisOptionsError && (
              <p className="mt-2 text-sm font-semibold text-rose-700">{analysisOptionsError}</p>
            )}
          </div>
          <label className="block text-sm font-medium text-slate-700">
            <span className="mb-2 block">Completed CV analysis</span>
            <select
              className="min-h-11 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition hover:border-slate-300 focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
              value={selectedAnalysisId}
              onChange={(event) => handleSelectedAnalysisChange(event.target.value)}
              disabled={isLoadingAnalyses || isDiscovering || analysisOptions.length === 0}
            >
              {analysisOptions.length === 0 ? (
                <option value="">
                  {isLoadingAnalyses ? 'Loading completed analyses...' : 'No completed analyses available'}
                </option>
              ) : (
                analysisOptions.map((analysis) => (
                  <option key={analysis.analysis_id} value={analysis.analysis_id}>
                    {formatAnalysisOption(analysis)}
                  </option>
                ))
              )}
            </select>
          </label>
        </div>
      </Card>

      {showCareerProfile && (
        <Card className="p-6">
          <div className="flex flex-col gap-6">
            <div className="flex items-start gap-3">
              <div className="flex size-11 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700 ring-1 ring-brand-100">
                <BrainCircuit className="size-5" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm font-bold text-brand-700">Your Career Profile</p>
                <h2 className="mt-1 text-xl font-bold tracking-tight text-slate-950">
                  Built from your latest CV analysis
                </h2>
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-md border border-slate-100 bg-slate-50 px-4 py-3">
                <p className="text-xs font-bold uppercase text-slate-400">Primary Role</p>
                <p className="mt-1 text-sm font-semibold text-slate-900">
                  {careerProfile.primary_role}
                </p>
              </div>
              <div className="rounded-md border border-slate-100 bg-slate-50 px-4 py-3">
                <p className="text-xs font-bold uppercase text-slate-400">Experience Level</p>
                <p className="mt-1 text-sm font-semibold text-slate-900">
                  {formatExperienceLevel(careerProfile.experience_level)}
                </p>
              </div>
              {careerProfile.overall_score !== null && (
                <div className="rounded-md border border-slate-100 bg-slate-50 px-4 py-3">
                  <p className="text-xs font-bold uppercase text-slate-400">Overall CV Score</p>
                  <p className="mt-1 text-sm font-semibold text-slate-900">{careerProfile.overall_score}%</p>
                </div>
              )}
              <div className="rounded-md border border-slate-100 bg-slate-50 px-4 py-3">
                <p className="text-xs font-bold uppercase text-slate-400">Location</p>
                <p className="mt-1 text-sm font-semibold text-slate-900">
                  {recommendationContext.resolvedLocation ?? 'Not specified'}
                </p>
              </div>
            </div>
            <div className="rounded-md border border-slate-100 bg-slate-50 px-4 py-3">
              <p className="text-xs font-bold uppercase text-slate-400">Top Skills</p>
              {topSkills.length > 0 ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {topSkills.map((skill) => (
                    <span
                      key={skill}
                      className="rounded-md bg-white px-2.5 py-1 text-xs font-bold text-slate-700 ring-1 ring-slate-200"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="mt-2 text-sm text-slate-600">
                  Skills will appear after a more detailed CV analysis.
                </p>
              )}
            </div>
          </div>
        </Card>
      )}

      <Card className="p-6">
        <div className="mb-5">
          <p className="text-sm font-bold text-brand-700">Refine Search</p>
          <h2 className="mt-1 text-xl font-bold tracking-tight text-slate-950">Adjust role or location</h2>
          <p className="mt-1 text-sm text-slate-500">
            Override your AI recommendations with a specific role or location when needed.
          </p>
        </div>
        <form className="grid gap-4 lg:grid-cols-[1fr_1fr_auto]" onSubmit={handleSearch}>
          <Input
            label="Role"
            placeholder="Product Manager"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
          <Input
            label="Location"
            placeholder="Istanbul, Ankara, Izmir, Remote..."
            value={searchLocation}
            onChange={(event) => setSearchLocation(event.target.value)}
          />
          <div className="flex items-end">
            <Button type="submit" disabled={isDiscovering} className="w-full">
              <Search className="size-4" />
              {isDiscovering ? 'Finding jobs...' : 'Search Jobs'}
            </Button>
          </div>
        </form>
      </Card>

      <section>
        <div className="mb-4 flex flex-col justify-between gap-2 md:flex-row md:items-end">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-950">Recommended jobs</h2>
            <p className="mt-1 text-sm text-slate-500">
              Results come from current external job listings. Save a job before running AI match analysis.
            </p>
          </div>
          {totalResults !== null && (
            <p className="text-sm font-semibold text-slate-500">{totalResults.toLocaleString()} results</p>
          )}
        </div>

        {isDiscovering ? (
          <Card className="p-8 text-center">
            <div className="mx-auto size-10 animate-pulse rounded-full bg-brand-100" />
            <p className="mt-4 text-sm font-semibold text-slate-600">Finding opportunities for you...</p>
          </Card>
        ) : discoveryError ? (
          <Card className="p-6 text-sm text-rose-700">{discoveryError}</Card>
        ) : providerUnavailable ? (
          <Card className="border-amber-200 bg-amber-50 p-8 text-center">
            <BriefcaseBusiness className="mx-auto size-10 text-amber-700" />
            <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">
              Job listings are temporarily unavailable.
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-700">
              Please try again shortly.
            </p>
          </Card>
        ) : recommendedJobs.length === 0 ? (
          <Card className="p-8 text-center">
            <BriefcaseBusiness className="mx-auto size-10 text-brand-700" />
            <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">
              No matching jobs were found.
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
              Try another role or location.
            </p>
          </Card>
        ) : (
          <div className="grid gap-4">
            {recommendedJobs.map((job) => {
              const salary = formatSalary(job);
              const isSaved = jobs.some((savedJob) => savedJob.source_url === job.source_url);
              const matchedSkills = job.matched_skills?.slice(0, 3) ?? [];
              const missingSkills = job.missing_skills?.slice(0, 3) ?? [];
              const matchReasons = job.match_reasons?.slice(0, 3) ?? [];

              return (
                <Card key={job.external_id} className="p-5">
                  <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-xl font-bold tracking-tight text-slate-950">{job.title}</h3>
                        <span className="rounded-md bg-slate-50 px-2.5 py-1 text-xs font-bold uppercase text-slate-600 ring-1 ring-slate-100">
                          {job.source}
                        </span>
                        {job.match_score !== null && job.match_score !== undefined && (
                          <span className="rounded-md bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700 ring-1 ring-emerald-100">
                            {job.match_score}% Match
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-sm font-semibold text-slate-700">{job.company_name}</p>
                      <p className="mt-2 text-sm text-slate-500">
                        {job.location || 'Location not specified'} · {formatOption(job.work_mode)} ·{' '}
                        {formatOption(job.employment_type)}
                      </p>
                      <div className="mt-2 flex flex-wrap gap-2 text-xs font-semibold text-slate-400">
                        <span>Posted {formatDate(job.created_at)}</span>
                        {salary && <span>{salary}</span>}
                      </div>
                      <p className="mt-3 max-w-4xl text-sm leading-6 text-slate-600">
                        {getDescriptionPreview(job.description)}
                      </p>
                      {matchReasons.length > 0 && (
                        <div className="mt-4 rounded-md border border-emerald-100 bg-emerald-50/60 p-3">
                          <p className="text-xs font-bold uppercase tracking-wide text-emerald-800">
                            Why this job?
                          </p>
                          <ul className="mt-2 space-y-1.5">
                            {matchReasons.map((reason) => (
                              <li key={reason} className="flex gap-2 text-xs leading-5 text-emerald-900">
                                <Check className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
                                <span>{reason}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {(matchedSkills.length > 0 || missingSkills.length > 0) && (
                        <div className="mt-3 grid gap-2 text-xs text-slate-500 sm:grid-cols-2">
                          {matchedSkills.length > 0 && (
                            <p>
                              <span className="font-bold text-slate-700">Matched:</span>{' '}
                              {matchedSkills.join(' · ')}
                            </p>
                          )}
                          {missingSkills.length > 0 && (
                            <p>
                              <span className="font-bold text-slate-700">Missing:</span>{' '}
                              {missingSkills.join(' · ')}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="flex shrink-0 flex-col gap-2 sm:flex-row lg:flex-col">
                      <a href={job.source_url} target="_blank" rel="noopener noreferrer">
                        <Button variant="secondary" className="w-full">
                          View Job
                          <ExternalLink className="size-4" />
                        </Button>
                      </a>
                      <Button
                        disabled={savingExternalId === job.external_id || isSaved}
                        onClick={() => void handleSaveExternalJob(job)}
                        className="w-full"
                      >
                        {isSaved ? 'Saved' : savingExternalId === job.external_id ? 'Saving...' : 'Save Job'}
                      </Button>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}

        {saveMessage && (
          <div role="status" className="mt-4 rounded-md border border-brand-100 bg-brand-50 px-4 py-3 text-sm text-brand-700">
            {saveMessage}
          </div>
        )}

        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:justify-end">
          <Button
            variant="secondary"
            disabled={currentPage <= 1 || isDiscovering}
            onClick={() => void runDiscovery(currentPage - 1)}
          >
            Previous
          </Button>
          <Button
            variant="secondary"
            disabled={!canGoNext || isDiscovering}
            onClick={() => void runDiscovery(currentPage + 1)}
          >
            Next
          </Button>
        </div>
      </section>

      <Card className="p-6">
        <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
          <div>
            <p className="text-sm font-bold text-brand-700">Analyze a Job Manually</p>
            <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">Paste any job posting</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
              Found a job on LinkedIn, Kariyer.net, Indeed, or a company career page? Paste it here to compare
              it with your CV.
            </p>
          </div>
          <Button onClick={() => setIsFormOpen((isOpen) => !isOpen)} variant="secondary" className="w-full md:w-auto">
            <Plus className="size-4" />
            Add Job Manually
          </Button>
        </div>

        {isFormOpen && (
          <form className="mt-6 grid gap-4 border-t border-slate-100 pt-6" onSubmit={handleSubmitManualJob}>
            <div className="grid gap-4 md:grid-cols-2">
              <Input
                label="Job title"
                value={form.title}
                onChange={(event) => setForm({ ...form, title: event.target.value })}
                required
              />
              <Input
                label="Company"
                value={form.company_name}
                onChange={(event) => setForm({ ...form, company_name: event.target.value })}
                required
              />
              <Input
                label="Location"
                value={form.location ?? ''}
                onChange={(event) => setForm({ ...form, location: event.target.value })}
              />
              <Input
                label="Source URL"
                value={form.source_url ?? ''}
                onChange={(event) => setForm({ ...form, source_url: event.target.value })}
              />
              <label className="block text-sm font-medium text-slate-700">
                <span className="mb-2 block">Employment type</span>
                <select
                  className="min-h-11 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition hover:border-slate-300 focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
                  value={form.employment_type ?? ''}
                  onChange={(event) =>
                    setForm({ ...form, employment_type: (event.target.value || null) as EmploymentType | null })
                  }
                >
                  <option value="">Not specified</option>
                  {employmentTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm font-medium text-slate-700">
                <span className="mb-2 block">Work mode</span>
                <select
                  className="min-h-11 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition hover:border-slate-300 focus:border-brand-500 focus:ring-4 focus:ring-brand-100"
                  value={form.work_mode ?? ''}
                  onChange={(event) =>
                    setForm({ ...form, work_mode: (event.target.value || null) as WorkMode | null })
                  }
                >
                  <option value="">Not specified</option>
                  {workModeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <Textarea
              label="Job description"
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
              required
              rows={8}
            />
            {formError && (
              <div role="alert" className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {formError}
              </div>
            )}
            <div className="flex flex-col gap-3 sm:flex-row">
              <Button type="submit" disabled={isSaving}>
                {isSaving ? 'Saving job...' : 'Save Job'}
              </Button>
              <Button type="button" variant="secondary" onClick={() => setIsFormOpen(false)}>
                Cancel
              </Button>
            </div>
          </form>
        )}
      </Card>

      <section>
        <h2 className="mb-4 text-xl font-bold tracking-tight text-slate-950">Saved Jobs</h2>
        {isLoadingSavedJobs ? (
          <Card className="p-8 text-center">
            <div className="mx-auto size-10 animate-pulse rounded-full bg-brand-100" />
            <p className="mt-4 text-sm font-semibold text-slate-600">Loading saved jobs...</p>
          </Card>
        ) : savedJobsError ? (
          <Card className="p-6 text-sm text-rose-700">{savedJobsError}</Card>
        ) : jobs.length === 0 ? (
          <Card className="p-8 text-center">
            <BriefcaseBusiness className="mx-auto size-10 text-brand-700" />
            <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">No saved jobs yet.</h2>
            <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
              Save a recommended job or add one manually to compare it with your CV.
            </p>
          </Card>
        ) : (
          <div className="grid gap-4">
            {jobs.map((job) => (
              <Card key={job.id} className="p-5">
                <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-xl font-bold tracking-tight text-slate-950">{job.title}</h3>
                      <span className="rounded-md bg-brand-50 px-2.5 py-1 text-xs font-bold capitalize text-brand-700">
                        {job.status}
                      </span>
                    </div>
                    <p className="mt-1 text-sm font-semibold text-slate-700">{job.company_name}</p>
                    <p className="mt-2 text-sm text-slate-500">
                      {job.location || 'Location not specified'} · {formatOption(job.work_mode)} ·{' '}
                      {formatOption(job.employment_type)}
                    </p>
                    <p className="mt-2 text-xs font-semibold text-slate-400">Saved {formatDate(job.created_at)}</p>
                  </div>
                  <Link to={`/jobs/${job.id}`} className="shrink-0">
                    <Button variant="secondary" className="w-full md:w-auto">
                      View details
                      <ExternalLink className="size-4" />
                    </Button>
                  </Link>
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
