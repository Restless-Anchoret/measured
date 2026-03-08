import { useState, useMemo, useEffect } from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useProjects } from '@/hooks/useProjects';
import {
  AllProjectsFilter,
  SingleProjectFilter,
  HARDCODED_PROJECT_GROUP_FILTERS,
  type ProjectFilter,
} from '@/lib/project_filters';

interface ProjectFilterSelectProps {
  onChange: (filter: ProjectFilter) => void;
}

const ALL_FILTER = new AllProjectsFilter();

function ColorDot({ color, extraColor }: { color: string; extraColor: string | null }) {
  const background = extraColor
    ? `linear-gradient(to right, ${color} 50%, ${extraColor} 50%)`
    : color;

  return (
    <span
      className="inline-block h-3 w-3 shrink-0 rounded-full"
      style={{ background }}
    />
  );
}

function FilterItem({ filter }: { filter: ProjectFilter }) {
  return (
    <SelectItem value={filter.filterKey()}>
      <span className="flex items-center gap-2">
        <ColorDot color={filter.color()} extraColor={filter.extraColor()} />
        {filter.name()}
      </span>
    </SelectItem>
  );
}

export default function ProjectFilterSelect({ onChange }: ProjectFilterSelectProps) {
  const { projects, loading } = useProjects();
  const [selectedKey, setSelectedKey] = useState(ALL_FILTER.filterKey());

  const projectFilters = useMemo(() => {
    return projects.map((project) => new SingleProjectFilter(project));
  }, [projects]);

  const allFilters = useMemo(() => {
    const filters: ProjectFilter[] = [ALL_FILTER];

    for (const group of HARDCODED_PROJECT_GROUP_FILTERS) {
      filters.push(group);
    }

    for (const projectFilter of projectFilters) {
      filters.push(projectFilter);
    }

    return filters;
  }, [projects]);

  const filtersMap = useMemo(() => {
    const map = new Map<string, ProjectFilter>();
    for (const filter of allFilters) {
      map.set(filter.filterKey(), filter);
    }
    return map;
  }, [allFilters]);

  useEffect(() => {
    onChange(ALL_FILTER);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleChange = (key: string) => {
    setSelectedKey(key);
    const filter = filtersMap.get(key);
    if (filter) onChange(filter);
  };

  return (
    <Select value={selectedKey} onValueChange={handleChange}>
      <SelectTrigger className="h-10 w-[200px]" disabled={loading}>
        <SelectValue placeholder={loading ? 'Loading…' : 'Select project'} />
      </SelectTrigger>
      <SelectContent>
        <FilterItem filter={ALL_FILTER} />

        <SelectSeparator />

        {HARDCODED_PROJECT_GROUP_FILTERS.map((groupFilter) => (
          <FilterItem key={groupFilter.filterKey()} filter={groupFilter} />
        ))}

        <SelectSeparator />

        {projectFilters.map((projectFilter) => (
          <FilterItem key={projectFilter.filterKey()} filter={projectFilter} />
        ))}
      </SelectContent>
    </Select>
  );
}
