import { ApiError } from '@/services/api-client';

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return 'An unexpected error occurred';
}

export function getErrorTitle(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404) return 'Not Found';
    if (error.status === 403) return 'Access Denied';
    if (error.status === 401) return 'Unauthorized';
    if (error.status === 422) return 'Validation Error';
    if (error.status >= 500) return 'Server Error';
  }
  return 'Error';
}
