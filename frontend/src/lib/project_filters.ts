import type { Project } from '@/lib/types';

export interface ProjectFilter {
  filterKey(): string;
  projectIds(): number[];
  name(): string;
  color(): string;
  extraColor(): string | null;
}

export class SingleProjectFilter implements ProjectFilter {
  readonly project: Project;

  constructor(project: Project) {
    this.project = project;
  }

  filterKey(): string {
    return `project:${this.project.id}`;
  }

  projectIds(): number[] {
    return [this.project.id];
  }

  name(): string {
    return this.project.name;
  }

  color(): string {
    return this.project.color;
  }

  extraColor(): string | null {
    return this.project.extraColor;
  }
}

export class ProjectsGroupFilter implements ProjectFilter {
  readonly _ids: number[];
  readonly _name: string;
  readonly _color: string;
  readonly _extraColor: string | null;

  constructor(ids: number[], name: string, color: string, extraColor: string | null) {
    this._ids = ids;
    this._name = name;
    this._color = color;
    this._extraColor = extraColor;
  }

  filterKey(): string {
    return `group:${this._name}`;
  }

  projectIds(): number[] {
    return this._ids;
  }

  name(): string {
    return this._name;
  }

  color(): string {
    return this._color;
  }

  extraColor(): string | null {
    return this._extraColor;
  }
}

export class AllProjectsFilter implements ProjectFilter {
  filterKey(): string {
    return 'all';
  }

  projectIds(): number[] {
    return [];
  }

  name(): string {
    return 'All projects';
  }

  color(): string {
    return '#ffffff';
  }

  extraColor(): string | null {
    return null;
  }
}

// TODO: move group definitions to the backend
export const HARDCODED_PROJECT_GROUP_FILTERS: ProjectsGroupFilter[] = [
  new ProjectsGroupFilter([9, 10, 11], 'Reading', '#068a19', null),
  new ProjectsGroupFilter([3, 4, 15], 'Sport', '#f59120', null),
  new ProjectsGroupFilter([1, 2, 5, 6], 'Rest', '#8a07db', '#f52020'),
];
