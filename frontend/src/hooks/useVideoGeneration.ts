import { useState, useCallback } from 'react'
import { videoApi } from '@/lib/api'
import { JobStatusResponse, JobData } from '@/types/api'

export interface UseVideoGenerationReturn {
  generateVideo: (file: File) => Promise<JobStatusResponse>
  getJobStatus: (jobId: string) => Promise<JobStatusResponse>
  cancelJob: (jobId: string, reason?: string) => Promise<void>
  downloadVideo: (jobId: string, download?: boolean) => Promise<Blob>
  getVideoUrl: (jobId: string, download?: boolean) => string
  isLoading: boolean
  error: string | null
  currentJob: JobStatusResponse | null
}

export const useVideoGeneration = (): UseVideoGenerationReturn => {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentJob, setCurrentJob] = useState<JobStatusResponse | null>(null)

  const generateVideo = useCallback(async (file: File): Promise<JobStatusResponse> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await videoApi.generateVideo(file)
      setCurrentJob(response)
      return response
    } catch (err: any) {
      // Handle 404/Not Found error with a friendlier message
      let errorMessage = 'Failed to generate video'
      if (err?.response?.status === 404) {
        errorMessage = 'API endpoint not found (404)'
      } else if (err instanceof Error) {
        errorMessage = err.message
      }
      setError(errorMessage)
      return Promise.reject(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }, [])

  const getJobStatus = useCallback(async (jobId: string): Promise<JobStatusResponse> => {
    try {
      const response = await videoApi.getJobStatus(jobId)
      setCurrentJob(response)
      return response
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get job status'
      setError(errorMessage)
      throw new Error(errorMessage)
    }
  }, [])

  const cancelJob = useCallback(async (jobId: string, reason = 'User requested cancellation'): Promise<void> => {
    setIsLoading(true)
    setError(null)

    try {
      await videoApi.cancelJob(jobId, reason)
      // Refresh current job status if it's the same job
      if (currentJob?.job_id === jobId) {
        const updatedJob = await videoApi.getJobStatus(jobId)
        setCurrentJob(updatedJob)
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to cancel job'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }, [currentJob])

  const downloadVideo = useCallback(async (jobId: string, download = false): Promise<Blob> => {
    try {
      return await videoApi.downloadVideo(jobId, download)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to download video'
      setError(errorMessage)
      throw new Error(errorMessage)
    }
  }, [])

  const getVideoUrl = useCallback((jobId: string, download = false): string => {
    return videoApi.getVideoUrl(jobId, download)
  }, [])

  return {
    generateVideo,
    getJobStatus,
    cancelJob,
    downloadVideo,
    getVideoUrl,
    isLoading,
    error,
    currentJob,
  }
}
