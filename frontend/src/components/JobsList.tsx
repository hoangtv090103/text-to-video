'use client'

import { useState, useEffect } from 'react'
import { Clock, CheckCircle, XCircle, AlertCircle, AlertTriangle, Loader2, Eye, Download, X } from 'lucide-react'
import { useJobs } from '@/hooks/useJobs'
import { JobData } from '@/types/api'
import { VideoPlayer } from './VideoPlayer'

interface JobDetailModalProps {
    job: JobData
    onClose: () => void
}

const JobDetailModal = ({ job, onClose }: JobDetailModalProps) => {
    // Check multiple possible locations for video data
    const videoData = job.result?.video
    const hasVideo = videoData && videoData.video_url && videoData.status !== 'error'
    const videoUrl = videoData?.video_url
    const downloadUrl = videoData?.download_url || `${videoData?.video_url}?download=true`
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

    // Debug logging
    useEffect(() => {
        console.log('📹 Job video status:', {
            job_id: job.job_id,
            status: job.status,
            hasResult: !!job.result,
            hasVideo: hasVideo,
            videoUrl: videoUrl,
            videoStatus: videoData?.status,
            videoPath: videoData?.video_path
        })
    }, [job.job_id, job.status, hasVideo, videoUrl, videoData])

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50" onClick={onClose}>
            <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between z-10">
                    <div>
                        <h2 className="text-2xl font-bold text-gray-900">Job Details</h2>
                        <p className="text-sm text-gray-600">ID: {job.job_id}</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                        <X className="h-6 w-6 text-gray-600" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6">
                    {/* Warning for completed jobs without result data */}
                    {job.status === 'completed' && !job.result && (
                        <div className="bg-amber-50 border border-amber-300 rounded-lg p-4">
                            <div className="flex items-start space-x-3">
                                <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5" />
                                <div>
                                    <p className="font-medium text-amber-900">Result Data Missing</p>
                                    <p className="text-sm text-amber-700 mt-1">
                                        This job completed but result data was not saved.
                                        Backend logs may contain more information.
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Video Player or No Video Message */}
                    {hasVideo ? (
                        <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl p-6 border border-gray-200">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-lg font-semibold text-gray-900">Generated Video</h3>
                                <a
                                    href={`${apiUrl}${downloadUrl}`}
                                    download={`video_${job.job_id}.mp4`}
                                    className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                                >
                                    <Download className="h-4 w-4" />
                                    <span>Download</span>
                                </a>
                            </div>

                            {/* Video Player */}
                            <div className="relative rounded-lg overflow-hidden bg-black">
                                <video
                                    controls
                                    controlsList="nodownload"
                                    preload="metadata"
                                    playsInline
                                    className="w-full max-h-[500px] mx-auto"
                                    poster=""
                                    onLoadedMetadata={(e) => {
                                        const video = e.currentTarget
                                        console.log('🎬 Video metadata loaded:', {
                                            duration: video.duration,
                                            videoWidth: video.videoWidth,
                                            videoHeight: video.videoHeight,
                                            readyState: video.readyState
                                        })
                                    }}
                                    onError={(e) => {
                                        console.error('❌ Video error:', e)
                                    }}
                                >
                                    <source src={`${apiUrl}${videoUrl}`} type="video/mp4" />
                                    Your browser does not support the video tag.
                                </video>
                            </div>

                            {/* Video Info */}
                            <div className="mt-4 flex items-center justify-center space-x-6 text-sm text-gray-600">
                                {videoData.duration && (
                                    <div className="flex items-center space-x-1">
                                        <Clock className="h-4 w-4" />
                                        <span>{videoData.duration.toFixed(1)}s</span>
                                    </div>
                                )}
                                {videoData.duration_seconds && !videoData.duration && (
                                    <div className="flex items-center space-x-1">
                                        <Clock className="h-4 w-4" />
                                        <span>{videoData.duration_seconds.toFixed(1)}s</span>
                                    </div>
                                )}
                                {videoData.file_size_mb && (
                                    <div className="flex items-center space-x-1">
                                        <Download className="h-4 w-4" />
                                        <span>{videoData.file_size_mb.toFixed(2)} MB</span>
                                    </div>
                                )}
                                <div className="flex items-center space-x-1">
                                    <CheckCircle className="h-4 w-4 text-green-600" />
                                    <span className="capitalize text-green-600">{videoData.status || 'ready'}</span>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className={`border rounded-lg p-6 text-center ${videoData?.status === 'error' || job.status === 'failed'
                            ? 'bg-red-50 border-red-200'
                            : job.status === 'processing' || job.status === 'pending'
                                ? 'bg-blue-50 border-blue-200'
                                : 'bg-yellow-50 border-yellow-200'
                            }`}>
                            {videoData?.status === 'error' || job.status === 'failed' ? (
                                <XCircle className="h-12 w-12 text-red-600 mx-auto mb-3" />
                            ) : job.status === 'processing' || job.status === 'pending' ? (
                                <Loader2 className="h-12 w-12 text-blue-600 mx-auto mb-3 animate-spin" />
                            ) : (
                                <AlertTriangle className="h-12 w-12 text-yellow-600 mx-auto mb-3" />
                            )}

                            <h3 className={`text-lg font-semibold mb-2 ${videoData?.status === 'error' || job.status === 'failed'
                                ? 'text-red-900'
                                : job.status === 'processing' || job.status === 'pending'
                                    ? 'text-blue-900'
                                    : 'text-yellow-900'
                                }`}>
                                {videoData?.status === 'error' || job.status === 'failed'
                                    ? 'Video Generation Error'
                                    : job.status === 'processing' || job.status === 'pending'
                                        ? 'Video Processing'
                                        : 'No Video Available'}
                            </h3>

                            <p className={`text-sm ${videoData?.status === 'error' || job.status === 'failed'
                                ? 'text-red-700'
                                : job.status === 'processing' || job.status === 'pending'
                                    ? 'text-blue-700'
                                    : 'text-yellow-700'
                                }`}>
                                {videoData?.error
                                    ? videoData.error
                                    : job.status === 'processing' || job.status === 'pending'
                                        ? 'Video is still being generated. Please refresh in a moment...'
                                        : job.status === 'failed'
                                            ? 'Video generation failed. Please check logs or try again.'
                                            : !job.result
                                                ? 'Result data missing. Backend may need to be checked.'
                                                : 'Video not available for this job.'}
                            </p>

                            {/* Show additional error details if available */}
                            {job.result?.errors && job.result.errors.length > 0 && (
                                <div className="mt-4 text-left bg-white rounded-lg p-3 border border-red-300">
                                    <p className="text-xs font-medium text-red-900 mb-2">Error Details:</p>
                                    <ul className="text-xs text-red-700 space-y-1 list-disc list-inside">
                                        {job.result.errors.map((error: any, idx: number) => (
                                            <li key={idx}>{typeof error === 'string' ? error : JSON.stringify(error)}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Job Information */}
                    <div className="bg-gray-50 rounded-lg p-4">
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">Information</h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <p className="text-sm text-gray-600">Status</p>
                                <p className="text-base font-medium text-gray-900 capitalize">
                                    {job.status.replace('_', ' ')}
                                </p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-600">Progress</p>
                                <p className="text-base font-medium text-gray-900">
                                    {job.progress !== undefined ? `${job.progress}%` : 'N/A'}
                                </p>
                            </div>
                            {job.updated_at && (
                                <div>
                                    <p className="text-sm text-gray-600">Last Updated</p>
                                    <p className="text-base font-medium text-gray-900">
                                        {new Date(job.updated_at).toLocaleString(undefined, {
                                            year: 'numeric',
                                            month: '2-digit',
                                            day: '2-digit',
                                            hour: '2-digit',
                                            minute: '2-digit',
                                            hour12: false
                                        })}
                                    </p>
                                </div>
                            )}
                            {job.completed_at && (
                                <div>
                                    <p className="text-sm text-gray-600">Completed At</p>
                                    <p className="text-base font-medium text-gray-900">
                                        {new Date(job.completed_at).toLocaleString(undefined, {
                                            year: 'numeric',
                                            month: '2-digit',
                                            day: '2-digit',
                                            hour: '2-digit',
                                            minute: '2-digit',
                                            hour12: false
                                        })}
                                    </p>
                                </div>
                            )}
                        </div>
                        {job.message && (
                            <div className="mt-4">
                                <p className="text-sm text-gray-600">Message</p>
                                <p className="text-base text-gray-900">{job.message}</p>
                            </div>
                        )}
                    </div>

                    {/* Result Details */}
                    {job.result && (
                        <div className="bg-gray-50 rounded-lg p-4">
                            <h3 className="text-lg font-semibold text-gray-900 mb-4">Processing Results</h3>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                {job.result.successful_tasks !== undefined && (
                                    <div>
                                        <p className="text-sm text-gray-600">Successful Tasks</p>
                                        <p className="text-2xl font-bold text-green-600">
                                            {job.result.successful_tasks}
                                        </p>
                                    </div>
                                )}
                                {job.result.failed_tasks !== undefined && (
                                    <div>
                                        <p className="text-sm text-gray-600">Failed Tasks</p>
                                        <p className="text-2xl font-bold text-red-600">
                                            {job.result.failed_tasks}
                                        </p>
                                    </div>
                                )}
                                {job.result.script_scenes && (
                                    <div>
                                        <p className="text-sm text-gray-600">Scenes</p>
                                        <p className="text-2xl font-bold text-blue-600">
                                            {Array.isArray(job.result.script_scenes)
                                                ? job.result.script_scenes.length
                                                : job.result.script_scenes}
                                        </p>
                                    </div>
                                )}
                                {job.result.video?.duration && (
                                    <div>
                                        <p className="text-sm text-gray-600">Duration</p>
                                        <p className="text-2xl font-bold text-purple-600">
                                            {job.result.video.duration.toFixed(1)}s
                                        </p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex justify-center gap-3 pt-4 border-t border-gray-200">
                        {hasVideo && (
                            <>
                                <a
                                    href={`${apiUrl}${videoUrl}?download=false`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg hover:from-indigo-700 hover:to-purple-700 transition-all font-medium shadow-lg"
                                >
                                    <Eye className="h-5 w-5" />
                                    <span>Open in New Tab</span>
                                </a>
                                <a
                                    href={`${apiUrl}${videoData.download_url || videoUrl}?download=true`}
                                    download
                                    className="inline-flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all font-medium shadow-lg"
                                >
                                    <Download className="h-5 w-5" />
                                    <span>Download Video</span>
                                </a>
                            </>
                        )}
                        <button
                            onClick={onClose}
                            className="inline-flex items-center space-x-2 px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
                        >
                            <X className="h-5 w-5" />
                            <span>Close</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

export const JobsList = () => {
    const { jobs, isLoading, error, refetchJobs } = useJobs()
    const [selectedJob, setSelectedJob] = useState<JobData | null>(null)
    const [filterStatus, setFilterStatus] = useState<'all' | 'active' | 'completed'>('all')

    useEffect(() => {
        refetchJobs()
        const interval = setInterval(refetchJobs, 5000)
        return () => clearInterval(interval)
    }, [refetchJobs])

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
            default:
                return <Clock className="h-5 w-5 text-gray-500" />
        }
    }

    const getStatusBadge = (status: string) => {
        const baseClasses = "px-3 py-1 rounded-full text-xs font-medium"
        switch (status) {
            case 'pending':
                return `${baseClasses} bg-yellow-100 text-yellow-800`
            case 'processing':
                return `${baseClasses} bg-blue-100 text-blue-800`
            case 'completed':
                return `${baseClasses} bg-green-100 text-green-800`
            case 'completed_with_errors':
                return `${baseClasses} bg-orange-100 text-orange-800`
            case 'failed':
                return `${baseClasses} bg-red-100 text-red-800`
            default:
                return `${baseClasses} bg-gray-100 text-gray-800`
        }
    }

    const filteredJobs = jobs.filter(job => {
        if (filterStatus === 'all') return true
        if (filterStatus === 'active') {
            return ['pending', 'processing'].includes(job.status)
        }
        if (filterStatus === 'completed') {
            return ['completed', 'completed_with_errors', 'failed', 'cancelled'].includes(job.status)
        }
        return true
    })

    if (isLoading && jobs.length === 0) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
            </div>
        )
    }

    if (error) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
                <AlertCircle className="h-8 w-8 text-red-600 mx-auto mb-2" />
                <p className="text-red-800">{error}</p>
                <button
                    onClick={refetchJobs}
                    className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                    Retry
                </button>
            </div>
        )
    }

    return (
        <>
            <div className="space-y-4">
                {/* Filter Tabs */}
                <div className="flex space-x-2 bg-gray-100 p-1 rounded-lg w-fit mx-auto">
                    <button
                        onClick={() => setFilterStatus('all')}
                        className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${filterStatus === 'all'
                            ? 'bg-white text-gray-900 shadow-sm'
                            : 'text-gray-600 hover:text-gray-900'
                            }`}
                    >
                        All ({jobs.length})
                    </button>
                    <button
                        onClick={() => setFilterStatus('active')}
                        className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${filterStatus === 'active'
                            ? 'bg-white text-gray-900 shadow-sm'
                            : 'text-gray-600 hover:text-gray-900'
                            }`}
                    >
                        Active ({jobs.filter(j => ['pending', 'processing'].includes(j.status)).length})
                    </button>
                    <button
                        onClick={() => setFilterStatus('completed')}
                        className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${filterStatus === 'completed'
                            ? 'bg-white text-gray-900 shadow-sm'
                            : 'text-gray-600 hover:text-gray-900'
                            }`}
                    >
                        Completed ({jobs.filter(j => ['completed', 'completed_with_errors'].includes(j.status)).length})
                    </button>
                </div>

                {/* Jobs Grid */}
                {filteredJobs.length === 0 ? (
                    <div className="text-center py-12 bg-white rounded-lg shadow-md">
                        <p className="text-gray-600">No jobs found</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {filteredJobs.map((job) => (
                            <div
                                key={job.job_id}
                                className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow p-6 border border-gray-200 cursor-pointer"
                                onClick={() => setSelectedJob(job)}
                            >
                                <div className="flex items-start justify-between mb-4">
                                    {getStatusIcon(job.status)}
                                    <span className={getStatusBadge(job.status)}>
                                        {job.status.replace('_', ' ')}
                                    </span>
                                </div>

                                <div className="space-y-2">
                                    <p className="text-sm font-mono text-gray-600">
                                        {job.job_id.slice(0, 8)}...
                                    </p>

                                    {job.progress !== undefined && (
                                        <div>
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="text-xs text-gray-600">Progress</span>
                                                <span className="text-xs font-medium text-gray-900">
                                                    {job.progress}%
                                                </span>
                                            </div>
                                            <div className="w-full bg-gray-200 rounded-full h-2">
                                                <div
                                                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                                    style={{ width: `${job.progress}%` }}
                                                />
                                            </div>
                                        </div>
                                    )}

                                    {job.message && (
                                        <p className="text-xs text-gray-600 line-clamp-2">
                                            {job.message}
                                        </p>
                                    )}

                                    {job.updated_at && (
                                        <p className="text-xs text-gray-500">
                                            Updated: {new Date(job.updated_at).toLocaleString(undefined, {
                                                year: 'numeric',
                                                month: '2-digit',
                                                day: '2-digit',
                                                hour: '2-digit',
                                                minute: '2-digit',
                                                hour12: false
                                            })}
                                        </p>
                                    )}
                                </div>

                                <button
                                    onClick={(e) => {
                                        e.stopPropagation()
                                        setSelectedJob(job)
                                    }}
                                    className="mt-4 w-full flex items-center justify-center space-x-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
                                >
                                    <Eye className="h-4 w-4" />
                                    <span className="text-sm font-medium">View Details</span>
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Detail Modal */}
            {selectedJob && (
                <JobDetailModal
                    job={selectedJob}
                    onClose={() => setSelectedJob(null)}
                />
            )}
        </>
    )
}
