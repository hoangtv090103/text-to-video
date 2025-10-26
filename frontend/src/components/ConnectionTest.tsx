'use client'

import { useState } from 'react'
import { videoApi } from '@/lib/api'

export const ConnectionTest = () => {
  const [testResult, setTestResult] = useState<string>('')
  const [isLoading, setIsLoading] = useState(false)

  const testConnection = async () => {
    setIsLoading(true)
    setTestResult('')
    
    try {
      const health = await videoApi.getHealth()
      setTestResult(`✅ Connection successful!\nStatus: ${health.status}\nService: ${health.service}\nDependencies: ${JSON.stringify(health.dependencies, null, 2)}`)
    } catch (error) {
      setTestResult(`❌ Connection failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="p-6 border border-gray-200 rounded-lg bg-white shadow-sm">
      <h3 className="text-lg font-semibold mb-4 admin-text">Connection Test</h3>
      <button
        onClick={testConnection}
        disabled={isLoading}
        className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isLoading ? 'Testing...' : 'Test Backend Connection'}
      </button>
      
      {testResult && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <pre className="text-sm whitespace-pre-wrap admin-text font-mono leading-relaxed">{testResult}</pre>
        </div>
      )}
    </div>
  )
}


