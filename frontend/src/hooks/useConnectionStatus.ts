import { useState, useEffect, useCallback } from 'react'
import { videoApi } from '@/lib/api'

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error'

export interface ConnectionInfo {
  status: ConnectionStatus
  lastChecked: Date | null
  error?: string
  retryCount: number
}

export const useConnectionStatus = (checkInterval: number = 30000) => {
  const [connectionInfo, setConnectionInfo] = useState<ConnectionInfo>({
    status: 'connecting',
    lastChecked: null,
    retryCount: 0
  })

  const checkConnection = useCallback(async () => {
    try {
      setConnectionInfo(prev => ({
        ...prev,
        status: 'connecting',
        lastChecked: new Date()
      }))

      const healthResponse = await videoApi.getHealth()
      
      if (healthResponse.status === 'healthy') {
        setConnectionInfo(prev => ({
          status: 'connected',
          lastChecked: new Date(),
          error: undefined,
          retryCount: 0
        }))
      } else {
        setConnectionInfo(prev => ({
          status: 'error',
          lastChecked: new Date(),
          error: `Backend status: ${healthResponse.status}`,
          retryCount: prev.retryCount + 1
        }))
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      setConnectionInfo(prev => ({
        status: 'disconnected',
        lastChecked: new Date(),
        error: errorMessage,
        retryCount: prev.retryCount + 1
      }))
    }
  }, [])

  useEffect(() => {
    // Check immediately on mount
    checkConnection()

    // Set up interval for periodic checks
    const interval = setInterval(checkConnection, checkInterval)

    return () => clearInterval(interval)
  }, [checkConnection, checkInterval])

  // Manual retry function
  const retryConnection = useCallback(() => {
    checkConnection()
  }, [checkConnection])

  return {
    ...connectionInfo,
    retryConnection,
    isConnected: connectionInfo.status === 'connected',
    isConnecting: connectionInfo.status === 'connecting',
    isDisconnected: connectionInfo.status === 'disconnected',
    hasError: connectionInfo.status === 'error'
  }
}

