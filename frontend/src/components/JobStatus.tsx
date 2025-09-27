'use client'

import { useState, useEffect } from 'react'
import { Play, Pause, Square, CheckCircle, XCircle, AlertCircle, Clock, Loader2 } from 'lucide-react'
import { useVideoGeneration } from '@/hooks/useVideoGeneration'
import { JobStatusResponse } from '@/types/api'

interface JobStatusProps {
    jobId: string
    onStatusChange?: (status: JobStatusResponse) => void
}

export const JobStatus = ({ jobId, onStatusChange }: JobStatusProps) => {
    const [job, setJob] = useState<JobStatusResponse | null>(null)
    const [isPolling, setIsPolling] = useState(true)
    const { getJobStatus, cancelJob } = useVideoGeneration()

    // Poll for job status updates
    useEffect(() => {
        if (!isPolling || !jobId) return

        const pollStatus = async () => {
            try {
                const status = await getJobStatus(jobId)
                setJob(status)
                onStatusChange?.(status)

                // Stop polling if job is completed or failed
                if (['completed', 'completed_with_errors', 'failed', 'cancelled'].includes(status.status)) {
                    setIsPolling(false)
                }
            } catch (error) {
                console.error('Failed to get job status:', error)
                setIsPolling(false)
            }
        }

        // Poll immediately and then every 2 seconds
        pollStatus()
        const interval = setInterval(pollStatus, 2000)

        return () => clearInterval(interval)
    }, [jobId, isPolling, getJobStatus, onStatusChange])

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'pending':
                return <Clock className="h-5 w-5 text-yellow-500" />
            case 'processing':
                return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
            case 'completed':
                return <CheckCircle className="h-5 w-5 text-green-500" />
            case 'completed_with_errors':
                return <AlertCircle className="h-5 w-5 text-orange-500" />
            case 'failed':
                return <XCircle className="h-5 w-5 text-red-500" />
            case 'cancelled':
                return <Square className="h-5 w-5 text-gray-500" />
            default:
                return <Clock className="h-5 w-5 text-gray-500" />
        }
    }

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'pending':
                return 'bg-yellow-100 border-yellow-300'
            case 'processing':
                return 'bg-blue-100 border-blue-300'
            case 'completed':
                return 'bg-green-100 border-green-300'
            case 'completed_with_errors':
                return 'bg-orange-100 border-orange-300'
            case 'failed':
                return 'bg-red-100 border-red-300'
            case 'cancelled':
                return 'bg-gray-100 border-gray-300'
            default:
                return 'bg-gray-100 border-gray-300'
        }
    }

    const getProgressWidth = (progress?: number) => {
        return progress ? `${Math.min(progress, 100)}%` : '0%'
    }

    const handleCancel = async () => {
        try {
            await cancelJob(jobId)
            setIsPolling(false)
        } catch (error) {
            console.error('Failed to cancel job:', error)
        }
    }

    if (!job) {
        return (
            <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center space-x-3">
                    <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
                    <span className="text-gray-600">Loading job status...</span>
                </div>
            </div>
        )
    }

    return (
        <div className={`bg-white rounded-lg shadow-md p-6 border-l-4 ${getStatusColor(job.status)}`}>
            <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3">
                    {getStatusIcon(job.status)}
                    <div className="flex-1">
                        <h3 className="text-lg font-semibold text-gray-900 mb-1">
                            Job {jobId.slice(0, 8)}...
                        </h3>

                        <div className="space-y-2">
                            <div className="flex items-center space-x-2">
                                <span className="text-sm font-medium text-gray-700 capitalize">
                                    Status: {job.status.replace('_', ' ')}
                                </span>
                                {job.progress !== undefined && (
                                    <span className="text-sm text-gray-500">({job.progress}%)</span>
                                )}
                            </div>

                            {job.message && (
                                <p className="text-sm text-gray-600">{job.message}</p>
                            )}

                            {job.progress !== undefined && (
                                <div className="w-full bg-gray-200 rounded-full h-2">
                                    <div
                                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                        style={{ width: getProgressWidth(job.progress) }}
                                    />
                                </div>
                            )}

                            <div className="flex items-center space-x-4 text-xs text-gray-500">
                                {job.updated_at && (
                                    <span>Updated: {new Date(job.updated_at).toLocaleString()}</span>
                                )}
                                {job.completed_at && (
                                    <span>Completed: {new Date(job.completed_at).toLocaleString()}</span>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                <div className="flex items-center space-x-2">
                    {job.status === 'processing' && (
                        <button
                            onClick={handleCancel}
                            className="px-3 py-1 text-sm bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                        >
                            Cancel
                        </button>
                    )}

                    {isPolling && ['pending', 'processing'].includes(job.status) && (
                        <button
                            onClick={() => setIsPolling(false)}
                            className="px-3 py-1 text-sm bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
                        >
                            Stop Updates
                        </button>
                    )}

                    {!isPolling && ['pending', 'processing'].includes(job.status) && (
                        <button
                            onClick={() => setIsPolling(true)}
                            className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                        >
                            Resume Updates
                        </button>
                    )}
                </div>
            </div>

            {job.result && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Result Details:</h4>
                    <pre className="text-xs text-gray-600 bg-gray-50 p-3 rounded overflow-auto max-h-32">
                        {JSON.stringify(job.result, null, 2)}
                    </pre>
                </div>
            )}
        </div>
    )
}
