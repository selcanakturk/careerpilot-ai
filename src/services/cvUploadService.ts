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
