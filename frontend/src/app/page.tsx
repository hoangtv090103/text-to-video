'use client'

import { useState } from 'react'
import { FileUpload } from '@/components/FileUpload'
import { JobStatus } from '@/components/JobStatus'
import { JobsList } from '@/components/JobsList'
import { AdminPanel } from '@/components/AdminPanel'

export default function Home() {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('upload')

  const handleJobCreated = (jobId: string) => {
    setSelectedJobId(jobId)
    setActiveTab('jobs')
  }

  const handleJobSelect = (jobId: string) => {
    setSelectedJobId(jobId)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">V</span>
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Text-to-Video Generator</h1>
                <p className="text-sm text-gray-600">Generate videos from text documents</p>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-600">
                Status: <span className="text-green-600 font-medium">Online</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-6">
          {/* Tab Navigation */}
          <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
            <button
              onClick={() => setActiveTab('upload')}
              className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${activeTab === 'upload'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
                }`}
            >
              Upload
            </button>
            <button
              onClick={() => setActiveTab('jobs')}
              className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${activeTab === 'jobs'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
                }`}
            >
              Jobs
            </button>
            <button
              onClick={() => setActiveTab('active')}
              className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${activeTab === 'active'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
                }`}
            >
              Active
            </button>
            <button
              onClick={() => setActiveTab('admin')}
              className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${activeTab === 'admin'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
                }`}
            >
              Admin
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === 'upload' && (
            <div className="space-y-6">
              <div className="text-center">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Upload Your Document</h2>
                <p className="text-gray-600 mb-8">
                  Upload a text, PDF, or markdown file to generate a video presentation
                </p>
              </div>

              <FileUpload onJobCreated={handleJobCreated} />

              {selectedJobId && (
                <div className="mt-8">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Job Status</h3>
                  <JobStatus jobId={selectedJobId} />
                </div>
              )}
            </div>
          )}

          {activeTab === 'jobs' && (
            <div className="space-y-6">
              <div className="text-center">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Recent Jobs</h2>
                <p className="text-gray-600 mb-8">
                  View all your video generation jobs and their status
                </p>
              </div>

              <JobsList onJobSelect={handleJobSelect} />

              {selectedJobId && (
                <div className="mt-8">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Selected Job Details</h3>
                  <JobStatus jobId={selectedJobId} />
                </div>
              )}
            </div>
          )}

          {activeTab === 'active' && (
            <div className="space-y-6">
              <div className="text-center">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Active Jobs</h2>
                <p className="text-gray-600 mb-8">
                  Monitor currently running video generation jobs
                </p>
              </div>

              <JobsList showActiveOnly={true} onJobSelect={handleJobSelect} />

              {selectedJobId && (
                <div className="mt-8">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Selected Job Details</h3>
                  <JobStatus jobId={selectedJobId} />
                </div>
              )}
            </div>
          )}

          {activeTab === 'admin' && (
            <div className="space-y-6">
              <div className="text-center">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">System Administration</h2>
                <p className="text-gray-600 mb-8">
                  Manage system resources and perform maintenance tasks
                </p>
              </div>

              <AdminPanel />
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-sm text-gray-600">
            <p>Text-to-Video Generator - Built with Next.js and FastAPI</p>
            <p className="mt-1">Supports .txt, .pdf, and .md files up to 50MB</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
