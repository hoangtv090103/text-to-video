export type JobStatusType =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'completed_with_errors'
  | 'failed'
  | 'cancelled'

export interface JobData {
  job_id: string
  status: JobStatusType
  message?: string
  progress?: number
  updated_at?: string
  completed_at?: string
  result?: any
  segments?: Record<string, any>
}

export interface VideoResult {
  video_path: string
  video_url?: string
  download_url?: string
  duration?: number
  file_size_mb?: number
  status: string
}

export interface JobResult {
  job_id: string
  status: string
  message: string
  processing_time: number
  total_scenes: number
  successful_tasks: number
  failed_tasks: number
  scenes: any[]
  script_scenes: any[]
  video?: VideoResult
  error?: string
}

export interface JobStatusResponse {
  job_id: string
  status: JobStatusType
  message?: string
  progress?: number
  updated_at?: string
  completed_at?: string
  result?: JobResult
}

export interface VideoGenerationRequest {
  file: File
}

export interface JobsListResponse {
  jobs: JobData[]
  total_count: number
}

export interface ActiveJobsResponse {
  active_jobs: JobData[]
  total_count: number
  limit: number
}

export interface CleanupResponse {
  message: string
  job_cleanup: {
    expired_jobs_cleaned: number
    jobs_remaining: number
    jobs_removed: number
    queue_length: number
    timestamp: string
  }
  timestamp: number
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy'
  service: string
  dependencies: {
    tts_service: string
    llm_service: string
    redis_service: string
  }
  circuit_breakers: {
    tts: string
    llm: string
    redis: string
  }
  timestamp: number
}

export interface ApiError {
  detail: string
  status_code?: number
}

// LLM Admin Types
export interface LLMConfig {
  provider: string
  base_url?: string
  has_api_key: boolean
  model?: string
}

export interface ModelInfo {
  id: string
  name: string
  description?: string
}

export interface FetchModelsResponse {
  success: boolean
  models: ModelInfo[]
  error?: string
}

export interface TestModelResponse {
  success: boolean
  message: string
  response?: string
  latency_ms?: number
}

// Admin LLM Configuration Types
export interface LLMProviderInfo {
  provider: string
  supported: boolean
  required_packages: string[]
  configuration: Record<string, any>
}

export interface LLMProvidersResponse {
  available_providers: string[]
  current_provider: string
  current_config: LLMProviderInfo
  supported_models: Record<string, string[]>
}

export interface LLMHealthResponse {
  provider: string
  healthy: boolean
  provider_info: LLMProviderInfo
  current_model: string
  timestamp: number
}

export interface LLMTestResponse {
  success: boolean
  provider: string
  model: string
  test_response: string
  error?: string
  timestamp: number
}

export interface SetProviderResponse {
  message: string
  provider: string
  note: string
}

// Model Cache Types
export interface ModelCacheInfo {
  cached_providers: string[]
  cache_timestamps: Record<string, string>
  cache_duration_hours: number
}

export interface CacheClearResponse {
  message: string
  provider?: string
  cache_info: ModelCacheInfo
  timestamp: number
}

export interface CacheInfoResponse {
  cache_info: ModelCacheInfo
  timestamp: number
}

export interface RefreshModelsResponse {
  message: string
  provider: string
  models_count: number
  models: string[]
  cache_info: ModelCacheInfo
  timestamp: number
}
