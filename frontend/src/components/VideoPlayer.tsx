'use client'

import { useState } from 'react'
import { Download, Eye, Play, Pause, Volume2, VolumeX } from 'lucide-react'
import { VideoResult } from '@/types/api'

interface VideoPlayerProps {
    video: VideoResult
    jobId: string
    className?: string
}

export const VideoPlayer = ({ video, jobId, className = '' }: VideoPlayerProps) => {
    const [isPlaying, setIsPlaying] = useState(false)
    const [isMuted, setIsMuted] = useState(false)
    const [showControls, setShowControls] = useState(true)

    const handlePlayPause = () => {
        setIsPlaying(!isPlaying)
    }

    const handleMuteToggle = () => {
        setIsMuted(!isMuted)
    }

    const formatFileSize = (sizeInMB?: number) => {
        if (!sizeInMB) return ''
        if (sizeInMB < 1) {
            return `${(sizeInMB * 1024).toFixed(0)} KB`
        }
        return `${sizeInMB.toFixed(2)} MB`
    }

    const formatDuration = (duration?: number) => {
        if (!duration) return ''
        const minutes = Math.floor(duration / 60)
        const seconds = Math.floor(duration % 60)
        return `${minutes}:${seconds.toString().padStart(2, '0')}`
    }

    return (
        <div className={`bg-gray-50 rounded-lg p-4 ${className}`}>
            {/* <div className="flex items-center justify-between mb-3">
                <h5 className="text-sm font-medium text-gray-700">Generated Video</h5>
                <div className="flex space-x-2">
                    <a
                        href={video.video_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                    >
                        <Eye className="h-4 w-4 mr-1" />
                        View
                    </a>
                    <a
                        href={video.download_url}
                        download={`video_${jobId}.mp4`}
                        className="inline-flex items-center px-3 py-1 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                    >
                        <Download className="h-4 w-4 mr-1" />
                        Download
                    </a>
                </div>
            </div> */}

            <div className="relative group">
                <video
                    controls
                    className="w-full max-w-2xl mx-auto rounded-lg shadow-sm"
                    poster=""
                    onPlay={() => setIsPlaying(true)}
                    onPause={() => setIsPlaying(false)}
                    onVolumeChange={(e) => setIsMuted((e.target as HTMLVideoElement).muted)}
                >
                    <source src={video.video_url} type="video/mp4" />
                    Your browser does not support the video tag.
                </video>

                {/* Custom overlay controls (optional) */}
                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <div className="bg-black bg-opacity-50 rounded-full p-3">
                        {isPlaying ? (
                            <Pause className="h-6 w-6 text-white" />
                        ) : (
                            <Play className="h-6 w-6 text-white" />
                        )}
                    </div>
                </div>
            </div>

            {/* Video metadata */}
            <div className="mt-3 flex items-center justify-center space-x-4 text-xs text-gray-500">
                {video.duration && (
                    <span className="flex items-center">
                        <Play className="h-3 w-3 mr-1" />
                        {formatDuration(video.duration)}
                    </span>
                )}

                {video.file_size_mb && (
                    <span className="flex items-center">
                        <Download className="h-3 w-3 mr-1" />
                        {formatFileSize(video.file_size_mb)}
                    </span>
                )}

                <span className="text-gray-400">•</span>
                <span className="capitalize">{video.status}</span>
            </div>
        </div>
    )
}
