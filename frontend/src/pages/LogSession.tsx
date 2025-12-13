import { useState, useEffect } from 'react';
import {
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
  Snackbar,
  Alert,
} from '@mui/material';
import { API_URL } from '../config';
import type { Project } from '../types';

export default function LogSession() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [duration, setDuration] = useState<number | null>(null);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error';
  }>({
    open: false,
    message: '',
    severity: 'success',
  });

  useEffect(() => {
    fetch(`${API_URL}/projects`)
      .then((response) => response.json())
      .then((data) => {
        setProjects(data);
        setProjectsLoading(false);
      })
      .catch((error) => {
        console.error('Error fetching projects:', error);
        setProjectsLoading(false);
        setSnackbar({
          open: true,
          message: 'Failed to load projects',
          severity: 'error',
        });
      });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedProjectId || duration === null) {
      setSnackbar({
        open: true,
        message: 'Please fill in all fields',
        severity: 'error',
      });
      return;
    }

    if (duration <= 0) {
      setSnackbar({
        open: true,
        message: 'Duration must be a positive number',
        severity: 'error',
      });
      return;
    }

    setSubmitting(true);

    const now = new Date();
    const startTime = new Date(now.getTime() - duration * 60 * 1000);

    try {
      const response = await fetch(`${API_URL}/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_id: selectedProjectId,
          start_time: startTime.toISOString(),
          end_time: now.toISOString(),
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to log session');
      }

      setSnackbar({
        open: true,
        message: 'New session logged',
        severity: 'success',
      });

      // Clear duration field on success
      setDuration(null);
    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to log session',
        severity: 'error',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  return (
    <div>
      <Typography variant="h4" component="h1" gutterBottom>
        Log Session
      </Typography>
      <Box component="form" onSubmit={handleSubmit} sx={{ maxWidth: 400, mt: 3 }}>
        <FormControl fullWidth margin="normal" required>
          <InputLabel id="project-select-label">Project</InputLabel>
          <Select
            labelId="project-select-label"
            id="project-select"
            value={selectedProjectId ?? ''}
            label="Project"
            onChange={(e) => setSelectedProjectId(e.target.value as number | null)}
            disabled={projectsLoading}
          >
            {projects.map((project) => (
              <MenuItem key={project.id} value={project.id}>
                {project.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <TextField
          fullWidth
          margin="normal"
          label="Duration (minutes)"
          type="number"
          value={duration ?? ''}
          onChange={(e) => {
            const value = e.target.value;
            setDuration(value === '' ? null : Number(value));
          }}
          required
          inputProps={{ min: 1 }}
        />
        <Button
          type="submit"
          variant="contained"
          fullWidth
          sx={{ mt: 3 }}
          disabled={submitting || projectsLoading}
        >
          {submitting ? 'Logging...' : 'Log Session'}
        </Button>
      </Box>
      <Snackbar
        open={snackbar.open}
        autoHideDuration={3000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </div>
  );
}
