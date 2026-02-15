import { useMemo } from 'react';
import { startOfWeek, addDays, addWeeks, addMonths } from 'date-fns';
import type { DateRange, Session, Project } from '@/types';
import { useSessions } from '@/hooks/useSessions';
import { useProjects } from '@/hooks/useProjects';

interface SessionsChartProps {
  dateRange: DateRange;
}

interface CompletedSession {
  id: number;
  project_id: number;
  start_time: Date;
  duration_in_minutes: number;
}

interface TimeSegment {
  start: Date;
  end: Date;
}

interface SessionsTimeSegment {
  timeSegment: TimeSegment;
  sessions: CompletedSession[];
}

interface AggregatedSession {
  project: Project;
  duration_in_minutes: number;
}

interface AggregatedSessionsTimeSegment {
  timeSegment: TimeSegment;
  sessions: AggregatedSession[];
}

function buildTimeSegments(dateRange: DateRange): TimeSegment[] {
  const segments: TimeSegment[] = [];
  const weekOptions = { weekStartsOn: 1 as const }; // Monday
  
  let current = dateRange.fromDate;
  
  // For weekly aggregation, start from the Monday of the week containing fromDate
  if (dateRange.aggregationBy === 'week') {
    current = startOfWeek(current, weekOptions);
  }

  while (current.getTime() < dateRange.toDate.getTime()) {
    const segmentStart = current;
    let segmentEnd: Date;
    
    switch (dateRange.aggregationBy) {
      case 'day':
        segmentEnd = addDays(current, 1);
        break;
      case 'week':
        segmentEnd = addWeeks(current, 1);
        break;
      case 'month':
        segmentEnd = addMonths(current, 1);
        break;
    }
    
    segments.push({
      start: segmentStart,
      end: segmentEnd,
    });
    
    current = segmentEnd;
  }
  
  return segments;
}

function convertToCompletedSessions(sessions: Session[]): CompletedSession[] {
  return sessions
    .filter(session => session.end_time !== null)
    .map(session => {
      const startTime = new Date(session.start_time).getTime();
      const endTime = new Date(session.end_time!).getTime();
      const durationInMinutes = Math.floor((endTime - startTime) / (1000 * 60));
      
      return {
        id: session.id,
        project_id: session.project_id,
        start_time: new Date(session.start_time),
        duration_in_minutes: durationInMinutes,
      };
    });
}

function groupSessionsIntoTimeSegments(
  timeSegments: TimeSegment[],
  completedSessions: CompletedSession[]
): SessionsTimeSegment[] {
  const result: SessionsTimeSegment[] = [];
  
  // Counter for time segments (forward)
  let segmentIndex = 0;
  
  // Counter for completed sessions (backward)
  let sessionIndex = completedSessions.length - 1;
  
  while (segmentIndex < timeSegments.length) {
    const segment = timeSegments[segmentIndex];
    const sessionsInSegment: CompletedSession[] = [];
    
    // Collect all sessions that fall within this segment
    // Sessions are processed from end to start
    while (sessionIndex >= 0) {
      const session = completedSessions[sessionIndex];
      const sessionStartTime = session.start_time.getTime();
      const segmentStartTime = segment.start.getTime();
      const segmentEndTime = segment.end.getTime();

      if (sessionStartTime >= segmentStartTime && sessionStartTime < segmentEndTime) {
        sessionsInSegment.push(session);
        sessionIndex--;
      } else {
        break;
      }
    }

    result.push({
      timeSegment: segment,
      sessions: sessionsInSegment,
    });
    
    segmentIndex++;
  }
  
  return result;
}

function aggregateSessionsByProject(
  sessionsTimeSegments: SessionsTimeSegment[],
  projects: Project[]
): AggregatedSessionsTimeSegment[] {
  return sessionsTimeSegments.map(segment => {
    // Group sessions by project_id
    const sessionsByProjectId = new Map<number, number>();
    
    for (const session of segment.sessions) {
      const currentDuration = sessionsByProjectId.get(session.project_id) || 0;
      sessionsByProjectId.set(session.project_id, currentDuration + session.duration_in_minutes);
    }
    
    // Create aggregated sessions
    const aggregatedSessions: AggregatedSession[] = [];
    
    for (const [projectId, totalDuration] of sessionsByProjectId) {
      const project = projects.find(p => p.id === projectId);
      
      if (project) {
        aggregatedSessions.push({
          project,
          duration_in_minutes: totalDuration,
        });
      }
    }
    
    return {
      timeSegment: segment.timeSegment,
      sessions: aggregatedSessions,
    };
  });
}

