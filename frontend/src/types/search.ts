export type SearchMatchType =
  | 'title'
  | 'transcript'
  | 'summary'
  | 'action_item'
  | 'chapter'
  | 'participant';

export interface SearchResultItem {
  meeting_id: number;
  meeting_title: string;
  meeting_status: string;
  recorded_at: string;
  match_type: SearchMatchType | string;
  matched_text: string;
  timestamp_ms: number | null;
  relevance: number;
}

export interface SearchResponse {
  items: SearchResultItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
