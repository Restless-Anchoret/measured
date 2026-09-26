import { useState, useEffect, useCallback } from 'react';
import { API_URL } from '../config';
import type { PaginatedSessions } from '../lib/types';

interface UseSessionsParams {
  page: number;
  pageSize: number;
  minDate?: string;
  maxDate?: string;
  projectIds?: number[];
}

export function useSessions({ page, pageSize, minDate, maxDate, projectIds }: UseSessionsParams) {
  const [sessionsPage, setSessionsPage] = useState<PaginatedSessions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const projectIdsKey = projectIds ? projectIds.join(',') : '';

  useEffect(() => {
    const controller = new AbortController();
    
    setLoading(true);
    setSessionsPage(null);
    setError(null);
    
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    
    if (minDate) {
      params.append('min_date', minDate);
    }

    if (maxDate) {
      params.append('max_date', maxDate);
    }
    
    if (projectIds && projectIds.length > 0) {
      for (const id of projectIds) {
        params.append('project_id', id.toString());
      }
    }
    
    fetch(`${API_URL}/sessions?${params.toString()}`, { signal: controller.signal })
      .then((response) => response.json())
      .then((data: PaginatedSessions) => {
        setSessionsPage(data);
        setLoading(false);
      })
      .catch((error) => {
        if (error.name === 'AbortError') return;
        console.error('Error fetching sessions:', error);
        setError(error);
        setLoading(false);
      });
    
    return () => controller.abort();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, minDate, maxDate, projectIdsKey, refreshKey]);

  const refetch = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  const totalPages = sessionsPage ? Math.ceil(sessionsPage.total / pageSize) : 0;

  return { sessionsPage, totalPages, loading, error, refetch };
}

