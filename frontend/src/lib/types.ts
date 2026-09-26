export interface Project {
  id: number;
  name: string;
  color: string;
  extraColor: string | null;
}

export interface Session {
  id: number;
  project_id: number;
  date: string; // ISO date string (YYYY-MM-DD)
  duration_minutes: number;
}

export interface PaginatedSessions {
  items: Session[];
  total: number;
  page: number;
  page_size: number;
}

export const IntervalKind = {
  WEEK: 'week',
  MONTH: 'month',
  YEAR: 'year',
} as const;

export type IntervalKind = typeof IntervalKind[keyof typeof IntervalKind];

export const AggregationBy = {
  DAY: 'day',
  WEEK: 'week',
  MONTH: 'month',
} as const;

export type AggregationBy = typeof AggregationBy[keyof typeof AggregationBy];

export interface DateRange {
  fromDate: Date;
  toDate: Date;
  intervalKind: IntervalKind;
  aggregationBy: AggregationBy;
}

