'use client'

import { useState, useCallback, useEffect } from 'react'
import { Upload, FileText, AlertCircle, Loader2, Download } from 'lucide-react'
import { useVideoGeneration } from '@/hooks/useVideoGeneration'
import { VideoPlayer } from './VideoPlayer'
import { JobStatusResponse } from '@/types/api'

export const FileUpload = () => {
    const [dragActive, setDragActive] = useState(false)
    const [selectedFile, setSelectedFile] = useState<File | null>(null)
    const [currentJobId, setCurrentJobId] = useState<string | null>(null)
    const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null)
    const [isPolling, setIsPolling] = useState(false)
    
    const { generateVideo, getJobStatus, isLoading, error } = useVideoGeneration()

    // Poll for job status when a job is running
    useEffect(() => {
        if (!isPolling || !currentJobId) return

        const pollStatus = async () => {
            try {
                const status = await getJobStatus(currentJobId)
                setJobStatus(status)

                // Stop polling if job is completed or failed
                if (['completed', 'completed_with_errors', 'failed', 'cancelled'].includes(status.status)) {
                    setIsPolling(false)
                }
            } catch (error) {
                console.error('Failed to get job status:', error)
                setIsPolling(false)
            }
        }

        pollStatus()
        const interval = setInterval(pollStatus, 2000)

        return () => clearInterval(interval)
    }, [currentJobId, isPolling, getJobStatus])

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true)
        } else if (e.type === 'dragleave') {
            setDragActive(false)
        }
    }, [])

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setDragActive(false)

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            const file = e.dataTransfer.files[0]
            if (validateFile(file)) {
                setSelectedFile(file)
            }
        }
    }, [])

    const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0]
            if (validateFile(file)) {
                setSelectedFile(file)
            }
        }
    }, [])

    const validateFile = (file: File): boolean => {
        const allowedTypes = ['text/plain', 'application/pdf', 'text/markdown']
        const maxSize = 50 * 1024 * 1024 // 50MB

        if (!allowedTypes.includes(file.type) && !file.name.endsWith('.md')) {
            alert('Please upload a .txt, .pdf, or .md file')
            return false
        }

        if (file.size > maxSize) {
            alert('File size must be less than 50MB')
            return false
        }

        return true
    }

    const handleSubmit = async () => {
        if (!selectedFile) return

        try {
            // Hide video player when starting new upload
            setJobStatus(null)
            
            const response = await generateVideo(selectedFile)
            setCurrentJobId(response.job_id)
            setIsPolling(true)
            setSelectedFile(null)
        } catch (err) {
            console.error('Failed to generate video:', err)
        }
    }

    const handleNewUpload = () => {
        setSelectedFile(null)
        setCurrentJobId(null)
        setJobStatus(null)
        setIsPolling(false)
    }

    const formatFileSize = (bytes: number): string => {
        if (bytes === 0) return '0 Bytes'
        const k = 1024
        const sizes = ['Bytes', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    const getProgressColor = (progress?: number) => {
        if (!progress) return 'bg-gray-400'
        if (progress < 30) return 'bg-blue-500'
        if (progress < 70) return 'bg-indigo-500'
        return 'bg-green-500'
    }

    const isJobComplete = jobStatus?.status === 'completed' || jobStatus?.status === 'completed_with_errors'
    const hasVideo = isJobComplete && jobStatus?.result?.video?.video_url

    return (
        <div className="w-full max-w-4xl mx-auto space-y-8">
            {/* Video Player Section - Shows when job is completed */}
            {hasVideo && (
                <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-200">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-xl font-bold text-gray-900">Your Generated Video</h3>
                        <a
                            href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${jobStatus.result.video.video_url}?download=true`}
                            download
                            className="inline-flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                        >
                            <Download className="h-4 w-4" />
                            <span>Download</span>
                        </a>
                    </div>
                    
                    <VideoPlayer video={jobStatus.result.video} jobId={currentJobId!} />
                    
                    <div className="mt-4 pt-4 border-t border-gray-200">
                        <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                                <span className="text-gray-600">Duration:</span>
                                <span className="ml-2 font-medium text-gray-900">
                                    {jobStatus.result.video?.duration_seconds 
                                        ? `${jobStatus.result.video.duration_seconds.toFixed(1)}s`
                                        : 'N/A'}
                                </span>
                            </div>
                            <div>
                                <span className="text-gray-600">Resolution:</span>
                                <span className="ml-2 font-medium text-gray-900">
                                    {jobStatus.result.video?.resolution || 'N/A'}
                                </span>
                            </div>
                        </div>
                    </div>

                    <button
                        onClick={handleNewUpload}
                        className="mt-6 w-full px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all font-medium"
                    >
                        Create Another Video
                    </button>
                </div>
            )}

            {/* Loading/Progress Section - Shows when job is processing */}
            {isPolling && jobStatus && !isJobComplete && (
                <div className="bg-white rounded-xl shadow-lg p-8 border border-gray-200">
                    <div className="text-center space-y-6">
                        <div className="flex justify-center">
                            <div className="relative">
                                <Loader2 className="h-16 w-16 text-blue-600 animate-spin" />
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <span className="text-xs font-bold text-blue-600">
                                        {jobStatus.progress || 0}%
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div>
                            <h3 className="text-2xl font-bold text-gray-900 mb-2">
                                Creating Your Video...
                            </h3>
                            <p className="text-gray-600">
                                {jobStatus.message || 'Processing your document'}
                            </p>
                        </div>

                        <div className="w-full bg-gray-200 rounded-full h-3">
                            <div
                                className={`h-3 rounded-full transition-all duration-500 ${getProgressColor(jobStatus.progress)}`}
                                style={{ width: `${jobStatus.progress || 0}%` }}
                            />
                        </div>

                        <div className="text-sm text-gray-500">
                            Job ID: {currentJobId?.slice(0, 8)}...
                        </div>
                    </div>
                </div>
            )}

            {/* Upload Section - Always visible at bottom, or centered when no video */}
            {!hasVideo && (
                <div
                    className={`
                        relative border-2 border-dashed rounded-xl p-12 text-center transition-all
                        ${dragActive
                            ? 'border-blue-500 bg-blue-50 scale-105'
                            : selectedFile
                            ? 'border-green-500 bg-green-50'
                            : 'border-gray-300 hover:border-gray-400 bg-white'
                        }
                        ${isPolling ? 'opacity-50 pointer-events-none' : ''}
                    `}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                >
                    <input
                        type="file"
                        id="file-upload"
                        className="hidden"
                        accept=".txt,.pdf,.md"
                        onChange={handleFileInput}
                        disabled={isLoading || isPolling}
                    />

                    <div className="space-y-6">
                        {selectedFile ? (
                            <>
                                <div className="flex items-center justify-center space-x-4">
                                    <div className="p-3 bg-green-100 rounded-full">
                                        <FileText className="h-8 w-8 text-green-600" />
                                    </div>
                                    <div className="text-left">
                                        <p className="font-semibold text-gray-900 text-lg">{selectedFile.name}</p>
                                        <p className="text-sm text-gray-500">{formatFileSize(selectedFile.size)}</p>
                                    </div>
                                </div>

                                <div className="flex items-center justify-center space-x-4">
                                    <button
                                        onClick={handleSubmit}
                                        disabled={isLoading}
                                        className="px-8 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium shadow-lg"
                                    >
                                        {isLoading ? (
                                            <span className="flex items-center space-x-2">
                                                <Loader2 className="h-5 w-5 animate-spin" />
                                                <span>Starting...</span>
                                            </span>
                                        ) : (
                                            'Generate Video'
                                        )}
                                    </button>

                                    <button
                                        onClick={() => setSelectedFile(null)}
                                        className="px-6 py-3 text-gray-700 hover:text-gray-900 transition-colors font-medium"
                                    >
                                        Cancel
                                    </button>
                                </div>
                            </>
                        ) : (
                            <>
                                <div className="flex justify-center">
                                    <div className="p-6 bg-blue-50 rounded-full">
                                        <Upload className="h-12 w-12 text-blue-600" />
                                    </div>
                                </div>

                                <div>
                                    <p className="text-xl font-semibold text-gray-900 mb-2">
                                        Drop your document here
                                    </p>
                                    <p className="text-gray-600 mb-4">
                                        or{' '}
                                        <label
                                            htmlFor="file-upload"
                                            className="text-blue-600 hover:text-blue-700 cursor-pointer font-medium"
                                        >
                                            browse files
                                        </label>
                                    </p>
                                    <p className="text-sm text-gray-500">
                                        Supports .txt, .pdf, .md files up to 50MB
                                    </p>
                                </div>
                            </>
                        )}

                        {error && (
                            <div className="flex items-center justify-center space-x-2 text-red-600 bg-red-50 py-3 px-4 rounded-lg">
                                <AlertCircle className="h-5 w-5" />
                                <span className="text-sm font-medium">{error}</span>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Upload Section Below Video */}
            {hasVideo && (
                <div className="bg-gray-50 rounded-xl p-8 border-2 border-dashed border-gray-300">
                    <div className="text-center space-y-4">
                        <Upload className="mx-auto h-10 w-10 text-gray-400" />
                        <div>
                            <h4 className="text-lg font-semibold text-gray-900 mb-2">
                                Create Another Video
                            </h4>
                            <p className="text-sm text-gray-600 mb-4">
                                Upload a new document to generate another video
                            </p>
                            <label
                                htmlFor="file-upload-bottom"
                                className="inline-block px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 cursor-pointer transition-colors"
                            >
                                Choose File
                            </label>
                            <input
                                type="file"
                                id="file-upload-bottom"
                                className="hidden"
                                accept=".txt,.pdf,.md"
                                onChange={(e) => {
                                    handleFileInput(e)
                                    if (e.target.files?.[0]) {
                                        handleNewUpload()
                                    }
                                }}
                            />
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
