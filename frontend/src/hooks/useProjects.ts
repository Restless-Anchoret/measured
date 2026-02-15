import { useState, useEffect } from 'react';
import { API_URL } from '../config';
import type { Project } from '../types';

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    
    fetch(`${API_URL}/projects`, { signal: controller.signal })
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

