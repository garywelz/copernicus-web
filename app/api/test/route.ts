import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  console.log('🧪 TEST ENDPOINT CALLED');
  console.log('🧪 TIMESTAMP:', new Date().toISOString());
  console.log('🧪 REQUEST URL:', request.url);
  
  return NextResponse.json({
    message: 'Test endpoint working',
    timestamp: new Date().toISOString(),
    logs: 'Check Vercel logs for console.log messages'
  });
}

export async function POST(request: NextRequest) {
  console.log('🧪 TEST POST ENDPOINT CALLED');
  console.log('🧪 TIMESTAMP:', new Date().toISOString());
  console.log('🧪 REQUEST URL:', request.url);
  
  return NextResponse.json({
    message: 'Test POST endpoint working',
    timestamp: new Date().toISOString(),
    logs: 'Check Vercel logs for console.log messages'
  });
}
