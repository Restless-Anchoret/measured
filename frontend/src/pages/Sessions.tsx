import { useState, useEffect } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  CircularProgress,
  Box,
  Pagination,
} from '@mui/material';
import { API_URL } from '../config';
import type { Session, Project, PaginatedSessions } from '../types';

const PAGE_SIZE = 10;

export default function Sessions() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  // Fetch projects once
  useEffect(() => {
    setLoadingProjects(true);
    fetch(`${API_URL}/projects`)
      .then((response) => response.json())
      .then((data) => {
        setProjects(data);
        setLoadingProjects(false);
      })
      .catch((error) => {
        console.error('Error fetching projects:', error);
        setLoadingProjects(false);
      });
  }, []);

  // Fetch sessions when page changes
  useEffect(() => {
    setLoadingSessions(true);
    fetch(`${API_URL}/sessions?page=${page}&page_size=${PAGE_SIZE}`)
      .then((response) => response.json())
      .then((data: PaginatedSessions) => {
        setSessions(data.items);
        setTotal(data.total);
        setLoadingSessions(false);
      })
      .catch((error) => {
        console.error('Error fetching sessions:', error);
        setSessions([]);
        setLoadingSessions(false);
      });
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
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <div>
      <Typography variant="h4" component="h1" gutterBottom>
        Sessions
      </Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Project Name</TableCell>
              <TableCell>Duration</TableCell>
              <TableCell>Start Date</TableCell>
            </TableRow>
          </TableHead>
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
      </TableContainer>
      {totalPages > 1 && (
        <Box display="flex" justifyContent="center" mt={3}>
          <Pagination
            count={totalPages}
            page={page}
            onChange={(_, newPage) => setPage(newPage)}
            color="primary"
          />
        </Box>
      )}
    </div>
  );
}
