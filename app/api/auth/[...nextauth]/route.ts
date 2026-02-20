import NextAuth from 'next-auth'
import GoogleProvider from 'next-auth/providers/google'
import { NextResponse } from 'next/server'

// Check if NextAuth is properly configured
const isConfigured = process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET

const handler = isConfigured ? NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          prompt: 'select_account',
        },
      },
    })
  ],
  callbacks: {
    async signIn({ user, account, profile }) {
      // Allow all Google sign-ins
      return true
    },
    async session({ session, user }) {
      // Add custom session data
      return session
    },
    async jwt({ token, user, account }) {
      // Add custom JWT data
      return token
    }
  },
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error',
  },
  session: {
    strategy: 'jwt',
  },
}) : null

// If not configured, return empty responses
export async function GET(request: Request) {
  if (!handler) {
    return NextResponse.json({ error: 'NextAuth not configured' }, { status: 503 })
  }
  return handler(request as any)
}

export async function POST(request: Request) {
  if (!handler) {
    return NextResponse.json({ error: 'NextAuth not configured' }, { status: 503 })
  }
  return handler(request as any)
}
