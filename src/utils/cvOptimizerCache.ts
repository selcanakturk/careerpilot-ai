import type { CVOptimizeResponse } from '../types/cvOptimizer';

const CV_OPTIMIZER_CACHE_PREFIX = 'careerpilot:cv-optimizer-result:';

type CacheIdentity = {
  userId: string;
  jobPostingId: string;
  analysisId: string;
};

function getStorageKey({ userId, jobPostingId, analysisId }: CacheIdentity) {
  return `${CV_OPTIMIZER_CACHE_PREFIX}${userId}:${jobPostingId}:${analysisId}`;
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string');
}

function isCVOptimizeResponse(value: unknown): value is CVOptimizeResponse {
  if (typeof value !== 'object' || value === null) {
    return false;
  }

  const candidate = value as Partial<CVOptimizeResponse>;

  return (
    typeof candidate.analysis_id === 'string' &&
    typeof candidate.job_external_id === 'string' &&
    (candidate.provider === 'jsearch' || candidate.provider === 'jooble' || candidate.provider === 'adzuna') &&
    typeof candidate.match_before === 'number' &&
    typeof candidate.estimated_match_after === 'number' &&
    isStringArray(candidate.changes) &&
    typeof candidate.optimized_cv === 'object' &&
    candidate.optimized_cv !== null &&
    !Array.isArray(candidate.optimized_cv)
  );
}

export function getCachedCVOptimizerResult(identity: CacheIdentity): CVOptimizeResponse | null {
  const storageKey = getStorageKey(identity);
  const rawValue = localStorage.getItem(storageKey);

  if (!rawValue) {
    return null;
  }

  try {
    const parsedValue = JSON.parse(rawValue) as unknown;

    if (isCVOptimizeResponse(parsedValue)) {
      return parsedValue;
    }
  } catch {
    localStorage.removeItem(storageKey);
    return null;
  }

  localStorage.removeItem(storageKey);
  return null;
}

export function saveCachedCVOptimizerResult(identity: CacheIdentity, result: CVOptimizeResponse) {
  localStorage.setItem(getStorageKey(identity), JSON.stringify(result));
}
