import type { DateRange } from '@/types';

interface SessionsChartProps {
  dateRange: DateRange;
}

export default function SessionsChart({ dateRange }: SessionsChartProps) {
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
    </div>
  );
}

