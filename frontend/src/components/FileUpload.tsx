'use client'

import { useState, useCallback } from 'react'
import { Upload, FileText, AlertCircle } from 'lucide-react'
import { useVideoGeneration } from '@/hooks/useVideoGeneration'

interface FileUploadProps {
    onJobCreated?: (jobId: string) => void
}

export const FileUpload = ({ onJobCreated }: FileUploadProps) => {
    const [dragActive, setDragActive] = useState(false)
    const [selectedFile, setSelectedFile] = useState<File | null>(null)
    const { generateVideo, isLoading, error } = useVideoGeneration()

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

        if (!allowedTypes.includes(file.type)) {
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
            const response = await generateVideo(selectedFile)
            onJobCreated?.(response.job_id)
            setSelectedFile(null)
        } catch (err) {
            console.error('Failed to generate video:', err)
        }
    }

    const formatFileSize = (bytes: number): string => {
        if (bytes === 0) return '0 Bytes'
        const k = 1024
        const sizes = ['Bytes', 'KB', 'MB', 'GB']
        const i = Math.floor(Math.log(bytes) / Math.log(k))
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    return (
        <div className="w-full max-w-2xl mx-auto">
            <div
                className={`
          relative border-2 border-dashed rounded-lg p-8 text-center transition-colors
          ${dragActive
                        ? 'border-blue-500 bg-blue-50'
                        : selectedFile
                            ? 'border-green-500 bg-green-50'
                            : 'border-gray-300 hover:border-gray-400'
                    }
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
                    disabled={isLoading}
                />

                <div className="space-y-4">
                    {selectedFile ? (
                        <div className="flex items-center justify-center space-x-3">
                            <FileText className="h-8 w-8 text-green-600" />
                            <div className="text-left">
                                <p className="font-medium text-gray-900">{selectedFile.name}</p>
                                <p className="text-sm text-gray-500">{formatFileSize(selectedFile.size)}</p>
                            </div>
                        </div>
                    ) : (
                        <>
                            <Upload className="mx-auto h-12 w-12 text-gray-400" />
                            <div>
                                <p className="text-lg font-medium text-gray-900">
                                    Drop your file here, or{' '}
                                    <label
                                        htmlFor="file-upload"
                                        className="text-blue-600 hover:text-blue-500 cursor-pointer"
                                    >
                                        browse
                                    </label>
                                </p>
                                <p className="text-sm text-gray-500">
                                    Supports .txt, .pdf, .md files up to 50MB
                                </p>
                            </div>
                        </>
                    )}

                    {error && (
                        <div className="flex items-center justify-center space-x-2 text-red-600">
                            <AlertCircle className="h-4 w-4" />
                            <span className="text-sm">{error}</span>
                        </div>
                    )}

                    {selectedFile && (
                        <button
                            onClick={handleSubmit}
                            disabled={isLoading}
                            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isLoading ? 'Generating...' : 'Generate Video'}
                        </button>
                    )}
                </div>
            </div>
        </div>
    )
}

