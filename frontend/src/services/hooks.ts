import { useQuery, useMutation, useQueryClient, UseQueryOptions } from '@tanstack/react-query';
import { api, ApiError } from './api-client';
import { toast } from 'sonner';

interface MutationOptions {
  invalidateKeys?: string[];
  successMessage?: string;
}

// Generic list query
export function useApiList<T>(
  endpoint: string,
  params?: Record<string, string | number | boolean | undefined>,
  options?: Omit<UseQueryOptions<T[], ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<T[], ApiError>({
    queryKey: [endpoint, params],
    queryFn: () => api.get<T[]>(endpoint, { params }),
    ...options,
  });
}

// Generic detail query
export function useApiDetail<T>(
  endpoint: string,
  id: string | null,
  options?: Omit<UseQueryOptions<T, ApiError>, 'queryKey' | 'queryFn'>
) {
  return useQuery<T, ApiError>({
    queryKey: [endpoint, id],
    queryFn: () => api.get<T>(`${endpoint}/${id}`),
    enabled: !!id,
    ...options,
  });
}

// Generic create mutation
export function useApiCreate<TData, TVariables>(
  endpoint: string,
  opts?: MutationOptions
) {
  const queryClient = useQueryClient();
  const { invalidateKeys, successMessage } = opts || {};

  return useMutation<TData, ApiError, TVariables>({
    mutationFn: (variables) => api.post<TData>(endpoint, variables),
    onSuccess: () => {
      invalidateKeys?.forEach((key) => queryClient.invalidateQueries({ queryKey: [key] }));
      if (successMessage) toast.success(successMessage);
    },
    onError: (error: ApiError) => {
      toast.error(error.message || 'Operation failed');
    },
  });
}

// Generic update mutation
export function useApiUpdate<TData, TVariables>(
  endpoint: string,
  opts?: MutationOptions
) {
  const queryClient = useQueryClient();
  const { invalidateKeys, successMessage } = opts || {};

  return useMutation<TData, ApiError, TVariables>({
    mutationFn: (variables: unknown) => {
      const { id, ...body } = variables as { id: string; [key: string]: unknown };
      return api.put<TData>(`${endpoint}/${id}`, body);
    },
    onSuccess: () => {
      invalidateKeys?.forEach((key) => queryClient.invalidateQueries({ queryKey: [key] }));
      if (successMessage) toast.success(successMessage);
    },
    onError: (error: ApiError) => {
      toast.error(error.message || 'Update failed');
    },
  });
}

// Generic delete mutation
export function useApiDelete(
  endpoint: string,
  opts?: MutationOptions
) {
  const queryClient = useQueryClient();
  const { invalidateKeys, successMessage } = opts || {};

  return useMutation<void, ApiError, string>({
    mutationFn: (id) => api.delete<void>(`${endpoint}/${id}`),
    onSuccess: () => {
      invalidateKeys?.forEach((key) => queryClient.invalidateQueries({ queryKey: [key] }));
      if (successMessage) toast.success(successMessage);
    },
    onError: (error: ApiError) => {
      toast.error(error.message || 'Delete failed');
    },
  });
}
