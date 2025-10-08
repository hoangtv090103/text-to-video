export interface JobStatus {
  PENDING: 'pending'
  PROCESSING: 'processing'
  COMPLETED: 'completed'
  COMPLETED_WITH_ERRORS: 'completed_with_errors'
  FAILED: 'failed'
  CANCELLED: 'cancelled'
}

export type JobStatusType = keyof JobStatus

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

export interface JobStatusResponse {
  job_id: string
  status: JobStatusType
  message?: string
  progress?: number
  updated_at?: string
  completed_at?: string
  result?: any
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
