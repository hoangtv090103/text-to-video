import React, { useState, useMemo } from 'react';
import { Volume2 } from 'lucide-react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Button } from '../components/ui/button';
import {
  ApiEndpointSelector,
  TextInput,
  AdvancedSettings,
  AudioPlayer
} from '../components/tts';
import VoiceLibrary from '../components/VoiceLibrary';
import AudioHistory from '../components/AudioHistory';
import StatusHeader from '../components/StatusHeader';
import StatusProgressOverlay from '../components/StatusProgressOverlay';
import StatusStatisticsPanel from '../components/StatusStatisticsPanel';
import StreamingProgressComponent from '../components/tts/StreamingProgress';
import { createTTSService } from '../services/tts';
import { useApiEndpoint } from '../hooks/useApiEndpoint';
import { useVoiceLibrary } from '../hooks/useVoiceLibrary';
import { useAudioHistory } from '../hooks/useAudioHistory';
import { useAdvancedSettings } from '../hooks/useAdvancedSettings';
import { useTextInput } from '../hooks/useTextInput';
import { useStatusMonitoring } from '../hooks/useStatusMonitoring';
import { useProgressSettings } from '../hooks/useProgressSettings';
import { useDefaultVoice } from '../hooks/useDefaultVoice';
import { useStreamingTTS } from '../hooks/useStreamingTTS';
import type { TTSRequest } from '../types';

