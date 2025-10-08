'use client'

import { useState } from 'react'
import { RefreshCw, Clock, CheckCircle, XCircle, AlertCircle, Square, Loader2 } from 'lucide-react'
import { useJobs } from '@/hooks/useJobs'
import { JobData } from '@/types/api'

interface JobsListProps {
    showActiveOnly?: boolean
    onJobSelect?: (jobId: string) => void
}

export const JobsList = ({ showActiveOnly = false, onJobSelect }: JobsListProps) => {
    const { jobs, activeJobs, isLoading, error, refetchJobs } = useJobs()
    const [selectedJob, setSelectedJob] = useState<string | null>(null)

    const displayJobs = showActiveOnly ? activeJobs : jobs

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'pending':
                return <Clock className="h-4 w-4 text-yellow-500" />
            case 'processing':
                return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
            case 'completed':
                return <CheckCircle className="h-4 w-4 text-green-500" />
            case 'completed_with_errors':
                return <AlertCircle className="h-4 w-4 text-orange-500" />
            case 'failed':
                return <XCircle className="h-4 w-4 text-red-500" />
            case 'cancelled':
                return <Square className="h-4 w-4 text-gray-500" />
            default:
                return <Clock className="h-4 w-4 text-gray-500" />
        }
    }

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'pending':
                return 'bg-yellow-50 border-yellow-200 hover:bg-yellow-100'
            case 'processing':
                return 'bg-blue-50 border-blue-200 hover:bg-blue-100'
            case 'completed':
                return 'bg-green-50 border-green-200 hover:bg-green-100'
            case 'completed_with_errors':
                return 'bg-orange-50 border-orange-200 hover:bg-orange-100'
            case 'failed':
                return 'bg-red-50 border-red-200 hover:bg-red-100'
            case 'cancelled':
                return 'bg-gray-50 border-gray-200 hover:bg-gray-100'
            default:
                return 'bg-gray-50 border-gray-200 hover:bg-gray-100'
        }
    }

    const handleJobClick = (job: JobData) => {
        setSelectedJob(job.job_id)
        onJobSelect?.(job.job_id)
    }

    const formatDate = (dateString?: string) => {
        if (!dateString) return 'N/A'
        try {
            return new Date(dateString).toLocaleString()
        } catch {
            return dateString
        }
    }

    if (error) {
        return (
            <div className="bg-white rounded-lg shadow-md p-6">
                <div className="flex items-center space-x-2 text-red-600">
                    <AlertCircle className="h-5 w-5" />
                    <span>Error loading jobs: {error}</span>
                </div>
            </div>
        )
    }

    return (
        <div className="bg-white rounded-lg shadow-md">
            <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                    <h2 className="text-lg font-semibold text-gray-900">
                        {showActiveOnly ? 'Active Jobs' : 'Recent Jobs'}
                    </h2>
                    <button
                        onClick={refetchJobs}
                        disabled={isLoading}
                        className="flex items-center space-x-2 px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                        <span>Refresh</span>
                    </button>
                </div>
            </div>

            <div className="divide-y divide-gray-200">
                {displayJobs.length === 0 ? (
                    <div className="px-6 py-8 text-center text-gray-500">
                        {showActiveOnly ? 'No active jobs' : 'No jobs found'}
                    </div>
                ) : (
                    displayJobs.map((job) => (
                        <div
                            key={job.job_id}
                            className={`
                px-6 py-4 cursor-pointer transition-colors
                ${getStatusColor(job.status)}
                ${selectedJob === job.job_id ? 'ring-2 ring-blue-500' : ''}
              `}
                            onClick={() => handleJobClick(job)}
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex items-start space-x-3">
                                    {getStatusIcon(job.status)}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center space-x-2">
                                            <p className="text-sm font-medium text-gray-900 truncate">
                                                Job {job.job_id.slice(0, 8)}...
                                            </p>
                                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize">
                                                {job.status.replace('_', ' ')}
                                            </span>
                                        </div>

                                        {job.message && (
                                            <p className="text-sm text-gray-600 mt-1 truncate">
                                                {job.message}
                                            </p>
                                        )}

                                        <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                                            {job.progress !== undefined && (
                                                <span>Progress: {job.progress}%</span>
                                            )}
                                            <span>Updated: {formatDate(job.updated_at)}</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex-shrink-0">
                                    {job.status === 'processing' && (
                                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                            Running
                                        </span>
                                    )}
                                    {job.status === 'completed' && (
                                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                            Done
                                        </span>
                                    )}
                                    {job.status === 'failed' && (
                                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                            Failed
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {displayJobs.length > 0 && (
                <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
                    <div className="flex items-center justify-between text-sm text-gray-600">
                        <span>
                            Showing {displayJobs.length} job{displayJobs.length !== 1 ? 's' : ''}
                        </span>
                        {showActiveOnly && (
                            <span>
                                {activeJobs.length} active • {jobs.length - activeJobs.length} completed
                            </span>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
