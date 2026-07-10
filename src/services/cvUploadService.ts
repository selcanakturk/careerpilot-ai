import { supabase } from '../lib/supabase';

export type CVUploadRecord = {
  id: string;
  user_id: string;
  file_name: string;
  file_path: string;
  file_type: string;
  file_size: number;
  target_role: string;
  experience_level: string;
  created_at: string;
};

export type CreateCVUploadInput = {
  userId: string;
  fileName: string;
  filePath: string;
  fileType: string;
  fileSize: number;
  targetRole: string;
  experienceLevel: string;
};

function createDatabaseError(message?: string) {
  return new Error(
    `Unable to save CV upload metadata${message ? `: ${message}` : '. Please try again.'}`,
  );
}

function createFetchError(message?: string) {
  return new Error(`Unable to load CV uploads${message ? `: ${message}` : '. Please try again.'}`);
}

export async function createCVUploadRecord(
  input: CreateCVUploadInput,
): Promise<CVUploadRecord> {
  const { data, error } = await supabase
    .from('cv_uploads')
    .insert({
      user_id: input.userId,
      file_name: input.fileName,
      file_path: input.filePath,
      file_type: input.fileType,
      file_size: input.fileSize,
      target_role: input.targetRole,
      experience_level: input.experienceLevel,
    })
    .select()
    .single<CVUploadRecord>();

  if (error || !data) {
    throw createDatabaseError(error?.message);
  }

  return data;
}

export async function getUserCVUploads(userId: string): Promise<CVUploadRecord[]> {
  const safeUserId = userId.trim();

  if (!safeUserId) {
    throw new Error('A valid userId is required to load CV uploads.');
  }

  const { data, error } = await supabase
    .from('cv_uploads')
    .select(
      'id,user_id,file_name,file_path,file_type,file_size,target_role,experience_level,created_at',
    )
    .eq('user_id', safeUserId)
    .order('created_at', { ascending: false })
    .returns<CVUploadRecord[]>();

  if (error) {
    throw createFetchError(error.message);
  }

  return data ?? [];
}