export default function TTSPage() {
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showStatistics, setShowStatistics] = useState(false);

  // API endpoint management
  const { apiBaseUrl, updateApiBaseUrl } = useApiEndpoint();

  // Text input management with persistence
  const { text, updateText, clearText, hasText } = useTextInput();

  // Advanced settings management with persistence
  const {
    exaggeration,
    cfgWeight,
    temperature,
    updateExaggeration,
    updateCfgWeight,
    updateTemperature,
    resetToDefaults,
    isDefault
  } = useAdvancedSettings();

  // Progress settings and session tracking
  const {
    settings: progressSettings,
    updateSettings: updateProgressSettings,
    trackRequest,
    shouldShowProgress,
    dismissProgress,
    sessionId
  } = useProgressSettings();

  // Streaming TTS management
  const {
    isStreaming,
    progress: streamingProgress,
    audioUrl: streamingAudioUrl,
    error: streamingError,
    audioInfo,
    isStreamingEnabled,
    toggleStreaming,
    streamingFormat,
    setStreamingFormat,
    startStreaming,
    stopStreaming,
    clearAudio: clearStreamingAudio
  } = useStreamingTTS({
    apiBaseUrl,
    sessionId
  });

  // Voice library management with backend health monitoring
  const {
    voices,
    selectedVoice,
    setSelectedVoice,
    addVoice,
    deleteVoice,
    renameVoice,
    refreshVoices,
    addAlias,
    removeAlias,
    isLoading: voicesLoading,
    isBackendReady: voicesBackendReady,
    error: voicesError
  } = useVoiceLibrary();

  // Audio history management
  const {
    audioHistory,
    addAudioRecord,
    deleteAudioRecord,
    renameAudioRecord,
    clearHistory,
    isLoading: historyLoading
  } = useAudioHistory();

  // Default voice management with backend health monitoring
  const {
    defaultVoice,
    updateDefaultVoice,
    clearDefaultVoice,
    isLoading: defaultVoiceLoading,
    isBackendReady: defaultVoiceBackendReady,
    healthStatus
  } = useDefaultVoice();

  // Create TTS service with current API base URL and session ID
  const ttsService = useMemo(() => createTTSService(apiBaseUrl, sessionId), [apiBaseUrl, sessionId]);

  // Status monitoring with real-time updates
  const {
    progress,
    statistics,
    isProcessing,
    hasError: statusHasError,
    isLoadingStats
  } = useStatusMonitoring(apiBaseUrl);

  const { data: health, isLoading: isLoadingHealth } = useQuery({
    queryKey: ['health', apiBaseUrl],
    queryFn: ttsService.getHealth,
    refetchInterval: 3000, // More frequent during startup
    retry: true,
    retryDelay: 1000
  });

  // Fetch API info (including version) periodically
  const { data: apiInfo } = useQuery({
    queryKey: ['apiInfo', apiBaseUrl],
    queryFn: async () => {
      const response = await fetch(`${apiBaseUrl}/info`);
      if (!response.ok) throw new Error('Failed to fetch API info');
      return response.json();
    },
    refetchInterval: 60000, // Refresh every minute
    retry: false
  });

  // Standard (non-streaming) generation mutation
  const generateMutation = useMutation({
    mutationFn: ttsService.generateSpeech,
    onMutate: (variables) => {
      // Track this request as originating from this frontend
      if (variables.session_id) {
        trackRequest(variables.session_id);
      }
    },
    onSuccess: async (audioBlob) => {
      // Clean up previous audio URL
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }

      // Create new audio URL
      const url = URL.createObjectURL(audioBlob);
      setAudioUrl(url);

      // Save to audio history
      try {
        await addAudioRecord(
          audioBlob,
          {
            text,
            exaggeration,
            cfgWeight,
            temperature,
            voiceId: selectedVoice?.id,
            voiceName: selectedVoice?.name
          }
        );
      } catch (error) {
        console.error('Failed to save audio record:', error);
      }
    },
    onError: (error) => {
      console.error('TTS generation failed:', error);
      alert('Failed to generate speech. Please try again.');
    }
  });

  const handleGenerate = async () => {
    if (!text.trim()) {
      alert('Please enter some text to convert to speech.');
      return;
    }

    // Prepare request data
    const requestData: TTSRequest = {
      input: text,
      exaggeration,
      cfg_weight: cfgWeight,
      temperature,
      session_id: sessionId
    };

    if (selectedVoice) {
      // Use voice name for backend voice library
      requestData.voice = selectedVoice.name;

      // Also include voice file if it's a client-side voice (for backward compatibility)
      if (selectedVoice.file) {
        requestData.voice_file = selectedVoice.file;
      }
    }

    // Track this request
    trackRequest(sessionId);

    if (isStreamingEnabled) {
      // Use streaming
      try {
        await startStreaming(requestData);

        // If streaming completes successfully and we have a final audio URL, save to history
        if (streamingAudioUrl) {
          try {
            const response = await fetch(streamingAudioUrl);
            const audioBlob = await response.blob();

            await addAudioRecord(
              audioBlob,
              {
                text,
                exaggeration,
                cfgWeight,
                temperature,
                voiceId: selectedVoice?.id,
                voiceName: selectedVoice?.name
              }
            );
          } catch (error) {
            console.error('Failed to save streaming audio to history:', error);
          }
        }
      } catch (error) {
        console.error('Streaming failed:', error);
        alert('Failed to stream speech. Please try again.');
      }
    } else {
      // Use standard generation
      generateMutation.mutate(requestData);
    }
  };

  // Determine if backend is ready for voice operations
  const isBackendReady = voicesBackendReady && defaultVoiceBackendReady;
  const isInitializing = healthStatus === 'initializing' || health?.status === 'initializing';

  // Determine if generation is in progress (streaming or standard)
  const isGenerating = generateMutation.isPending || isStreaming;

  // Use streaming audio URL if available, otherwise use standard audio URL
  const currentAudioUrl = streamingAudioUrl || audioUrl;

  return (
    <>
      <div className="container mx-auto px-4 py-8 flex flex-col items-center justify-center gap-4">
        {/* Status Header */}
        <div className="flex justify-between items-start w-full max-w-4xl mx-auto relative">
          <div className="flex-1">
            <StatusHeader
              health={health}
              progress={progress}
              statistics={statistics}
              isLoadingHealth={isLoadingHealth}
              hasErrors={statusHasError}
              apiVersion={apiInfo?.version || apiInfo?.api_version}
              progressSettings={{
                onlyShowMyRequests: progressSettings.onlyShowMyRequests,
                onToggleOnlyMyRequests: () => updateProgressSettings({
                  onlyShowMyRequests: !progressSettings.onlyShowMyRequests
                })
              }}
              defaultVoiceSettings={{
                defaultVoice,
                voices,
                onSetDefaultVoice: updateDefaultVoice,
                onClearDefaultVoice: clearDefaultVoice,
                isLoading: voicesLoading || defaultVoiceLoading
              }}
            />
          </div>
        </div>

        {/* Backend Loading State */}
        {(isInitializing || !isBackendReady) && (
          <div className="w-full max-w-2xl mx-auto">
            <div className="bg-primary/10 border border-primary/20 rounded-lg p-4 text-center">
              <div className="flex items-center justify-center gap-2 mb-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                <span className="text-sm font-medium text-primary">
                  {isInitializing ? 'Backend initializing...' : 'Loading voice library...'}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {isInitializing
                  ? 'TTS model is starting up. Voice library will load once ready.'
                  : 'Connecting to voice library and loading default settings.'
                }
              </p>
            </div>
          </div>
        )}

        <div className="w-full max-w-2xl mx-auto flex flex-col items-center justify-center gap-4">

          <div className="flex flex-col items-center justify-center gap-2 w-full">
            <button
              onClick={() => setShowStatistics(!showStatistics)}
              className="px-3 py-1 text-xs bg-primary/10 hover:bg-primary/20 text-primary rounded-full transition-colors duration-300"
            >
              {showStatistics ? 'Hide Stats' : 'Show Stats'}
            </button>
            {/* Statistics Panel (collapsible) */}
            {showStatistics && (
              <StatusStatisticsPanel
                statistics={statistics}
                isLoading={isLoadingStats}
                hasError={statusHasError}
              />
            )}
          </div>

          <div className="max-w-2xl mx-auto gap-4 flex flex-col w-full">
            {/* API Endpoint Selector */}
            <div className="">
              <ApiEndpointSelector
                apiBaseUrl={apiBaseUrl}
                onUrlChange={updateApiBaseUrl}
              />
            </div>

            {/* Text Input */}
            <TextInput
              value={text}
              onChange={updateText}
              onClear={clearText}
              hasText={hasText}
              isStreamingEnabled={isStreamingEnabled}
              onToggleStreaming={toggleStreaming}
            />

            {/* Streaming Progress */}
            {(isStreaming || streamingProgress || streamingAudioUrl || streamingError) && (
              <StreamingProgressComponent
                isStreaming={isStreaming}
                progress={streamingProgress}
                audioUrl={streamingAudioUrl}
                error={streamingError}
                audioInfo={audioInfo}
                onStop={stopStreaming}
                onClear={clearStreamingAudio}
              />
            )}

            {/* Voice Library */}
            <VoiceLibrary
              voices={voices}
              selectedVoice={selectedVoice}
              onVoiceSelect={setSelectedVoice}
              onAddVoice={addVoice}
              onDeleteVoice={deleteVoice}
              onRenameVoice={renameVoice}
              onRefresh={refreshVoices}
              isLoading={voicesLoading}
              defaultVoice={defaultVoice}
              onSetDefaultVoice={updateDefaultVoice}
              onClearDefaultVoice={clearDefaultVoice}
              onAddAlias={addAlias}
              onRemoveAlias={removeAlias}
            />

            {/* Voice Library Error Display */}
            {voicesError && !voicesLoading && (
              <div className="text-center py-4 text-muted-foreground">
                <p className="text-sm text-destructive mb-2">
                  Failed to load voice library: {voicesError.message || 'Unknown error'}
                </p>
                <button
                  onClick={refreshVoices}
                  className="text-xs text-primary hover:text-primary/80 underline"
                >
                  Retry
                </button>
              </div>
            )}

            {/* Advanced Settings */}
            <AdvancedSettings
              showAdvanced={showAdvanced}
              onToggle={() => setShowAdvanced(!showAdvanced)}
              exaggeration={exaggeration}
              onExaggerationChange={updateExaggeration}
              cfgWeight={cfgWeight}
              onCfgWeightChange={updateCfgWeight}
              temperature={temperature}
              onTemperatureChange={updateTemperature}
              onResetToDefaults={resetToDefaults}
              isDefault={isDefault}
            />

            {/* Current Voice Indicator */}
            {selectedVoice && (
              <div className="text-center text-sm text-muted-foreground">
                Using voice: <span className="font-medium text-foreground">{selectedVoice.name}</span>
                {defaultVoice === selectedVoice.name && (
                  <span className="ml-2 text-xs bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 px-2 py-1 rounded">
                    Default
                  </span>
                )}
              </div>
            )}

            {/* Generate Button */}
            <Button
              onClick={handleGenerate}
              disabled={isGenerating || !hasText}
              className="w-full py-6 px-6 text-xl [&_svg]:size-6 [&_svg:not([class*='size-'])]:size-6 flex gap-4"
            >
              <Volume2 className="w-5 h-5 mr-2" />
              {isGenerating ? (isStreaming ? 'Streaming...' : 'Generating...') : 'Generate Speech'}
            </Button>

            {/* Audio Player - Only show for non-streaming audio or completed streaming */}
            {currentAudioUrl && !isStreaming && (
              <AudioPlayer audioUrl={currentAudioUrl} />
            )}
          </div>
        </div>

        {/* Audio History */}
        <div className="w-full max-w-2xl mx-auto">
          <AudioHistory
            audioHistory={audioHistory}
            onDeleteAudioRecord={deleteAudioRecord}
            onRenameAudioRecord={renameAudioRecord}
            onClearHistory={clearHistory}
            onRestoreSettings={(settings) => {
              updateExaggeration(settings.exaggeration);
              updateCfgWeight(settings.cfgWeight);
              updateTemperature(settings.temperature);
            }}
            onRestoreText={updateText}
            isLoading={historyLoading}
          />
        </div>
      </div>

      {/* Progress Overlay */}
      {shouldShowProgress(progress?.request_id) && progress && (
        <StatusProgressOverlay
          progress={progress}
          isVisible={shouldShowProgress(progress?.request_id)}
          onDismiss={dismissProgress}
        />
      )}
    </>
  );
} 