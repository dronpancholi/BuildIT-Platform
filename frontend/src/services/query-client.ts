import { QueryClient } from '@tanstack/react-query';
import { QUERY_STALE_TIME, QUERY_CACHE_TIME } from '@/config/constants';

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: QUERY_STALE_TIME,
        gcTime: QUERY_CACHE_TIME,
        refetchOnWindowFocus: false,
        retry: (failureCount, error: Error & { status?: number }) => {
          if (error?.status === 404 || error?.status === 403 || error?.status === 401) return false;
          return failureCount < 2;
        },
      },
      mutations: {
        retry: false,
      },
    },
  });
}
