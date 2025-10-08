import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const url = new URL(request.url)
    const provider = url.searchParams.get('provider')

    const targetUrl = provider
      ? `${apiUrl}/api/v1/admin/llm/cache/clear?provider=${provider}`
      : `${apiUrl}/api/v1/admin/llm/cache/clear`

    const response = await fetch(targetUrl, {
      method: 'POST'
    })

    if (!response.ok) {
      throw new Error(`Backend API error: ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error proxying to backend:', error)
    return NextResponse.json(
      { error: 'Failed to clear cache' },
      { status: 500 }
    )
  }
}
