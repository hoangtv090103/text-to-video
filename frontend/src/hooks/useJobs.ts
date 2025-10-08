import { useState, useEffect, useCallback } from 'react'
import { videoApi } from '@/lib/api'
import { JobData, JobsListResponse, ActiveJobsResponse } from '@/types/api'

export interface UseJobsReturn {
  jobs: JobData[]
  activeJobs: JobData[]
  isLoading: boolean
  error: string | null
  refetchJobs: () => Promise<void>
  refetchActiveJobs: () => Promise<void>
}

export const useJobs = (): UseJobsReturn => {
  const [jobs, setJobs] = useState<JobData[]>([])
  const [activeJobs, setActiveJobs] = useState<JobData[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchJobs = useCallback(async () => {
    try {
      const response = await videoApi.listJobs(20)
      setJobs(response.jobs)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch jobs'
      setError(errorMessage)
    }
  }, [])

  const fetchActiveJobs = useCallback(async () => {
    try {
      const response = await videoApi.getActiveJobs(50)
      setActiveJobs(response.active_jobs)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch active jobs'
      setError(errorMessage)
    }
  }, [])

  const refetchJobs = useCallback(async () => {
    setIsLoading(true)
    await Promise.all([fetchJobs(), fetchActiveJobs()])
    setIsLoading(false)
  }, [fetchJobs, fetchActiveJobs])

  const refetchActiveJobs = useCallback(async () => {
    await fetchActiveJobs()
  }, [fetchActiveJobs])

  useEffect(() => {
    refetchJobs()
  }, [refetchJobs])

  return {
    jobs,
    activeJobs,
    isLoading,
    error,
    refetchJobs,
    refetchActiveJobs,
  }
}

