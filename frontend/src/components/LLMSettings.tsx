'use client'

import { useState } from 'react'
import { Settings, Loader2, CheckCircle, XCircle, AlertTriangle, Zap } from 'lucide-react'
import { LLMConfig, ModelInfo, FetchModelsResponse, TestModelResponse } from '@/types/api'

export const LLMSettings = () => {
    const [provider, setProvider] = useState('openai')
    const [baseUrl, setBaseUrl] = useState('')
    const [apiKey, setApiKey] = useState('')
    const [models, setModels] = useState<ModelInfo[]>([])
    const [selectedModel, setSelectedModel] = useState('')
    const [isFetchingModels, setIsFetchingModels] = useState(false)
    const [isTesting, setIsTesting] = useState(false)
    const [isSaving, setIsSaving] = useState(false)
    const [testResult, setTestResult] = useState<TestModelResponse | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [success, setSuccess] = useState<string | null>(null)

    const providers = [
        { id: 'openai', name: 'OpenAI', requiresUrl: false },
        { id: 'google', name: 'Google Gemini', requiresUrl: false },
        { id: 'anthropic', name: 'Anthropic Claude', requiresUrl: false },
        { id: 'local', name: 'Local Model', requiresUrl: true },
    ]

    const handleFetchModels = async () => {
        setError(null)
        setIsFetchingModels(true)
        setModels([])
        setSelectedModel('')
        setTestResult(null)

        try {
            const requestBody = {
                provider,
                base_url: baseUrl || null,
                api_key: apiKey || null,
            }
            console.log('Fetching models with:', requestBody)

            const response = await fetch('/api/v1/admin/llm/fetch-models', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody),
            })

            console.log('Fetch models response status:', response.status)
            const data: FetchModelsResponse = await response.json()
            console.log('Fetch models data:', data)

            if (data.success && data.models.length > 0) {
                setModels(data.models)
                setSuccess(`Found ${data.models.length} models`)
            } else {
                setError(data.error || 'No models found')
            }
        } catch (err) {
            console.error('Fetch models error:', err)
            setError(err instanceof Error ? err.message : 'Failed to fetch models')
        } finally {
            setIsFetchingModels(false)
        }
    }

    const handleTestModel = async () => {
        if (!selectedModel) return

        setError(null)
        setIsTesting(true)
        setTestResult(null)

        try {
            const response = await fetch('/api/v1/admin/llm/test-model', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    provider,
                    base_url: baseUrl || null,
                    api_key: apiKey || null,
                    model: selectedModel,
                }),
            })

            const data: TestModelResponse = await response.json()
            setTestResult(data)

            if (!data.success) {
                setError(data.message)
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to test model')
            setTestResult({
                success: false,
                message: 'Network error',
            })
        } finally {
            setIsTesting(false)
        }
    }

    const handleSaveConfig = async () => {
        if (!selectedModel || !testResult?.success) return

        setError(null)
        setSuccess(null)
        setIsSaving(true)

        try {
            const response = await fetch('/api/v1/admin/llm/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    provider,
                    base_url: baseUrl || null,
                    api_key: apiKey || null,
                    model: selectedModel,
                }),
            })

            if (response.ok) {
                setSuccess('Configuration saved successfully!')
                // Reset form after successful save
                setTimeout(() => {
                    setSuccess(null)
                    setTestResult(null)
                }, 3000)
            } else {
                const data = await response.json()
                setError(data.detail || 'Failed to save configuration')
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to save configuration')
        } finally {
            setIsSaving(false)
        }
    }

    const currentProvider = providers.find(p => p.id === provider)
    const canFetchModels = provider && (!currentProvider?.requiresUrl || baseUrl)
    const canTest = selectedModel && models.length > 0
    const canSave = testResult?.success && selectedModel

    return (
        <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
            <div className="flex items-center space-x-3 mb-6">
                <div className="p-2 bg-blue-100 rounded-lg">
                    <Settings className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                    <h3 className="text-lg font-semibold text-gray-900">LLM Configuration</h3>
                    <p className="text-sm text-gray-600">
                        Configure your AI model provider and settings
                    </p>
                </div>
            </div>

            <div className="space-y-6">
                {/* Provider Selection */}
                <div>
                    <label className="block text-sm font-medium mb-2">
                        Provider
                    </label>
                    <select
                        value={provider}
                        onChange={(e) => {
                            setProvider(e.target.value)
                            setModels([])
                            setSelectedModel('')
                            setTestResult(null)
                            setError(null)
                        }}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                    >
                        {providers.map((p) => (
                            <option key={p.id} value={p.id}>
                                {p.name}
                            </option>
                        ))}
                    </select>
                </div>

                {/* Base URL (optional for some providers) */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        LLM URL {!currentProvider?.requiresUrl && '(Optional)'}
                    </label>
                    <input
                        type="text"
                        value={baseUrl}
                        onChange={(e) => setBaseUrl(e.target.value)}
                        placeholder={
                            currentProvider?.id === 'openai'
                                ? 'https://api.openai.com/v1'
                                : 'Enter base URL'
                        }
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-400"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                        Leave empty to use default provider URL
                    </p>
                </div>

                {/* API Key */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        API Key (Optional)
                    </label>
                    <input
                        type="password"
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder="Enter API key or leave empty to use environment variable"
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 placeholder-gray-400"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                        Leave empty to use API key from environment variables
                    </p>
                </div>

                {/* Fetch Models Button */}
                <div>
                    <button
                        onClick={handleFetchModels}
                        disabled={!canFetchModels || isFetchingModels}
                        className={`
                            w-full px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center space-x-2
                            ${canFetchModels && !isFetchingModels
                                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            }
                        `}
                    >
                        {isFetchingModels ? (
                            <>
                                <Loader2 className="h-4 w-4 animate-spin" />
                                <span>Fetching Models...</span>
                            </>
                        ) : (
                            <>
                                <Zap className="h-4 w-4" />
                                <span>Fetch Models</span>
                            </>
                        )}
                    </button>
                </div>

                {/* Models List */}
                {models.length > 0 && (
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Select Model
                        </label>
                        <select
                            value={selectedModel}
                            onChange={(e) => {
                                setSelectedModel(e.target.value)
                                setTestResult(null)
                            }}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900"
                        >
                            <option value="">Choose a model...</option>
                            {models.map((model) => (
                                <option key={model.id} value={model.id}>
                                    {model.name}
                                </option>
                            ))}
                        </select>
                        {selectedModel && (
                            <p className="text-xs text-gray-600 mt-1">
                                {models.find(m => m.id === selectedModel)?.description}
                            </p>
                        )}
                    </div>
                )}

                {/* Test Model Button */}
                {models.length > 0 && (
                    <div>
                        <button
                            onClick={handleTestModel}
                            disabled={!canTest || isTesting}
                            className={`
                                w-full px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center space-x-2
                                ${canTest && !isTesting
                                    ? 'bg-indigo-600 hover:bg-indigo-700 text-white'
                                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                }
                            `}
                        >
                            {isTesting ? (
                                <>
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    <span>Testing Model...</span>
                                </>
                            ) : (
                                <>
                                    <Zap className="h-4 w-4" />
                                    <span>Test Model</span>
                                </>
                            )}
                        </button>
                    </div>
                )}

                {/* Test Result */}
                {testResult && (
                    <div className={`
                        p-4 rounded-lg border-2
                        ${testResult.success
                            ? 'bg-green-50 border-green-200'
                            : 'bg-red-50 border-red-200'
                        }
                    `}>
                        <div className="flex items-start space-x-3">
                            {testResult.success ? (
                                <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                            ) : (
                                <XCircle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
                            )}
                            <div className="flex-1">
                                <p className={`font-medium ${testResult.success ? 'text-green-900' : 'text-red-900'}`}>
                                    {testResult.message}
                                </p>
                                {testResult.response && (
                                    <p className="text-sm text-gray-700 mt-2">
                                        Response: "{testResult.response}"
                                    </p>
                                )}
                                {testResult.latency_ms && (
                                    <p className="text-xs text-gray-600 mt-1">
                                        Latency: {testResult.latency_ms}ms
                                    </p>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* Submit Button */}
                {testResult?.success && (
                    <div>
                        <button
                            onClick={handleSaveConfig}
                            disabled={!canSave || isSaving}
                            className={`
                                w-full px-4 py-2 rounded-lg font-medium transition-colors flex items-center justify-center space-x-2
                                ${canSave && !isSaving
                                    ? 'bg-green-600 hover:bg-green-700 text-white'
                                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                }
                            `}
                        >
                            {isSaving ? (
                                <>
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    <span>Saving...</span>
                                </>
                            ) : (
                                <>
                                    <CheckCircle className="h-4 w-4" />
                                    <span>Save Configuration</span>
                                </>
                            )}
                        </button>
                    </div>
                )}

                {/* Error Message */}
                {error && (
                    <div className="flex items-center space-x-2 p-4 bg-red-50 border border-red-200 rounded-lg">
                        <AlertTriangle className="h-5 w-5 text-red-600 flex-shrink-0" />
                        <div>
                            <p className="text-sm font-medium text-red-900">Error</p>
                            <p className="text-xs text-red-700 mt-1">{error}</p>
                        </div>
                    </div>
                )}

                {/* Success Message */}
                {success && (
                    <div className="flex items-center space-x-2 p-4 bg-green-50 border border-green-200 rounded-lg">
                        <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
                        <div>
                            <p className="text-sm font-medium text-green-900">{success}</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
