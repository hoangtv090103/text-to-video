'use client'

import { useState } from 'react'
import { Trash2, AlertTriangle, CheckCircle, Loader2, Info } from 'lucide-react'
import { LLMSettings } from './LLMSettings'
import { ConnectionTest } from './ConnectionTest'

export const AdminPanel = () => {
    const [isCleaning, setIsCleaning] = useState(false)
    const [cleanupResult, setCleanupResult] = useState<any>(null)
    const [error, setError] = useState<string | null>(null)

    const handleCleanup = async () => {
        setIsCleaning(true)
        setError(null)
        setCleanupResult(null)

        try {
            const response = await fetch('/api/v1/admin/cleanup', {
                method: 'POST',
            })

            if (!response.ok) {
                throw new Error(`Cleanup failed: ${response.status}`)
            }

            const data = await response.json()
            setCleanupResult(data)
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Cleanup failed'
            setError(errorMessage)
            console.error('Cleanup error:', err)
        } finally {
            setIsCleaning(false)
        }
    }

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            {/* Connection Test Section */}
            <ConnectionTest />

            {/* LLM Settings Section */}
            <LLMSettings />

            {/* System Cleanup Section */}
            <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
                <div className="flex items-center space-x-3 mb-6">
                    <div className="p-2 bg-orange-100 rounded-lg">
                        <Trash2 className="h-6 w-6 text-orange-600" />
                    </div>
                    <div className="flex-1">
                        <div className="flex items-center space-x-2">
                            <h3 className="text-lg font-semibold text-gray-900">System Cleanup</h3>
                            <div className="group relative">
                                <Info className="h-4 w-4 text-blue-500 cursor-help" />
                                <div className="invisible group-hover:visible absolute left-0 top-6 z-10 w-64 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-lg">
                                    <p className="font-medium mb-2">About System Cleanup:</p>
                                    <ul className="space-y-1 list-disc list-inside">
                                        <li>Removes jobs older than 24 hours</li>
                                        <li>Cleans up temporary files and assets</li>
                                        <li>Frees up disk space</li>
                                        <li>Safe to run anytime - won't affect active jobs</li>
                                    </ul>
                                    <div className="absolute -top-1 left-2 w-2 h-2 bg-gray-900 transform rotate-45"></div>
                                </div>
                            </div>
                        </div>
                        <p className="text-sm text-gray-600">
                            Remove expired jobs and clean up temporary files
                        </p>
                    </div>
                </div>

                <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                        <div className="flex items-center space-x-3">
                            <AlertTriangle className="h-5 w-5 text-yellow-600" />
                            <div>
                                <p className="text-sm font-medium text-gray-900">
                                    Clean Expired Jobs
                                </p>
                                <p className="text-xs text-gray-600">
                                    Remove jobs older than 24 hours and their associated files
                                </p>
                            </div>
                        </div>
                        <button
                            onClick={handleCleanup}
                            disabled={isCleaning}
                            className={`
                                px-4 py-2 rounded-lg font-medium transition-colors
                                ${isCleaning
                                    ? 'bg-gray-400 cursor-not-allowed'
                                    : 'bg-orange-600 hover:bg-orange-700 text-white'
                                }
                            `}
                        >
                            {isCleaning ? (
                                <span className="flex items-center space-x-2">
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    <span>Cleaning...</span>
                                </span>
                            ) : (
                                'Run Cleanup'
                            )}
                        </button>
                    </div>

                    {/* Error Message */}
                    {error && (
                        <div className="flex items-center space-x-2 p-4 bg-red-50 border border-red-200 rounded-lg">
                            <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0" />
                            <div>
                                <p className="text-sm font-medium text-red-900">Cleanup Failed</p>
                                <p className="text-xs text-red-700 mt-1">{error}</p>
                            </div>
                        </div>
                    )}

                    {/* Success Result */}
                    {cleanupResult && (
                        <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                            <div className="flex items-center space-x-2 mb-3">
                                <CheckCircle className="h-5 w-5 text-green-600" />
                                <h4 className="text-sm font-semibold text-green-900">
                                    Cleanup Completed Successfully
                                </h4>
                            </div>

                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <p className="text-gray-600">Jobs Cleaned</p>
                                    <p className="text-lg font-bold text-green-700">
                                        {cleanupResult.job_cleanup?.expired_jobs_cleaned || 0}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-gray-600">Jobs Remaining</p>
                                    <p className="text-lg font-bold text-blue-700">
                                        {cleanupResult.job_cleanup?.jobs_remaining || 0}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-gray-600">Queue Length</p>
                                    <p className="text-lg font-bold text-purple-700">
                                        {cleanupResult.job_cleanup?.queue_length || 0}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-gray-600">Timestamp</p>
                                    <p className="text-xs text-gray-700">
                                        {cleanupResult.job_cleanup?.timestamp
                                            ? new Date(cleanupResult.job_cleanup.timestamp).toLocaleString()
                                            : 'N/A'}
                                    </p>
                                </div>
                            </div>

                            {cleanupResult.message && (
                                <p className="mt-3 text-xs text-gray-600">
                                    {cleanupResult.message}
                                </p>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* System Status */}
            <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">System Status</h3>
                <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <span className="text-sm text-gray-700">Backend API</span>
                        <span className="px-3 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full">
                            Online
                        </span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <span className="text-sm text-gray-700">TTS Service</span>
                        <span className="px-3 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full">
                            Available
                        </span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <span className="text-sm text-gray-700">LLM Service</span>
                        <span className="px-3 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full">
                            Available
                        </span>
                    </div>
                </div>
            </div>
        </div>
    )
}
