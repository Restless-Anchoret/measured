import { useMemo, useState } from 'react';
import { startOfWeek, addDays, addWeeks, addMonths, format, addDays as addOneDay } from 'date-fns';
import type { DateRange, Session, Project } from '@/types';
import { useSessions } from '@/hooks/useSessions';
import { useProjects } from '@/hooks/useProjects';
import Tooltip from './Tooltip';

interface SessionsChartProps {
  dateRange: DateRange;
  verbose?: boolean;
}

interface CompletedSession {
  id: number;
  projectId: number;
  startTime: Date;
  durationInMinutes: number;
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
  durationInMinutes: number;
}

interface AggregatedSessionsTimeSegment {
  timeSegment: TimeSegment;
  sessions: AggregatedSession[];
  totalDuration: number;
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
        projectId: session.project_id,
        startTime: new Date(session.start_time),
        durationInMinutes: durationInMinutes,
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
      const sessionStartTime = session.startTime.getTime();
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
    // Group sessions by projectId
    const sessionsByProjectId = new Map<number, number>();
    
    for (const session of segment.sessions) {
      const currentDuration = sessionsByProjectId.get(session.projectId) || 0;
      sessionsByProjectId.set(session.projectId, currentDuration + session.durationInMinutes);
    }
    
    // Create aggregated sessions
    const aggregatedSessions: AggregatedSession[] = [];
    let totalDuration = 0;
    
    for (const [projectId, duration] of sessionsByProjectId) {
      const project = projects.find(p => p.id === projectId);
      
      if (project) {
        aggregatedSessions.push({
          project,
          durationInMinutes: duration,
        });
        totalDuration += duration;
      }
    }
    
    return {
      timeSegment: segment.timeSegment,
      sessions: aggregatedSessions,
      totalDuration,
    };
  });
}

function getSegmentBorderRadius(isFirst: boolean, isLast: boolean): React.CSSProperties {
  return {
    borderTopLeftRadius: isFirst ? '0.375rem' : '0',
    borderBottomLeftRadius: isFirst ? '0.375rem' : '0',
    borderTopRightRadius: isLast ? '0.375rem' : '0',
    borderBottomRightRadius: isLast ? '0.375rem' : '0',
  };
}

export default function SessionsChart({ dateRange, verbose = false }: SessionsChartProps) {
  const [activeTooltip, setActiveTooltip] = useState<string | null>(null);
  const [isTouchDevice, setIsTouchDevice] = useState(false);

  // Detect if device supports touch
  useMemo(() => {
    setIsTouchDevice('ontouchstart' in window || navigator.maxTouchPoints > 0);
  }, []);

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

  // Format segment label based on aggregation type
  const formatSegmentLabel = (segment: TimeSegment): string => {
    const start = segment.start;
    const end = segment.end;

    switch (dateRange.aggregationBy) {
      case 'day':
        return format(start, 'dd.MM');
      case 'week':
        const weekEnd = addOneDay(end, -1);
        return `${format(start, 'dd.MM')} - ${format(weekEnd, 'dd.MM')}`;
      case 'month':
        return format(start, 'MMMM');
    }
  };

  // Format duration in minutes to readable string
  const formatDurationInMinutes = (minutes: number): string => {
    if (minutes === 0) {
      return '0';
    }
    
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    
    if (hours === 0) {
      return `${remainingMinutes}m`;
    }
    
    if (remainingMinutes === 0) {
      return `${hours}h`;
    }
    
    return `${hours}h ${remainingMinutes}m`;
  };

  // Calculate max total duration for proportional sizing
  const maxDuration = useMemo(() => {
    return Math.max(
      ...aggregatedSessionsTimeSegments.map(segment => segment.totalDuration),
      1 // Minimum 1 to avoid division by zero
    );
  }, [aggregatedSessionsTimeSegments]);

  return (
    <div className="mt-6 space-y-4" onClick={isTouchDevice ? () => setActiveTooltip(null) : undefined}>
      {/* Visual Chart */}
      <div className="p-4 border rounded-md bg-card">
        <h2 className="text-lg font-semibold mb-4">Sessions Timeline</h2>
        <div className="space-y-2">
          {aggregatedSessionsTimeSegments.map((segment, segmentIndex) => {
            return (
              <div key={segmentIndex} className="flex items-center gap-1 sm:gap-2 md:gap-3 relative">
                {/* Segment Label */}
                <div className="w-14 sm:w-24 md:w-32 text-xs sm:text-sm font-medium text-right flex-shrink-0">
                  {formatSegmentLabel(segment.timeSegment)}
                </div>
                
                {/* Visual Bar */}
                <div className="flex-1">
                  <div className="flex items-center h-8 bg-muted/30 rounded relative">
                    {segment.sessions.map((session, sessionIndex) => {
                        const widthPercent = (session.durationInMinutes / maxDuration) * 100;
                        const isFirst = sessionIndex === 0;
                        const isLast = sessionIndex === segment.sessions.length - 1;
                        const tooltipKey = `${segmentIndex}-${sessionIndex}`;
                        const isTooltipVisible = activeTooltip === tooltipKey;
                        
                        return (
                          <div
                            key={sessionIndex}
                            className="h-full relative group cursor-pointer"
                            style={{ width: `${widthPercent}%` }}
                            onClick={isTouchDevice ? (e) => {
                              e.stopPropagation();
                              setActiveTooltip(isTooltipVisible ? null : tooltipKey);
                            } : undefined}
                          >
                            {/* Color segments */}
                            <div className="w-full h-full flex items-center justify-center">
                              {session.project.extraColor ? (
                                // Two-color gradient for projects with extraColor
                                <div 
                                  className="w-full h-full flex flex-col overflow-hidden"
                                  style={getSegmentBorderRadius(isFirst, isLast)}
                                >
                                  <div
                                    className="w-full h-1/2 transition-opacity group-hover:opacity-80"
                                    style={{ backgroundColor: session.project.color }}
                                  />
                                  <div
                                    className="w-full h-1/2 transition-opacity group-hover:opacity-80"
                                    style={{ backgroundColor: session.project.extraColor }}
                                  />
                                </div>
                              ) : (
                                // Single color
                                <div
                                  className="w-full h-full transition-opacity group-hover:opacity-80"
                                  style={{ 
                                    backgroundColor: session.project.color,
                                    ...getSegmentBorderRadius(isFirst, isLast),
                                  }}
                                />
                              )}
                            </div>
                            
                            {/* Tooltip */}
                            <Tooltip
                              text={`${session.project.name}: ${formatDurationInMinutes(session.durationInMinutes)}`}
                              visible={isTouchDevice && isTooltipVisible}
                            />
                          </div>
                        );
                      })}
                  </div>
                </div>
                
                {/* Duration Label */}
                <div className="w-12 sm:w-16 md:w-20 text-xs sm:text-sm text-muted-foreground flex-shrink-0">
                  {segment.totalDuration > 0 ? formatDurationInMinutes(segment.totalDuration) : '-'}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Verbose Details */}
      {verbose && (
        <div className="p-4 border rounded-md bg-muted/50">
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
                            {formatDurationInMinutes(session.durationInMinutes)}
                          </span>
                        </div>
                      ))}
                      <div className="text-sm ml-4 pt-2 border-t">
                        <span className="font-medium">Total in segment: </span>
                        <span className="font-mono">
                          {formatDurationInMinutes(segment.totalDuration)}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

