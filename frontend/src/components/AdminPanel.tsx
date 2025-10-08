'use client'

import { useState } from 'react'
import { Settings, Trash2, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react'

export const AdminPanel = () => {
    const [isCleaning, setIsCleaning] = useState(false)
    const [cleanupResult, setCleanupResult] = useState<any>(null)

    const handleCleanup = async () => {
        setIsCleaning(true)
        setCleanupResult(null)

        try {
            const response = await fetch('/api/v1/admin/cleanup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            })

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`)
            }

            const result = await response.json()
            setCleanupResult(result)
        } catch (error) {
            console.error('Cleanup failed:', error)
            setCleanupResult({
                error: error instanceof Error ? error.message : 'Unknown error occurred'
            })
        } finally {
            setIsCleaning(false)
        }
    }

    return (
        <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex items-center space-x-3 mb-6">
                <Settings className="h-6 w-6 text-gray-600" />
                <h2 className="text-xl font-semibold text-gray-900">Admin Panel</h2>
            </div>

            <div className="space-y-6">
                {/* Cleanup Section */}
                <div className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center space-x-3 mb-4">
                        <Trash2 className="h-5 w-5 text-red-500" />
                        <h3 className="text-lg font-medium text-gray-900">System Cleanup</h3>
                    </div>

                    <p className="text-sm text-gray-600 mb-4">
                        Clean up expired jobs and temporary files. This will remove jobs older than 24 hours.
                    </p>

                    <button
                        onClick={handleCleanup}
                        disabled={isCleaning}
                        className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isCleaning ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <Trash2 className="h-4 w-4" />
                        )}
                        <span>{isCleaning ? 'Cleaning...' : 'Run Cleanup'}</span>
                    </button>

                    {cleanupResult && (
                        <div className="mt-4 p-4 rounded-md border">
                            {cleanupResult.error ? (
                                <div className="flex items-center space-x-2 text-red-600">
                                    <AlertTriangle className="h-4 w-4" />
                                    <span className="text-sm">Cleanup failed: {cleanupResult.error}</span>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    <div className="flex items-center space-x-2 text-green-600">
                                        <CheckCircle className="h-4 w-4" />
                                        <span className="text-sm font-medium">Cleanup completed successfully</span>
                                    </div>

                                    <div className="text-sm text-gray-600 space-y-1">
                                        <div>Jobs cleaned: {cleanupResult.job_cleanup?.expired_jobs_cleaned || 0}</div>
                                        <div>Jobs remaining: {cleanupResult.job_cleanup?.jobs_remaining || 0}</div>
                                        <div>Queue length: {cleanupResult.job_cleanup?.queue_length || 0}</div>
                                        {cleanupResult.timestamp && (
                                            <div>Completed at: {new Date(cleanupResult.timestamp * 1000).toLocaleString()}</div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* System Info Section */}
                <div className="border border-gray-200 rounded-lg p-4">
                    <h3 className="text-lg font-medium text-gray-900 mb-4">System Information</h3>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                        <div>
                            <span className="font-medium text-gray-700">API Base URL:</span>
                            <p className="text-gray-600 mt-1 font-mono">
                                {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
                            </p>
                        </div>

                        <div>
                            <span className="font-medium text-gray-700">Frontend Version:</span>
                            <p className="text-gray-600 mt-1">v1.0.0</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
