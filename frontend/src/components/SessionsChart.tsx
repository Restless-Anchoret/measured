import { useMemo } from 'react';
import type { DateRange } from '@/types';
import { useSessions } from '@/hooks/useSessions';

interface SessionsChartProps {
  dateRange: DateRange;
}

export default function SessionsChart({ dateRange }: SessionsChartProps) {
  const { sessionsPage, loading, error } = useSessions({
    page: 1,
    pageSize: 1000,
    minStartTime: dateRange.fromDate,
    maxStartTime: dateRange.toDate,
  });

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
    </div>
  );
}

