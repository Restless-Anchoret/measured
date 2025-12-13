export interface Project {
  id: number;
  name: string;
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

