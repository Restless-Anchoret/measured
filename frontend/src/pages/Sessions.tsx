import { useState, useEffect } from 'react';
import { toast } from 'sonner';
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
import { useProjects } from '../hooks/useProjects';
import { useSessions } from '../hooks/useSessions';

const PAGE_SIZE = 20;

export default function Sessions() {
  const { projects, loading: loadingProjects, error: projectsError } = useProjects();
  const [page, setPage] = useState(1);
  
  const { sessionsPage, totalPages, loading: loadingSessions, error: sessionsError } = useSessions({
    page,
    pageSize: PAGE_SIZE,
  });

  useEffect(() => {
    if (projectsError) {
      toast.error('Failed to load projects');
    }
  }, [projectsError]);

  useEffect(() => {
    if (sessionsError) {
      toast.error('Failed to load sessions');
    }
  }, [sessionsError]);

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

  const isLoading = loadingProjects || loadingSessions;
  const sessions = sessionsPage?.items || [];

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
