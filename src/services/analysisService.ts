import { supabase } from '../lib/supabase';
import type { CVAnalysis } from '../types/analysis';
import { apiRequest } from './apiService';

const ANALYSIS_COLUMNS =
  'id,user_id,cv_upload_id,target_role,status,overall_score,summary,strengths,weaknesses,skill_gaps,cv_suggestions,created_at,updated_at';

function createAnalysisFetchError(message?: string) {
  return new Error(`Unable to load analyses${message ? `: ${message}` : '. Please try again.'}`);
}

async function getCurrentUserId() {
  const { data, error } = await supabase.auth.getSession();

  if (error || !data.session?.user.id) {
    throw new Error('Please sign in again to view your analyses.');
  }

  return data.session.user.id;
}

export async function analyzeCV(uploadId: string): Promise<CVAnalysis> {
  const safeUploadId = uploadId.trim();

  if (!safeUploadId) {
    throw new Error('A valid upload id is required to analyze a CV.');
  }

  return apiRequest<CVAnalysis>(`/api/uploads/${safeUploadId}/analyze`, {
    method: 'POST',
  });
}

export async function getAnalysisById(analysisId: string): Promise<CVAnalysis | null> {
  const safeAnalysisId = analysisId.trim();

  if (!safeAnalysisId) {
    return null;
  }

  const userId = await getCurrentUserId();
  const { data, error } = await supabase
    .from('cv_analyses')
    .select(ANALYSIS_COLUMNS)
    .eq('id', safeAnalysisId)
    .eq('user_id', userId)
    .limit(1)
    .returns<CVAnalysis[]>();

  if (error) {
    throw createAnalysisFetchError(error.message);
  }

  return data?.[0] ?? null;
}

export async function getLatestCompletedAnalysis(): Promise<CVAnalysis | null> {
  const userId = await getCurrentUserId();
  const { data, error } = await supabase
    .from('cv_analyses')
    .select(ANALYSIS_COLUMNS)
    .eq('user_id', userId)
    .eq('status', 'completed')
    .order('created_at', { ascending: false })
    .limit(1)
    .returns<CVAnalysis[]>();

  if (error) {
    throw createAnalysisFetchError(error.message);
  }

  return data?.[0] ?? null;
}

export async function getCompletedAnalysesForUploadIds(
  uploadIds: string[],
): Promise<Record<string, CVAnalysis>> {
  const safeUploadIds = uploadIds.map((id) => id.trim()).filter(Boolean);

  if (safeUploadIds.length === 0) {
    return {};
  }

  const userId = await getCurrentUserId();
  const { data, error } = await supabase
    .from('cv_analyses')
    .select(ANALYSIS_COLUMNS)
    .eq('user_id', userId)
    .eq('status', 'completed')
    .in('cv_upload_id', safeUploadIds)
    .order('created_at', { ascending: false })
    .returns<CVAnalysis[]>();

  if (error) {
    throw createAnalysisFetchError(error.message);
  }

  return (data ?? []).reduce<Record<string, CVAnalysis>>((accumulator, analysis) => {
    if (!accumulator[analysis.cv_upload_id]) {
      accumulator[analysis.cv_upload_id] = analysis;
    }

    return accumulator;
  }, {});
}
