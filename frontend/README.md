# Text-to-Video Frontend

A modern Next.js frontend for the Text-to-Video generation service.

## Features

- **File Upload**: Drag-and-drop or browse to upload text, PDF, or markdown files
- **Job Management**: Real-time job status tracking with progress indicators
- **Job History**: View all previous jobs and their outcomes
- **Active Jobs**: Monitor currently running jobs
- **Admin Panel**: System cleanup and maintenance tools
- **Responsive Design**: Works on desktop and mobile devices

## Tech Stack

- **Next.js 15** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **Lucide React** - Beautiful icons
- **Axios** - HTTP client for API calls
- **SWR** - Data fetching and caching

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Backend server running on port 8000

### Installation

1. Install dependencies:
```bash
npm install
```

2. Create environment file:
```bash
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

3. Start the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Available Scripts

- `npm run dev` - Start development server with Turbopack
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## Project Structure

```
src/
├── app/                 # Next.js App Router
│   ├── layout.tsx      # Root layout
│   └── page.tsx        # Home page
├── components/         # React components
│   ├── FileUpload.tsx  # File upload component
│   ├── JobStatus.tsx   # Job status display
│   ├── JobsList.tsx    # Jobs listing
│   └── AdminPanel.tsx  # Admin interface
├── hooks/             # Custom React hooks
│   ├── useVideoGeneration.ts
│   └── useJobs.ts
├── lib/               # Utilities and API clients
│   ├── api.ts        # API client
│   └── utils.ts      # Utility functions
├── types/             # TypeScript type definitions
│   └── api.ts        # API response types
└── styles/           # Global styles
```

## API Integration

The frontend communicates with the backend API at the configured `NEXT_PUBLIC_API_URL`. Key endpoints:

- `POST /api/v1/video/generate` - Upload file and start video generation
- `GET /api/v1/video/status/{job_id}` - Get job status and progress
- `GET /api/v1/video/jobs` - List all jobs
- `POST /api/v1/video/cancel/{job_id}` - Cancel a running job
- `GET /api/v1/video/active` - Get active jobs
- `POST /api/v1/admin/cleanup` - Clean up expired jobs

## Features in Detail

### File Upload
- Drag-and-drop interface
- File type validation (txt, pdf, md)
- File size validation (50MB limit)
- Real-time upload progress

### Job Status Tracking
- Real-time polling for job updates
- Progress bars and status indicators
- Detailed error messages
- Job cancellation support

### Admin Panel
- System health monitoring
- Job cleanup operations
- Queue length monitoring
- System information display

## Configuration

### Environment Variables

- `NEXT_PUBLIC_API_URL` - Backend API base URL (default: http://localhost:8000)

### File Size Limits

- Maximum file size: 50MB
- Supported formats: .txt, .pdf, .md

## Development

### Adding New Features

1. Create new components in `src/components/`
2. Add API calls in `src/lib/api.ts`
3. Create custom hooks in `src/hooks/`
4. Update types in `src/types/`

### Styling

Uses Tailwind CSS with custom components. Follow the existing design patterns for consistency.

### Error Handling

The app includes comprehensive error handling with user-friendly error messages and retry mechanisms.

## Deployment

Build the application for production:

```bash
npm run build
npm run start
```

The app can be deployed to Vercel, Netlify, or any platform that supports Next.js.
