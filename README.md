# Text-to-Video Generation Service

A robust, asynchronous, and scalable FastAPI microservice for generating videos from text. The system orchestrates parallel generation of audio and visual assets and composes them into final videos.

## Features

- **Asynchronous Processing**: Uses asyncio for concurrent audio and visual asset generation
- **Resilient Architecture**: Implements exponential backoff retry mechanisms and graceful error handling
- **Scalable State Management**: Redis-based distributed state management
- **Structured Logging**: JSON-formatted logs with comprehensive context
- **Containerized**: Docker and Docker Compose ready
- **Modern Best Practices**: Built with FastAPI, Pydantic, and modern Python patterns

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Orchestrator   │    │   Services      │
│   Endpoints     │───▶│   (Core Logic)   │───▶│   (TTS, Visual) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                       │
         ▼                        ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Background    │    │   Composer       │    │   Asset Router  │
│   Tasks         │    │   (State Mgmt)   │    │   (Routing)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │     Redis       │
                       │  (State Store)  │
                       └─────────────────┘
```

## Project Structure

```
text-to-video-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, endpoint definitions
│   ├── orchestrator.py         # Main business logic
│   ├── composer.py             # State management with Redis
│   ├── asset_router.py         # Visual generation routing
│   ├── services/
│   │   ├── __init__.py
│   │   ├── tts_service.py      # Mock TTS service
│   │   ├── visual_services.py  # Mock visual services
│   │   └── llm_service.py      # Mock LLM service
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Pydantic configuration
│   │   └── logging_config.py   # JSON logging setup
│   └── schemas/
│       ├── __init__.py
│       └── video.py            # API models
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env
```

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone and navigate to the project**:
   ```bash
   cd text-to-video-service
   ```

2. **Start the services**:
   ```bash
   docker-compose up --build
   ```

3. **Test the API**:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/video/generate" \
        -H "Content-Type: application/json" \
        -d '{"source_text": "Explain machine learning concepts and applications"}'
   ```

### Manual Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Redis**:
   ```bash
   redis-server
   ```

3. **Run the application**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## API Endpoints

### Generate Video
**POST** `/api/v1/video/generate`

Generate a video from source text.

**Request Body**:
```json
{
  "source_text": "Your text content to convert into video"
}
```

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

### Health Check
**GET** `/health`

Check service health status.

### Job Status (Basic Implementation)
**GET** `/api/v1/video/status/{job_id}`

Get the status of a video generation job.

## Configuration

The service is configured via environment variables:

- `REDIS_HOST`: Redis host (default: localhost)
- `REDIS_PORT`: Redis port (default: 6379)
- `REDIS_DB`: Redis database number (default: 0)
- `LOG_LEVEL`: Logging level (default: INFO)

## Processing Flow

1. **Request Reception**: FastAPI receives video generation request
2. **Script Generation**: LLM service generates structured scene script
3. **Parallel Processing**: For each scene:
   - Audio generation (TTS service)
   - Visual generation (routing to appropriate visual service)
4. **State Management**: Redis tracks completion of assets
5. **Composition**: When both audio and visual assets are ready, segment is marked for rendering

## Visual Asset Types

The system supports multiple visual types:

- `slide`: Presentation slides (via Presenton service)
- `diagram`: Flowcharts and diagrams (via Mermaid service)
- `code`: Code visualizations (via Matplotlib service)
- `formula`: Mathematical formulas (via LaTeX service)
- Unsupported types fallback to generic service with placeholder

## Resilience Features

- **Exponential Backoff**: 3 retry attempts with exponential delay
- **Graceful Degradation**: Failed visual assets use placeholder images
- **Comprehensive Logging**: Structured JSON logs for debugging and monitoring
- **Error Isolation**: Individual asset failures don't crash the entire job

## Development

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests (to be implemented)
pytest
```

### Viewing Logs
Logs are output in structured JSON format. For development, you can use tools like `jq` to format them:

```bash
docker-compose logs text-to-video-service | jq .
```

## Production Considerations

1. **Security**: Update CORS settings and implement authentication
2. **Scaling**: Use Redis Cluster for high availability
3. **Monitoring**: Integrate with monitoring solutions (Prometheus, Grafana)
4. **Storage**: Implement proper file storage (S3, etc.)
5. **Queue Management**: Consider using Celery or similar for job queuing

## License

This project is a prototype implementation for educational purposes.
