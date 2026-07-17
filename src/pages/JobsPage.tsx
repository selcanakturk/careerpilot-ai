import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { BriefcaseBusiness, ExternalLink, Plus, Search } from 'lucide-react';
import { Link } from 'react-router-dom';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import Input from '../components/ui/Input';
import Textarea from '../components/ui/Textarea';
import { createJobPosting, discoverJobs, listJobPostings } from '../services/jobService';
import type {
  CreateJobPostingInput,
  EmploymentType,
  ExternalJobPosting,
  JobPosting,
  WorkMode,
} from '../types/job';

const RESULTS_PER_PAGE = 10;

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

function formatOption(value: string | null) {
  return value ? value.replace(/_/g, ' ') : 'Not specified';
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
  const [jobs, setJobs] = useState<JobPosting[]>([]);
  const [recommendedJobs, setRecommendedJobs] = useState<ExternalJobPosting[]>([]);
  const [form, setForm] = useState<CreateJobPostingInput>(initialForm);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isLoadingSavedJobs, setIsLoadingSavedJobs] = useState(true);
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [savingExternalId, setSavingExternalId] = useState<string | null>(null);
  const [savedJobsError, setSavedJobsError] = useState('');
  const [discoveryError, setDiscoveryError] = useState('');
  const [formError, setFormError] = useState('');
  const [saveMessage, setSaveMessage] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchLocation, setSearchLocation] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalResults, setTotalResults] = useState<number | null>(null);

  const runDiscovery = async (page: number, query = searchQuery, location = searchLocation) => {
    setIsDiscovering(true);
    setDiscoveryError('');

    try {
      const result = await discoverJobs({
        query,
        location,
        page,
        resultsPerPage: RESULTS_PER_PAGE,
      });
      setRecommendedJobs(result.jobs);
      setCurrentPage(result.page);
      setTotalResults(result.total_results);
    } catch (discoverError) {
      setRecommendedJobs([]);
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
      setSavedJobsError('');

      try {
        const savedJobs = await listJobPostings();

        if (isMounted) {
          setJobs(savedJobs);
        }
      } catch {
        if (isMounted) {
          setSavedJobsError('Unable to load saved jobs.');
        }
      } finally {
        if (isMounted) {
          setIsLoadingSavedJobs(false);
        }
      }
    };

    void loadJobs();
    void runDiscovery(1, '', '');

    return () => {
      isMounted = false;
    };
    // Initial discovery intentionally uses backend career context when available.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void runDiscovery(1);
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

  return (
    <div className="space-y-7">
      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-soft">
        <div>
          <p className="text-sm font-semibold text-brand-700">Job Center</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-950">Jobs For You</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Discover current opportunities in Türkiye based on your CV, target role, and career roadmap.
          </p>
        </div>
      </section>

      <Card className="p-6">
        <form className="grid gap-4 lg:grid-cols-[1fr_1fr_auto]" onSubmit={handleSearch}>
          <Input
            label="Role / keywords"
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
            <p className="mt-4 text-sm font-semibold text-slate-600">Finding jobs for you...</p>
          </Card>
        ) : discoveryError ? (
          <Card className="p-6 text-sm text-rose-700">{discoveryError}</Card>
        ) : recommendedJobs.length === 0 ? (
          <Card className="p-8 text-center">
            <BriefcaseBusiness className="mx-auto size-10 text-brand-700" />
            <h2 className="mt-4 text-2xl font-bold tracking-tight text-slate-950">
              No matching jobs were found.
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">
              Try broadening your role or location filters.
            </p>
          </Card>
        ) : (
          <div className="grid gap-4">
            {recommendedJobs.map((job) => {
              const salary = formatSalary(job);
              const isSaved = jobs.some((savedJob) => savedJob.source_url === job.source_url);

              return (
                <Card key={job.external_id} className="p-5">
                  <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-xl font-bold tracking-tight text-slate-950">{job.title}</h3>
                        <span className="rounded-md bg-slate-50 px-2.5 py-1 text-xs font-bold uppercase text-slate-600 ring-1 ring-slate-100">
                          {job.source}
                        </span>
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
