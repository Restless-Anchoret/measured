import { useState } from 'react';
import DateIntervalChooser from '@/components/DateIntervalChooser';
import SessionsChart from '@/components/SessionsChart';
import type { DateRange } from '@/types';

export default function Charts() {
  const [selectedInterval, setSelectedInterval] = useState<DateRange | null>(null);

  return (
    <div>
      <h1 className="text-4xl font-bold mb-6">Charts</h1>
      
      <div className="mb-8">
        <DateIntervalChooser onChange={setSelectedInterval} />
      </div>

      {selectedInterval && <SessionsChart dateRange={selectedInterval} />}
    </div>
  );
}

