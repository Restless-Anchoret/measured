import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import { MoreVertical, Trash2 } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { Pagination } from '@/components/ui/pagination';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { useProjects } from '../hooks/useProjects';
import { useSessions } from '../hooks/useSessions';
import { formatDurationInMinutes } from '@/lib/format';
import { API_URL } from '../config';
import type { Session } from '../lib/types';

const PAGE_SIZE = 20;

export default function Sessions() {
  const { projects, loading: loadingProjects, error: projectsError } = useProjects();
  const [page, setPage] = useState(1);
  const [sessionToDelete, setSessionToDelete] = useState<Session | null>(null);
  const [deleting, setDeleting] = useState(false);
  
  const { sessionsPage, totalPages, loading: loadingSessions, error: sessionsError, refetch } = useSessions({
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
    return formatDurationInMinutes(diffMinutes);
  };

  const formatStartDate = (startTime: string): string => {
    return format(new Date(startTime), 'dd.MM.yyyy');
  };

  const handleDelete = async () => {
    if (!sessionToDelete) return;

    setDeleting(true);
    try {
      const response = await fetch(`${API_URL}/sessions/${sessionToDelete.id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete session');
      }

      setSessionToDelete(null);
      refetch();
    } catch {
      toast.error('Failed to delete session');
    } finally {
      setDeleting(false);
    }
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
              <TableHead className="w-[50px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sessions.map((session) => (
              <TableRow key={session.id}>
                <TableCell>{getProjectName(session.project_id)}</TableCell>
                <TableCell>{formatDuration(session.start_time, session.end_time)}</TableCell>
                <TableCell>{formatStartDate(session.start_time)}</TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        className="text-destructive focus:text-destructive"
                        onClick={() => setSessionToDelete(session)}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
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

      <AlertDialog open={!!sessionToDelete} onOpenChange={(open) => { if (!open) setSessionToDelete(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure you want to delete this session?</AlertDialogTitle>
            <AlertDialogDescription>
              {sessionToDelete && (
                <>
                  {getProjectName(sessionToDelete.project_id)} &mdash;{' '}
                  {formatStartDate(sessionToDelete.start_time)},{' '}
                  {formatDuration(sessionToDelete.start_time, sessionToDelete.end_time)}
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleting ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
