import { useState } from 'react';
import DateIntervalChooser from '@/components/DateIntervalChooser';
import type { DateRange } from '@/types';

export default function Charts() {
  const [selectedInterval, setSelectedInterval] = useState<DateRange | null>(null);

  return (
    <div>
      <h1 className="text-4xl font-bold mb-6">Charts</h1>
      
      <div className="mb-8">
        <DateIntervalChooser onChange={setSelectedInterval} />
      </div>

      {/* Display selected interval for demonstration */}
      {selectedInterval && (
        <div className="mt-6 p-4 border rounded-md bg-muted/50">
          <h2 className="text-lg font-semibold mb-2">Selected Interval:</h2>
          <div className="space-y-1 text-sm">
            <p>
              <span className="font-medium">From Date:</span>{' '}
              {selectedInterval.fromDate.toLocaleDateString()}
            </p>
            <p>
              <span className="font-medium">To Date (exclusive):</span>{' '}
              {selectedInterval.toDate.toLocaleDateString()}
            </p>
            <p>
              <span className="font-medium">Interval Kind:</span>{' '}
              {selectedInterval.intervalKind}
            </p>
            <p>
              <span className="font-medium">Aggregation By:</span>{' '}
              {selectedInterval.aggregationBy}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

