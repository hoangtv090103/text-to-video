'use client'

import { useConnectionStatus } from '@/hooks/useConnectionStatus'

interface ConnectionStatusProps {
  className?: string
}

export const ConnectionStatus = ({ className = '' }: ConnectionStatusProps) => {
  const {
    status,
    lastChecked,
    error,
    retryCount,
    retryConnection,
    isConnected,
    isConnecting,
    isDisconnected,
    hasError
  } = useConnectionStatus()

  const getStatusColor = () => {
    if (isConnected) return 'text-green-600'
    if (isConnecting) return 'text-yellow-600'
    if (isDisconnected || hasError) return 'text-red-600'
    return 'text-gray-600'
  }

  const getStatusText = () => {
    if (isConnected) return 'Online'
    if (isConnecting) return 'Connecting...'
    if (isDisconnected) return 'Offline'
    if (hasError) return 'Error'
    return 'Unknown'
  }

  const getStatusIcon = () => {
    if (isConnected) {
      return (
        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
      )
    }
    if (isConnecting) {
      return (
        <div className="w-2 h-2 bg-yellow-500 rounded-full animate-spin"></div>
      )
    }
    if (isDisconnected || hasError) {
      return (
        <div className="w-2 h-2 bg-red-500 rounded-full"></div>
      )
    }
    return (
      <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
    )
  }

  const formatLastChecked = () => {
    if (!lastChecked) return ''
    const now = new Date()
    const diff = now.getTime() - lastChecked.getTime()
    const seconds = Math.floor(diff / 1000)
    
    if (seconds < 60) return `${seconds}s ago`
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    return `${hours}h ago`
  }

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      {getStatusIcon()}
      <div className="flex flex-col">
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-600">Status:</span>
          <span className={`text-sm font-medium ${getStatusColor()}`}>
            {getStatusText()}
          </span>
          {(isDisconnected || hasError) && retryCount > 0 && (
            <span className="text-xs text-gray-500">
              (retry {retryCount})
            </span>
          )}
        </div>
        {lastChecked && (
          <span className="text-xs text-gray-500">
            Last checked: {formatLastChecked()}
          </span>
        )}
        {error && (
          <div className="flex items-center space-x-2">
            <span className="text-xs text-red-500 truncate max-w-48">
              {error}
            </span>
            <button
              onClick={retryConnection}
              className="text-xs text-blue-600 hover:text-blue-800 underline"
              title="Retry connection"
            >
              Retry
            </button>
          </div>
        )}
      </div>
    </div>
  )
}


