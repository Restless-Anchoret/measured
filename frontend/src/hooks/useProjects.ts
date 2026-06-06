import { useState, useEffect } from 'react';
import { API_URL } from '../config';
import type { Project } from '../lib/types';

type ProjectSort = 'DEFAULT' | 'MOST_RECENTLY_USED';

export function useProjects(sort: ProjectSort = 'DEFAULT') {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    fetch(`${API_URL}/projects?sort=${sort}`, { signal: controller.signal })
      .then((response) => response.json())
      .then((data) => {
        setProjects(data);
        setLoading(false);
      })
      .catch((error) => {
        if (error.name === 'AbortError') return; // Ignore abort errors
        console.error('Error fetching projects:', error);
        setError(error);
        setLoading(false);
      });
    
    return () => controller.abort();
  }, []);

  return { projects, loading, error };
}

