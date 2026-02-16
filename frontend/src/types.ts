export interface Project {
  id: number;
  name: string;
  color: string;
  extraColor: string | null;
}

export interface Session {
  id: number;
  project_id: number;
  start_time: string; // ISO datetime string
  end_time: string | null; // ISO datetime string or null
  created_at: string; // ISO datetime string
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

