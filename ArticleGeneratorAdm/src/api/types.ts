/**
 * 全局 API 类型定义
 */

export interface Hotspot {
  id: number;
  title: string;
  source: string;
  heat: number;
  summary?: string;
  url?: string;
  status: string;
  created_at: string;
}

export interface StyleProfile {
  thinking_pattern: string;
  structure_pattern: string;
  sentence_pattern: string;
  vocabulary_pattern: string;
  evidence_type: string;
  taboos: string;
  blank_leaving: string;
}

export interface Account {
  id: number;
  platform: string;
  account_name: string;
  lora_path?: string;
  sample_articles?: string;
  style_profile?: string;
  style_profile_updated_at?: string;
  style_profile_structured?: StyleProfile | null;
  style_profile_version?: number;
  style_profile_status?: string;
  created_at: string;
}

export interface HotspotSource {
  id: number;
  name: string;
  type: string;
  config?: string;
  enabled: boolean;
  created_at: string;
}

export interface Article {
  id: number;
  hotspot_id: number;
  account_id: number;
  title?: string;
  content: string;
  status: string;
  refine_history?: string;
  quality_score?: number;
  compliance_score?: number;
  review_notes?: string;
  published_at?: string;
  created_at: string;
  updated_at: string;
  hotspot?: Hotspot;
  account?: Account;
}

export interface Provider {
  id: number;
  name: string;
  base_url: string;
  api_key: string;
  models?: string;
  enabled: boolean;
  created_at: string;
}

export interface ScenarioConfig {
  id: number;
  scenario: string;
  provider_id: number;
  model: string;
  system_prompt_template?: string;
  params?: string;
  priority: number;
  description?: string;
  sort_order?: number;
  enabled: boolean;
  provider?: Provider;
  created_at: string;
}

export interface ReferenceArticle {
  id: number;
  account_id: number;
  title: string;
  content: string;
  source_url?: string;
  embedding?: string;
  is_benchmark: boolean;
  created_at: string;
}

export interface GenerationLog {
  id: number;
  scenario: string;
  provider_id?: number;
  model?: string;
  prompt_tokens: number;
  completion_tokens: number;
  latency_ms: number;
  status: string;
  error_message?: string;
  created_at: string;
}

export interface DirectionItem {
  id: string;
  title: string;
}

export interface OutlinePoint {
  order: number;
  point: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
}

export interface UnifiedTaskItem {
  task_id: string;
  task_type: string;
  status: string;
  target: string;
  article_id: number | null;
  account_name?: string;
  extra_info?: string;
  error_message: string | null;
  created_at: string;
  updated_at?: string;
}

export interface UnifiedTasksResponse {
  tasks: UnifiedTaskItem[];
  running_count: number;
  pending_count: number;
  completed_count: number;
}
