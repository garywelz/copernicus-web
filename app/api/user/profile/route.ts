import { NextRequest, NextResponse } from 'next/server'
import { google } from 'googleapis'

// Initialize Firestore
const { initializeApp, cert } = require('firebase-admin/app')
const { getFirestore } = require('firebase-admin/firestore')

if (!global.firebaseApp) {
  // Use environment variables for Firebase credentials
  const serviceAccount = {
    type: "service_account",
    project_id: process.env.FIREBASE_PROJECT_ID,
    private_key_id: process.env.FIREBASE_PRIVATE_KEY_ID,
    private_key: process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g, '\n'),
    client_email: process.env.FIREBASE_CLIENT_EMAIL,
    client_id: process.env.FIREBASE_CLIENT_ID,
    auth_uri: "https://accounts.google.com/o/oauth2/auth",
    token_uri: "https://oauth2.googleapis.com/token",
    auth_provider_x509_cert_url: "https://www.googleapis.com/oauth2/v1/certs",
    client_x509_cert_url: `https://www.googleapis.com/robot/v1/metadata/x509/${process.env.FIREBASE_CLIENT_EMAIL}`
  }
  
  if (!serviceAccount.project_id || !serviceAccount.private_key || !serviceAccount.client_email) {
    console.error('Missing Firebase environment variables')
    throw new Error('Firebase credentials not configured')
  }
  
  global.firebaseApp = initializeApp({
    credential: cert(serviceAccount)
  })
}

const db = getFirestore(global.firebaseApp)

export async function GET(request: NextRequest) {
  try {
    const authHeader = request.headers.get('authorization')
    if (!authHeader?.startsWith('Bearer ')) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const email = authHeader.substring(7)
    
    // Get user from Firestore
    const userDoc = await db.collection('users').doc(email).get()
    
    if (!userDoc.exists) {
      // Create new user
      const newUser = {
        id: email,
        email,
        name: email.split('@')[0],
        subscriptionTier: 'free',
        subscriptionStatus: 'active',
        podcastsUsed: 0,
        podcastsLimit: 10,
        createdAt: new Date().toISOString(),
        lastLogin: new Date().toISOString()
      }
      
      await db.collection('users').doc(email).set(newUser)
      return NextResponse.json(newUser)
    }
    
    const userData = userDoc.data()
    
    // Update last login
    await db.collection('users').doc(email).update({
      lastLogin: new Date().toISOString()
    })
    
    return NextResponse.json({
      ...userData,
      lastLogin: new Date().toISOString()
    })
    
  } catch (error) {
    console.error('Error fetching user profile:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

export async function PUT(request: NextRequest) {
  try {
    const authHeader = request.headers.get('authorization')
    if (!authHeader?.startsWith('Bearer ')) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const email = authHeader.substring(7)
    const updates = await request.json()
    
    // Update user in Firestore
    await db.collection('users').doc(email).update({
      ...updates,
      updatedAt: new Date().toISOString()
    })
    
    return NextResponse.json({ success: true })
    
  } catch (error) {
    console.error('Error updating user profile:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
