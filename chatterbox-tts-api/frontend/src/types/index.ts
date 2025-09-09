export interface TTSRequest {
  input: string;
  voice?: string;
  exaggeration?: number;
  cfg_weight?: number;
  temperature?: number;
  voice_file?: File;
  session_id?: string;
  stream_format?: 'audio' | 'sse';
  streaming_chunk_size?: number;
  streaming_strategy?: 'sentence' | 'paragraph' | 'fixed' | 'word';
  streaming_quality?: 'fast' | 'balanced' | 'high';
}

export interface HealthResponse {
  status: string;
  model_loaded: boolean;
  device: string;
  config: any;
  memory_info?: {
    cpu_memory_mb: number;
    gpu_memory_allocated_mb: number;
  };
  initialization_state?: string;
  initialization_progress?: string;
  initialization_error?: string;
}

// New status API types
export interface TTSProgress {
  is_processing: boolean;
  status: string;
  current_step?: string;
  current_chunk?: number;
  total_chunks?: number;
  progress_percentage?: number;
  duration_seconds?: number;
  estimated_completion?: number;
  text_preview?: string;
  message?: string;
  request_id?: string;
  session_id?: string;
}

export interface TTSStatistics {
  total_requests: number;
  completed_requests: number;
  error_requests: number;
  success_rate: number;
  average_duration_seconds: number;
  average_text_length: number;
  is_processing: boolean;
  current_memory?: {
    cpu_memory_mb: number;
    gpu_memory_allocated_mb: number;
  };
}

export interface TTSRequestHistory {
  request_id: string;
  status: string;
  start_time: number;
  end_time?: number;
  duration_seconds: number;
  text_length: number;
  text_preview: string;
  voice_source: string;
  parameters: {
    exaggeration: number;
    cfg_weight: number;
    temperature: number;
  };
}

export interface TTSStatus {
  status: string;
  is_processing: boolean;
  request_id?: string;
  start_time?: number;
  duration_seconds?: number;
  text_length?: number;
  text_preview?: string;
  voice_source?: string;
  parameters?: {
    exaggeration: number;
    cfg_weight: number;
    temperature: number;
  };
  progress?: {
    current_chunk: number;
    total_chunks: number;
    current_step: string;
    progress_percentage: number;
    estimated_completion?: number;
  };
  total_requests: number;
  message?: string;
}

export interface APIInfo {
  api_name: string;
  version: string;
  status: string;
  tts_status: TTSStatus;
  statistics: TTSStatistics;
  memory_info?: {
    cpu_memory_mb: number;
    gpu_memory_allocated_mb: number;
  };
  recent_requests: TTSRequestHistory[];
  uptime_info: {
    total_requests: number;
    success_rate: number;
    is_processing: boolean;
  };
}

export interface VoiceSample {
  id: string;
  name: string;
  file: File;
  audioUrl: string;
  uploadDate: Date;
  aliases?: string[];
}

export interface AudioRecord {
  id: string;
  name: string;
  audioUrl: string;
  blob: Blob;
  createdAt: Date;
  settings: {
    text: string;
    exaggeration: number;
    cfgWeight: number;
    temperature: number;
    voiceId?: string;
    voiceName?: string;
  };
}

export interface VoiceLibraryItem {
  name: string;
  filename: string;
  original_filename: string;
  file_extension: string;
  file_size: number;
  upload_date: string;
  path: string;
  aliases?: string[];
}

export interface VoiceLibraryResponse {
  voices: VoiceLibraryItem[];
  count: number;
}

export interface DefaultVoiceResponse {
  default_voice: string | null;
  source: 'voice_library' | 'file_system';
  voice_info?: VoiceLibraryItem;
  path?: string;
}

export interface AudioInfo {
  sample_rate: number;
  channels: number;
  bits_per_sample: number;
}

export interface SSEAudioInfo {
  type: 'speech.audio.info';
  sample_rate: number;
  channels: number;
  bits_per_sample: number;
}

export interface SSEAudioDelta {
  type: 'speech.audio.delta';
  audio: string; // Base64 encoded audio chunk
}

export interface SSEAudioDone {
  type: 'speech.audio.done';
  usage: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
}

export type SSEEvent = SSEAudioInfo | SSEAudioDelta | SSEAudioDone;

export interface StreamingProgress {
  chunksReceived: number;
  totalBytes: number;
  isComplete: boolean;
  audioChunks: Blob[];
  currentChunk?: number;
  totalChunks?: number;
} 