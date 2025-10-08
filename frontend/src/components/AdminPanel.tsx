'use client'

import { useState, useEffect } from 'react'
import { Settings, Trash2, AlertTriangle, CheckCircle, Loader2, Brain, TestTube, Activity } from 'lucide-react'
import {
    LLMProvidersResponse,
    LLMHealthResponse,
    LLMTestResponse,
    SetProviderResponse,
    CacheClearResponse,
    CacheInfoResponse,
    RefreshModelsResponse
} from '../types/api'

export const AdminPanel = () => {
    const [isCleaning, setIsCleaning] = useState(false)
    const [cleanupResult, setCleanupResult] = useState<any>(null)

    // LLM Configuration state
    const [llmProviders, setLlmProviders] = useState<LLMProvidersResponse | null>(null)
    const [llmHealth, setLlmHealth] = useState<LLMHealthResponse | null>(null)
    const [isLoadingProviders, setIsLoadingProviders] = useState(false)
    const [isLoadingHealth, setIsLoadingHealth] = useState(false)
    const [isTestingLLM, setIsTestingLLM] = useState(false)
    const [testResult, setTestResult] = useState<LLMTestResponse | null>(null)
    const [selectedProvider, setSelectedProvider] = useState('')
    const [selectedModel, setSelectedModel] = useState('')
    const [isSettingProvider, setIsSettingProvider] = useState(false)

    // Cache Management state
    const [cacheInfo, setCacheInfo] = useState<CacheInfoResponse | null>(null)
    const [isLoadingCacheInfo, setIsLoadingCacheInfo] = useState(false)
    const [isClearingCache, setIsClearingCache] = useState(false)
    const [isRefreshingModels, setIsRefreshingModels] = useState(false)
    const [refreshResult, setRefreshResult] = useState<RefreshModelsResponse | null>(null)

    // Load LLM providers on component mount
    useEffect(() => {
        loadLLMProviders()
        loadLLMHealth()
        loadCacheInfo()
    }, [])

    const loadLLMProviders = async () => {
        setIsLoadingProviders(true)
        try {
            const response = await fetch('/api/v1/admin/llm/providers')
            if (response.ok) {
                const data: LLMProvidersResponse = await response.json()
                setLlmProviders(data)
                setSelectedProvider(data.current_provider)
            }
        } catch (error) {
            console.error('Failed to load LLM providers:', error)
        } finally {
            setIsLoadingProviders(false)
        }
    }

    const loadLLMHealth = async () => {
        setIsLoadingHealth(true)
        try {
            const response = await fetch('/api/v1/admin/llm/health')
            if (response.ok) {
                const data: LLMHealthResponse = await response.json()
                setLlmHealth(data)
            }
        } catch (error) {
            console.error('Failed to load LLM health:', error)
        } finally {
            setIsLoadingHealth(false)
        }
    }

    const testLLM = async () => {
        setIsTestingLLM(true)
        setTestResult(null)

        try {
            const response = await fetch('/api/v1/admin/llm/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            })

            const data: LLMTestResponse = await response.json()
            setTestResult(data)
        } catch (error) {
            console.error('LLM test failed:', error)
            setTestResult({
                success: false,
                provider: selectedProvider,
                model: selectedModel,
                error: error instanceof Error ? error.message : 'Unknown error',
                timestamp: Date.now() / 1000
            })
        } finally {
            setIsTestingLLM(false)
        }
    }

    const setProvider = async () => {
        if (!selectedProvider) return

        setIsSettingProvider(true)
        try {
            const response = await fetch(`/api/v1/admin/llm/provider/${selectedProvider}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            })

            if (response.ok) {
                const data: SetProviderResponse = await response.json()
                alert(data.message)
                // Reload providers to get updated info
                await loadLLMProviders()
                await loadLLMHealth()
            } else {
                const error = await response.json()
                alert(`Failed to set provider: ${error.detail}`)
            }
        } catch (error) {
            console.error('Failed to set provider:', error)
            alert('Failed to set provider')
        } finally {
            setIsSettingProvider(false)
        }
    }

    const loadCacheInfo = async () => {
        setIsLoadingCacheInfo(true)
        try {
            const response = await fetch('/api/v1/admin/llm/cache/info')
            if (response.ok) {
                const data: CacheInfoResponse = await response.json()
                setCacheInfo(data)
            }
        } catch (error) {
            console.error('Failed to load cache info:', error)
        } finally {
            setIsLoadingCacheInfo(false)
        }
    }

    const clearCache = async (provider?: string) => {
        setIsClearingCache(true)
        try {
            const url = provider
                ? `/api/v1/admin/llm/cache/clear?provider=${provider}`
                : '/api/v1/admin/llm/cache/clear'

            const response = await fetch(url, { method: 'POST' })
            if (response.ok) {
                const data: CacheClearResponse = await response.json()
                alert(data.message)
                await loadCacheInfo()
            } else {
                const error = await response.json()
                alert(`Failed to clear cache: ${error.detail}`)
            }
        } catch (error) {
            console.error('Failed to clear cache:', error)
            alert('Failed to clear cache')
        } finally {
            setIsClearingCache(false)
        }
    }

    const refreshProviderModels = async (provider: string) => {
        setIsRefreshingModels(true)
        setRefreshResult(null)

        try {
            const response = await fetch(`/api/v1/admin/llm/cache/refresh/${provider}`, {
                method: 'POST'
            })

            if (response.ok) {
                const data: RefreshModelsResponse = await response.json()
                setRefreshResult(data)
                await loadCacheInfo()
                await loadLLMProviders() // Refresh providers to get updated models
            } else {
                const error = await response.json()
                alert(`Failed to refresh models: ${error.detail}`)
            }
        } catch (error) {
            console.error('Failed to refresh models:', error)
            alert('Failed to refresh models')
        } finally {
            setIsRefreshingModels(false)
        }
    }

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

                {/* LLM Configuration Section */}
                <div className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center space-x-3 mb-4">
                        <Brain className="h-5 w-5 text-blue-500" />
                        <h3 className="text-lg font-medium text-gray-900">LLM Configuration</h3>
                    </div>

                    {/* Current Status */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 text-sm">
                        <div>
                            <span className="font-medium text-gray-700">Current Provider:</span>
                            <p className="text-gray-600 mt-1">
                                {isLoadingProviders ? (
                                    <Loader2 className="h-4 w-4 animate-spin inline" />
                                ) : (
                                    llmProviders?.current_provider || 'Loading...'
                                )}
                            </p>
                        </div>

                        <div>
                            <span className="font-medium text-gray-700">Health Status:</span>
                            <div className="flex items-center mt-1">
                                {isLoadingHealth ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : llmHealth?.healthy ? (
                                    <CheckCircle className="h-4 w-4 text-green-500 mr-1" />
                                ) : (
                                    <AlertTriangle className="h-4 w-4 text-red-500 mr-1" />
                                )}
                                <span className={llmHealth?.healthy ? 'text-green-600' : 'text-red-600'}>
                                    {llmHealth?.healthy ? 'Healthy' : 'Unhealthy'}
                                </span>
                            </div>
                        </div>

                        <div>
                            <span className="font-medium text-gray-700">Current Model:</span>
                            <p className="text-gray-600 mt-1">
                                {llmHealth?.current_model || 'Loading...'}
                            </p>
                        </div>
                    </div>

                    {/* Provider Selection */}
                    {llmProviders && (
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Select LLM Provider
                                </label>
                                <select
                                    value={selectedProvider}
                                    onChange={(e) => setSelectedProvider(e.target.value)}
                                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                >
                                    {llmProviders.available_providers.map((provider) => (
                                        <option key={provider} value={provider}>
                                            {provider.charAt(0).toUpperCase() + provider.slice(1)}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Model Selection */}
                            {selectedProvider && llmProviders.supported_models[selectedProvider] && llmProviders.supported_models[selectedProvider].length > 0 && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Select Model
                                    </label>
                                    <select
                                        value={selectedModel}
                                        onChange={(e) => setSelectedModel(e.target.value)}
                                        className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    >
                                        <option value="">Select a model...</option>
                                        {llmProviders.supported_models[selectedProvider].map((model) => (
                                            <option key={model} value={model}>
                                                {model}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            )}

                            {/* Action Buttons */}
                            <div className="flex space-x-3">
                                <button
                                    onClick={setProvider}
                                    disabled={!selectedProvider || isSettingProvider}
                                    className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {isSettingProvider ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                        <Settings className="h-4 w-4" />
                                    )}
                                    <span>{isSettingProvider ? 'Setting...' : 'Set Provider'}</span>
                                </button>

                                <button
                                    onClick={testLLM}
                                    disabled={isTestingLLM}
                                    className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {isTestingLLM ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                        <TestTube className="h-4 w-4" />
                                    )}
                                    <span>{isTestingLLM ? 'Testing...' : 'Test LLM'}</span>
                                </button>

                                <button
                                    onClick={() => {
                                        loadLLMProviders()
                                        loadLLMHealth()
                                        loadCacheInfo()
                                    }}
                                    className="flex items-center space-x-2 px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
                                >
                                    <Activity className="h-4 w-4" />
                                    <span>Refresh All</span>
                                </button>
                            </div>

                            {/* Test Results */}
                            {testResult && (
                                <div className="mt-4 p-4 rounded-md border">
                                    <div className="flex items-center space-x-2 mb-2">
                                        {testResult.success ? (
                                            <CheckCircle className="h-4 w-4 text-green-500" />
                                        ) : (
                                            <AlertTriangle className="h-4 w-4 text-red-500" />
                                        )}
                                        <span className={`text-sm font-medium ${testResult.success ? 'text-green-600' : 'text-red-600'}`}>
                                            {testResult.success ? 'Test Successful' : 'Test Failed'}
                                        </span>
                                    </div>

                                    <div className="text-sm text-gray-600 space-y-1">
                                        <div>Provider: {testResult.provider}</div>
                                        <div>Model: {testResult.model}</div>
                                        {testResult.test_response && (
                                            <div>Response: {testResult.test_response}</div>
                                        )}
                                        {testResult.error && (
                                            <div className="text-red-600">Error: {testResult.error}</div>
                                        )}
                                        <div>Timestamp: {new Date(testResult.timestamp * 1000).toLocaleString()}</div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Cache Management Section */}
                <div className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center space-x-3 mb-4">
                        <Activity className="h-5 w-5 text-purple-500" />
                        <h3 className="text-lg font-medium text-gray-900">Cache Management</h3>
                    </div>

                    {/* Cache Info */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4 text-sm">
                        <div>
                            <span className="font-medium text-gray-700">Cached Providers:</span>
                            <p className="text-gray-600 mt-1">
                                {isLoadingCacheInfo ? (
                                    <Loader2 className="h-4 w-4 animate-spin inline" />
                                ) : (
                                    cacheInfo?.cache_info.cached_providers.length || 0
                                )}
                            </p>
                        </div>

                        <div>
                            <span className="font-medium text-gray-700">Cache Duration:</span>
                            <p className="text-gray-600 mt-1">
                                {cacheInfo?.cache_info.cache_duration_hours.toFixed(1) || 'N/A'} hours
                            </p>
                        </div>
                    </div>

                    {/* Cache Actions */}
                    <div className="space-y-3">
                        <div className="flex flex-wrap gap-3">
                            <button
                                onClick={() => clearCache()}
                                disabled={isClearingCache}
                                className="flex items-center space-x-2 px-3 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                            >
                                {isClearingCache ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    <Trash2 className="h-4 w-4" />
                                )}
                                <span>Clear All Cache</span>
                            </button>

                            <button
                                onClick={loadCacheInfo}
                                className="flex items-center space-x-2 px-3 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 text-sm"
                            >
                                <Activity className="h-4 w-4" />
                                <span>Refresh Cache Info</span>
                            </button>
                        </div>

                        {/* Provider-specific cache management */}
                        {llmProviders && (
                            <div>
                                <h4 className="text-sm font-medium text-gray-700 mb-2">Refresh Models by Provider:</h4>
                                <div className="flex flex-wrap gap-2">
                                    {llmProviders.available_providers.map((provider) => (
                                        <button
                                            key={provider}
                                            onClick={() => refreshProviderModels(provider)}
                                            disabled={isRefreshingModels}
                                            className="flex items-center space-x-1 px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs hover:bg-blue-200 disabled:opacity-50"
                                        >
                                            {isRefreshingModels ? (
                                                <Loader2 className="h-3 w-3 animate-spin" />
                                            ) : (
                                                <Brain className="h-3 w-3" />
                                            )}
                                            <span>{provider}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Refresh Results */}
                        {refreshResult && (
                            <div className="mt-4 p-3 rounded-md border">
                                <div className="flex items-center space-x-2 mb-2">
                                    <CheckCircle className="h-4 w-4 text-green-500" />
                                    <span className="text-sm font-medium text-green-600">
                                        Models Refreshed Successfully
                                    </span>
                                </div>

                                <div className="text-sm text-gray-600 space-y-1">
                                    <div>Provider: {refreshResult.provider}</div>
                                    <div>Models: {refreshResult.models_count}</div>
                                    <div>Sample: {refreshResult.models.slice(0, 3).join(', ')}{refreshResult.models.length > 3 ? '...' : ''}</div>
                                </div>
                            </div>
                        )}
                    </div>
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
