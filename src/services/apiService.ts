import { supabase } from '../lib/supabase';

type ApiErrorBody = {
  detail?: string;
};

type ApiRequestOptions = RequestInit & {
  timeoutMs?: number;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;

if (!apiBaseUrl) {
  throw new Error(
    'Missing backend API environment variable. Please define VITE_API_BASE_URL in your local .env file.',
  );
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export class ApiAuthError extends ApiError {
  constructor(message = 'Please sign in again to continue.') {
    super(message, 401);
    this.name = 'ApiAuthError';
  }
}

async function getAccessToken() {
  const { data, error } = await supabase.auth.getSession();

  if (error) {
    throw new ApiAuthError('We could not verify your session. Please sign in again.');
  }

  const accessToken = data.session?.access_token;

  if (!accessToken) {
    throw new ApiAuthError();
  }

  return accessToken;
}

function getApiUrl(path: string) {
  const normalizedBaseUrl = apiBaseUrl.replace(/\/$/, '');
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;

  return `${normalizedBaseUrl}${normalizedPath}`;
}

async function getErrorMessage(response: Response) {
  try {
    const body = (await response.json()) as ApiErrorBody;

    if (typeof body.detail === 'string' && body.detail.trim()) {
      return body.detail;
    }
  } catch {
    // Fall through to a safe generic message.
  }

  if (response.status === 401) {
    return 'Your session has expired. Please sign in again.';
  }

  if (response.status === 404) {
    return 'The requested resource could not be found.';
  }

  if (response.status === 502) {
    return 'The AI analysis service is temporarily unavailable.';
  }

  return 'Something went wrong. Please try again.';
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const accessToken = await getAccessToken();
  const { timeoutMs, headers, signal, body, ...requestOptions } = options;
  const controller = new AbortController();
  const timeoutId = timeoutMs ? window.setTimeout(() => controller.abort(), timeoutMs) : null;

  if (signal) {
    if (signal.aborted) {
      controller.abort();
    } else {
      signal.addEventListener('abort', () => controller.abort(), { once: true });
    }
  }

  const requestHeaders = new Headers(headers);
  requestHeaders.set('Authorization', `Bearer ${accessToken}`);

  if (body !== undefined) {
    requestHeaders.set('Content-Type', 'application/json');
  }

  let response: Response;

  try {
    response = await fetch(getApiUrl(path), {
      ...requestOptions,
      body,
      headers: requestHeaders,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('The request took too long. Please try again.', 408);
    }

    throw error;
  } finally {
    if (timeoutId !== null) {
      window.clearTimeout(timeoutId);
    }
  }

  if (!response.ok) {
    throw new ApiError(await getErrorMessage(response), response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
