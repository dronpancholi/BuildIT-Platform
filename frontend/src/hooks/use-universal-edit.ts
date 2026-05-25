/**
 * Universal Edit System
 * 
 * Provides inline, modal, and full-page editing capabilities across all entities.
 * Every edit must:
 * - Update database
 * - Update cache
 * - Update UI
 * - Survive refresh
 * - Survive restart
 */

import { useState, useCallback, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';

export interface EditState<T> {
  original: T | null;
  current: T | null;
  isDirty: boolean;
  isSaving: boolean;
  error: string | null;
}

export interface EditOptions<T> {
  entity: string;
  id: string;
  onUpdate: (data: T) => Promise<void>;
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

export function useUniversalEdit<T>({
  entity,
  id,
  onUpdate,
  onSuccess,
  onError,
}: EditOptions<T>) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<EditState<T>>({
    original: null,
    current: null,
    isDirty: false,
    isSaving: false,
    error: null,
  });

  // Load original data
  useEffect(() => {
    const loadData = async () => {
      try {
        const response = await fetch(`/api/v1/${entity}/${id}`);
        const data = await response.json();
        setState(prev => ({
          ...prev,
          original: data.data,
          current: data.data,
          isDirty: false,
        }));
      } catch (error) {
        setState(prev => ({
          ...prev,
          error: error instanceof Error ? error.message : 'Failed to load data',
        }));
      }
    };

    if (id) {
      loadData();
    }
  }, [entity, id]);

  // Check for dirty state
  const isDirty = useCallback((current: T | null, original: T | null) => {
    if (!current || !original) return false;
    return JSON.stringify(current) !== JSON.stringify(original);
  }, []);

  // Update field value
  const updateField = useCallback(<K extends keyof T>(field: K, value: T[K]) => {
    setState(prev => {
      if (!prev.current) return prev;
      
      const updated = { ...prev.current, [field]: value };
      return {
        ...prev,
        current: updated,
        isDirty: isDirty(updated, prev.original),
      };
    });
  }, [isDirty]);

  // Save changes
  const save = useCallback(async () => {
    if (!state.current || !state.isDirty) return;

    setState(prev => ({ ...prev, isSaving: true, error: null }));

    try {
      await onUpdate(state.current);
      
      // Invalidate queries
      queryClient.invalidateQueries({ queryKey: [entity] });
      queryClient.invalidateQueries({ queryKey: [entity, id] });
      
      // Update original to current
      setState(prev => ({
        ...prev,
        original: prev.current,
        isDirty: false,
        isSaving: false,
      }));

      onSuccess?.();
    } catch (error) {
      setState(prev => ({
        ...prev,
        isSaving: false,
        error: error instanceof Error ? error.message : 'Failed to save',
      }));
      onError?.(error instanceof Error ? error : new Error('Failed to save'));
    }
  }, [state.current, state.isDirty, onUpdate, onSuccess, onError, queryClient, entity, id]);

  // Cancel edits
  const cancel = useCallback(() => {
    setState(prev => ({
      ...prev,
      current: prev.original,
      isDirty: false,
      error: null,
    }));
  }, []);

  // Reset
  const reset = useCallback(() => {
    setState({
      original: null,
      current: null,
      isDirty: false,
      isSaving: false,
      error: null,
    });
  }, []);

  return {
    data: state.current,
    original: state.original,
    isDirty: state.isDirty,
    isSaving: state.isSaving,
    error: state.error,
    updateField,
    save,
    cancel,
    reset,
  };
}

// Auto-save hook
export function useAutoSave<T>(data: T | null, isDirty: boolean, onSave: () => Promise<void>, delay: number = 5000) {
  useEffect(() => {
    if (!isDirty || !data) return;

    const timer = setTimeout(() => {
      onSave();
    }, delay);

    return () => clearTimeout(timer);
  }, [data, isDirty, onSave, delay]);
}

// Conflict detection
export function useConflictDetection<T>(entity: string, id: string, currentVersion: number) {
  const [hasConflict, setHasConflict] = useState(false);

  useEffect(() => {
    const checkConflict = async () => {
      try {
        const response = await fetch(`/api/v1/${entity}/${id}`);
        const data = await response.json();
        setHasConflict(data.version !== currentVersion);
      } catch (error) {
        console.error('Conflict detection failed:', error);
      }
    };

    const interval = setInterval(checkConflict, 10000); // Check every 10 seconds
    return () => clearInterval(interval);
  }, [entity, id, currentVersion]);

  return hasConflict;
}
