import { useState, useEffect } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Spinner } from '@/components/ui/spinner';
import { Pagination } from '@/components/ui/pagination';
import { API_URL } from '../config';
import type { Session, PaginatedSessions } from '../types';
import { useProjects } from '../hooks/useProjects';

const PAGE_SIZE = 10;

export default function Sessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const { projects, loading: loadingProjects } = useProjects();
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  // Fetch sessions when page changes
  useEffect(() => {
    const controller = new AbortController();
    
    const fetchSessions = async () => {
      setLoadingSessions(true);
      try {
        const response = await fetch(
          `${API_URL}/sessions?page=${page}&page_size=${PAGE_SIZE}`,
          { signal: controller.signal }
        );
        const data: PaginatedSessions = await response.json();
        setSessions(data.items);
        setTotal(data.total);
        setLoadingSessions(false);
      } catch (error) {
        if ((error as Error).name === 'AbortError') return; // Ignore abort errors
        console.error('Error fetching sessions:', error);
        setSessions([]);
        setLoadingSessions(false);
      }
    };
    
    fetchSessions();
    return () => controller.abort();
  }, [page]);

  const getProjectName = (projectId: number): string => {
    const project = projects.find((p) => p.id === projectId);
    return project?.name || 'Unknown';
  };

  const formatDuration = (startTime: string, endTime: string | null): string => {
    if (!endTime) {
      return 'Ongoing';
    }
    const start = new Date(startTime);
    const end = new Date(endTime);
    const diffMs = end.getTime() - start.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    return `${diffMinutes} minutes`;
  };

  const formatStartDate = (startTime: string): string => {
    const date = new Date(startTime);
    return date.toLocaleDateString();
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const isLoading = loadingProjects || loadingSessions;

  if (isLoading && sessions.length === 0) {
    return (
      <div className="flex justify-center items-center min-h-[200px]">
        <Spinner />
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-4xl font-bold mb-6">Sessions</h1>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Project Name</TableHead>
              <TableHead>Duration</TableHead>
              <TableHead>Start Date</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sessions.map((session) => (
              <TableRow key={session.id}>
                <TableCell>{getProjectName(session.project_id)}</TableCell>
                <TableCell>{formatDuration(session.start_time, session.end_time)}</TableCell>
                <TableCell>{formatStartDate(session.start_time)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <div className="mt-6">
        <Pagination
          currentPage={page}
          totalPages={totalPages}
          onPageChange={setPage}
        />
      </div>
    </div>
  );
}