export default function SessionsChart({ dateRange }: SessionsChartProps) {
  const { sessionsPage, loading, error } = useSessions({
    page: 1,
    pageSize: 1000,
    minStartTime: dateRange.fromDate,
    maxStartTime: dateRange.toDate,
  });

  const { projects, loading: projectsLoading, error: projectsError } = useProjects();

  // Generate time segments based on aggregation type
  const timeSegments = useMemo<TimeSegment[]>(
    () => buildTimeSegments(dateRange),
    [dateRange]
  );

  // Calculate list of completed sessions (sessions with end_time defined)
  const completedSessions = useMemo<CompletedSession[]>(
    () => sessionsPage?.items ? convertToCompletedSessions(sessionsPage.items) : [],
    [sessionsPage?.items]
  );

  // Group sessions into time segments
  const sessionsTimeSegments = useMemo<SessionsTimeSegment[]>(
    () => groupSessionsIntoTimeSegments(timeSegments, completedSessions),
    [timeSegments, completedSessions]
  );

  // Aggregate sessions by project
  const aggregatedSessionsTimeSegments = useMemo<AggregatedSessionsTimeSegment[]>(
    () => projects ? aggregateSessionsByProject(sessionsTimeSegments, projects) : [],
    [sessionsTimeSegments, projects]
  );

  // Calculate total duration in milliseconds
  const totalDuration = useMemo(() => {
    if (!sessionsPage?.items) return 0;
    
    return sessionsPage.items.reduce((total, session) => {
      if (!session.end_time) return total;
      
      const startTime = new Date(session.start_time).getTime();
      const endTime = new Date(session.end_time).getTime();
      return total + (endTime - startTime);
    }, 0);
  }, [sessionsPage?.items]);

  // Format duration as hours and minutes
  const formatDuration = (milliseconds: number) => {
    const hours = Math.floor(milliseconds / (1000 * 60 * 60));
    const minutes = Math.floor((milliseconds % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}h ${minutes}m`;
  };

  return (
    <div className="mt-6 p-4 border rounded-md bg-muted/50">
      <h2 className="text-lg font-semibold mb-2">Selected Interval:</h2>
      <div className="space-y-1 text-sm">
        <p>
          <span className="font-medium">From Date:</span>{' '}
          {dateRange.fromDate.toLocaleDateString()}
        </p>
        <p>
          <span className="font-medium">To Date (exclusive):</span>{' '}
          {dateRange.toDate.toLocaleDateString()}
        </p>
        <p>
          <span className="font-medium">Interval Kind:</span>{' '}
          {dateRange.intervalKind}
        </p>
        <p>
          <span className="font-medium">Aggregation By:</span>{' '}
          {dateRange.aggregationBy}
        </p>
      </div>

      <div className="mt-4 pt-4 border-t space-y-1 text-sm">
        {loading && <p className="text-muted-foreground">Loading sessions...</p>}
        {error && <p className="text-destructive">Error loading sessions: {error.message}</p>}
        {sessionsPage && (
          <>
            <p>
              <span className="font-medium">Sessions in Period:</span>{' '}
              {sessionsPage.items.length}
            </p>
            <p>
              <span className="font-medium">Total Duration:</span>{' '}
              {formatDuration(totalDuration)}
            </p>
          </>
        )}
      </div>

      {/* Aggregated Sessions by Time Segment */}
      <div className="mt-6 pt-4 border-t">
        <h3 className="text-md font-semibold mb-3">Aggregated Sessions by Time Segment:</h3>
        {projectsLoading && <p className="text-sm text-muted-foreground">Loading projects...</p>}
        {projectsError && <p className="text-sm text-destructive">Error loading projects: {projectsError.message}</p>}
        
        {aggregatedSessionsTimeSegments.length === 0 && !projectsLoading && (
          <p className="text-sm text-muted-foreground">No aggregated sessions to display.</p>
        )}
        
        <div className="space-y-4">
          {aggregatedSessionsTimeSegments.map((segment, segmentIndex) => (
            <div key={segmentIndex} className="p-3 bg-background rounded-md border">
              <div className="mb-2">
                <span className="text-sm font-medium">Time Segment #{segmentIndex + 1}:</span>
                <div className="text-sm text-muted-foreground ml-4">
                  <div>Start: {segment.timeSegment.start.toLocaleString()}</div>
                  <div>End: {segment.timeSegment.end.toLocaleString()}</div>
                </div>
              </div>
              
              {segment.sessions.length === 0 ? (
                <p className="text-sm text-muted-foreground ml-4">No sessions in this segment</p>
              ) : (
                <div className="ml-4 space-y-2">
                  <div className="text-sm font-medium">Projects and Durations:</div>
                  {segment.sessions.map((session, sessionIndex) => (
                    <div key={sessionIndex} className="text-sm ml-4 flex justify-between items-center">
                      <span>
                        <span className="font-medium">{session.project.name}</span>
                        <span className="text-muted-foreground"> (ID: {session.project.id})</span>
                      </span>
                      <span className="font-mono">
                        {Math.floor(session.duration_in_minutes / 60)}h {session.duration_in_minutes % 60}m
                      </span>
                    </div>
                  ))}
                  <div className="text-sm ml-4 pt-2 border-t">
                    <span className="font-medium">Total in segment: </span>
                    <span className="font-mono">
                      {Math.floor(segment.sessions.reduce((sum, s) => sum + s.duration_in_minutes, 0) / 60)}h{' '}
                      {segment.sessions.reduce((sum, s) => sum + s.duration_in_minutes, 0) % 60}m
                    </span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

