import { NextRequest, NextResponse } from 'next/server'
import { google } from 'googleapis'

// Initialize Firestore
const { initializeApp, cert } = require('firebase-admin/app')
const { getFirestore } = require('firebase-admin/firestore')

if (!global.firebaseApp) {
  const serviceAccount = require('../../../../regal-scholar-453620-r7-b4a72581927b.json')
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
