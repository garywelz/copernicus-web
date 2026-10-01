import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  // Emergency lockdown, Step 1 (2026-10-01): this handler was an
  // unauthenticated proxy to an unresolved BACKEND_URL fallback
  // (copernicus-podcast-api-v2-204731194849.us-central1.run.app, confirmed
  // absent -- no such Cloud Run service exists in any region of the
  // project). Disabled rather than fixed in place; re-enable only behind
  // real auth once a live, audited target is decided. See
  // governance/BULLETIN.md and the architecture-review draft PR #24.
  return NextResponse.json(
    { error: 'Temporarily disabled' },
    { status: 503 }
  )
}

export async function GET() {
  return NextResponse.json({ 
    message: 'Copernicus Podcast Generation API',
    status: 'operational',
    endpoints: {
      'POST /api/generate': 'Generate a new podcast episode'
    }
  })
}
