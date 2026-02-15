import { useState, useEffect } from 'react';
import { API_URL } from '../config';
import type { PaginatedSessions } from '../types';

interface UseSessionsParams {
  page: number;
  pageSize: number;
  minStartTime?: Date;
  maxStartTime?: Date;
}

export function useSessions({ page, pageSize, minStartTime, maxStartTime }: UseSessionsParams) {
  const [sessionsPage, setSessionsPage] = useState<PaginatedSessions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

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
  }, [page, pageSize, minStartTime, maxStartTime]);

  const totalPages = sessionsPage ? Math.ceil(sessionsPage.total / pageSize) : 0;

  return { sessionsPage, totalPages, loading, error };
}

