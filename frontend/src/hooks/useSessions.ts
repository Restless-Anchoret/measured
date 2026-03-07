import { useState, useEffect } from 'react';
import { API_URL } from '../config';
import type { PaginatedSessions } from '../types';

interface UseSessionsParams {
  page: number;
  pageSize: number;
  minStartTime?: Date;
  maxStartTime?: Date;
  projectIds?: number[];
}

export function useSessions({ page, pageSize, minStartTime, maxStartTime, projectIds }: UseSessionsParams) {
  const [sessionsPage, setSessionsPage] = useState<PaginatedSessions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const projectIdsKey = projectIds ? projectIds.join(',') : '';

  useEffect(() => {
    const controller = new AbortController();
    
    setLoading(true);
    setSessionsPage(null);
    setError(null);
    
    // Build query parameters
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    
    if (minStartTime) {
      params.append('min_start_time', minStartTime.toISOString());
    }
    
    if (maxStartTime) {
      params.append('max_start_time', maxStartTime.toISOString());
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
        if (error.name === 'AbortError') return; // Ignore abort errors
        console.error('Error fetching sessions:', error);
        setError(error);
        setLoading(false);
      });
    
    return () => controller.abort();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize, minStartTime, maxStartTime, projectIdsKey]);

  const totalPages = sessionsPage ? Math.ceil(sessionsPage.total / pageSize) : 0;

  return { sessionsPage, totalPages, loading, error };
}

