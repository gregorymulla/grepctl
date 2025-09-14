export interface SearchResult {
  doc_id: string;
  uri: string;
  source: string;
  modality: string;
  text_content: string;
  score: number;
  created_at?: string;
  metadata?: Record<string, any>;
}

export interface SearchFilters {
  modalities: string[];
  topK: number;
  useRerank: boolean;
  startDate?: string;
  endDate?: string;
}

export interface SearchRequest {
  query: string;
  top_k?: number;
  modalities?: string[];
  sources?: string[];
  use_rerank?: boolean;
  start_date?: string;
  end_date?: string;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query_time: number;
  query: string;
}

export interface SystemStatus {
  dataset_exists: boolean;
  document_count: number;
  index_status: Record<string, any>;
  modalities: string[];
  last_updated?: string;
}

export interface ThemeConfig {
  branding: {
    companyName: string;
    logo: string;
    favicon: string;
    tagline: string;
  };
  colors: Record<string, string>;
  darkMode?: {
    enabled: boolean;
    colors: Record<string, string>;
  };
  layout?: {
    maxWidth: string;
    borderRadius: string;
    fontFamily: string;
    headerHeight: string;
  };
  features?: {
    darkMode: boolean;
    exportEnabled: boolean;
    advancedFilters: boolean;
    keyboardShortcuts: boolean;
  };
}