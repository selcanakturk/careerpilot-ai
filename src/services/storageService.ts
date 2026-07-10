import type { FileObject } from '@supabase/storage-js';
import { supabase } from '../lib/supabase';

export const CV_STORAGE_BUCKET = 'cv-files';

export type UploadedCVInfo = {
  path: string;
  fullPath: string;
  bucket: typeof CV_STORAGE_BUCKET;
  size: number;
  mimeType: string;
};

export type StoredFileInfo = {
  path: string;
  bucket: typeof CV_STORAGE_BUCKET;
  name: string;
  size: number | null;
  mimeType: string | null;
  createdAt: string | null;
  updatedAt: string | null;
  metadata: FileObject['metadata'];
};

function createStorageError(action: string, message?: string) {
  return new Error(`Supabase Storage ${action} failed${message ? `: ${message}` : '.'}`);
}

function formatTimestamp(date = new Date()) {
  const pad = (value: number) => String(value).padStart(2, '0');

  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
    '-',
    pad(date.getHours()),
    pad(date.getMinutes()),
    pad(date.getSeconds()),
  ].join('');
}

function sanitizeFileName(fileName: string) {
  const fallbackName = 'cv.pdf';
  const normalizedName = fileName.trim().toLowerCase() || fallbackName;

  return normalizedName
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9._-]/g, '')
    .replace(/-+/g, '-')
    .replace(/^[-.]+|[-.]+$/g, '') || fallbackName;
}

function buildCVPath(file: File, userId: string) {
  const safeUserId = userId.trim();

  if (!safeUserId) {
    throw new Error('A valid userId is required to upload a CV.');
  }

  return `${safeUserId}/${formatTimestamp()}-${sanitizeFileName(file.name)}`;
}

function splitStoragePath(path: string) {
  const normalizedPath = path.trim().replace(/^\/+|\/+$/g, '');
  const lastSlashIndex = normalizedPath.lastIndexOf('/');

  if (!normalizedPath || lastSlashIndex === -1) {
    throw new Error('A valid storage path with a folder and file name is required.');
  }

  return {
    folderPath: normalizedPath.slice(0, lastSlashIndex),
    fileName: normalizedPath.slice(lastSlashIndex + 1),
    normalizedPath,
  };
}

export async function uploadCV(file: File, userId: string): Promise<UploadedCVInfo> {
  const path = buildCVPath(file, userId);
  const { data, error } = await supabase.storage.from(CV_STORAGE_BUCKET).upload(path, file, {
    cacheControl: '3600',
    contentType: file.type || 'application/octet-stream',
    upsert: false,
  });

  if (error || !data) {
    throw createStorageError('upload', error?.message);
  }

  return {
    path: data.path,
    fullPath: data.fullPath,
    bucket: CV_STORAGE_BUCKET,
    size: file.size,
    mimeType: file.type || 'application/octet-stream',
  };
}

export async function deleteCV(path: string): Promise<void> {
  const normalizedPath = path.trim().replace(/^\/+|\/+$/g, '');

  if (!normalizedPath) {
    throw new Error('A valid storage path is required to delete a CV.');
  }

  const { error } = await supabase.storage.from(CV_STORAGE_BUCKET).remove([normalizedPath]);

  if (error) {
    throw createStorageError('delete', error.message);
  }
}

export async function getFileInfo(path: string): Promise<StoredFileInfo> {
  const { folderPath, fileName, normalizedPath } = splitStoragePath(path);
  const { data, error } = await supabase.storage.from(CV_STORAGE_BUCKET).list(folderPath, {
    limit: 1,
    search: fileName,
  });

  if (error) {
    throw createStorageError('file lookup', error.message);
  }

  const fileInfo = data?.find((item) => item.name === fileName);

  if (!fileInfo) {
    throw new Error(`CV file not found in Supabase Storage: ${normalizedPath}`);
  }

  return {
    path: normalizedPath,
    bucket: CV_STORAGE_BUCKET,
    name: fileInfo.name,
    size: typeof fileInfo.metadata?.size === 'number' ? fileInfo.metadata.size : null,
    mimeType:
      typeof fileInfo.metadata?.mimetype === 'string' ? fileInfo.metadata.mimetype : null,
    createdAt: fileInfo.created_at,
    updatedAt: fileInfo.updated_at,
    metadata: fileInfo.metadata,
  };
}
