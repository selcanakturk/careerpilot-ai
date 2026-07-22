import type { CVOptimizerProvider } from '../types/cvOptimizer';
import type { ExternalJobPosting } from '../types/job';

const JOB_SOURCE_METADATA_PREFIX = 'careerpilot:job-source-metadata:';

export type JobSourceMetadata = {
  externalId: string;
  provider: CVOptimizerProvider;
};

type SaveJobSourceMetadataInput = {
  userId: string;
  jobPostingId: string;
  externalJob: ExternalJobPosting;
};

function getStorageKey(userId: string, jobPostingId: string) {
  return `${JOB_SOURCE_METADATA_PREFIX}${userId}:${jobPostingId}`;
}

function isProvider(value: unknown): value is CVOptimizerProvider {
  return value === 'jsearch' || value === 'jooble' || value === 'adzuna';
}

export function saveJobSourceMetadata({ userId, jobPostingId, externalJob }: SaveJobSourceMetadataInput) {
  const metadata: JobSourceMetadata = {
    externalId: externalJob.external_id,
    provider: externalJob.source,
  };

  localStorage.setItem(getStorageKey(userId, jobPostingId), JSON.stringify(metadata));
}

export function getJobSourceMetadata(userId: string, jobPostingId: string): JobSourceMetadata | null {
  const rawValue = localStorage.getItem(getStorageKey(userId, jobPostingId));

  if (!rawValue) {
    return null;
  }

  try {
    const parsedValue = JSON.parse(rawValue) as Partial<JobSourceMetadata>;

    if (
      typeof parsedValue.externalId === 'string' &&
      parsedValue.externalId.trim() &&
      isProvider(parsedValue.provider)
    ) {
      return {
        externalId: parsedValue.externalId,
        provider: parsedValue.provider,
      };
    }
  } catch {
    return null;
  }

  return null;
}
