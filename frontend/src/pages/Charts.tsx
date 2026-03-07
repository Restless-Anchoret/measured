import { useState } from 'react';
import DateIntervalChooser from '@/components/DateIntervalChooser';
import ProjectFilterSelect from '@/components/ProjectFilterSelect';
import SessionsChart from '@/components/SessionsChart';
import type { DateRange } from '@/types';
import type { ProjectFilter } from '@/project_filters';

export default function Charts() {
  const [selectedInterval, setSelectedInterval] = useState<DateRange | null>(null);
  const [projectFilter, setProjectFilter] = useState<ProjectFilter | null>(null);

  return (
    <div>
      <h1 className="text-4xl font-bold mb-6">Charts</h1>
      
      <div className="mb-8 flex flex-wrap items-center gap-4">
        <DateIntervalChooser onChange={setSelectedInterval} />
        <ProjectFilterSelect onChange={setProjectFilter} />
      </div>

      {selectedInterval && projectFilter && (
        <SessionsChart dateRange={selectedInterval} projectFilter={projectFilter} />
      )}
    </div>
  );
}

