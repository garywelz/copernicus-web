import { NextRequest, NextResponse } from 'next/server'
import Stripe from 'stripe'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2023-10-16'
})

// Lazy Firebase initialization (only when needed, not during build)
const { initializeApp, cert } = require('firebase-admin/app')
const { getFirestore } = require('firebase-admin/firestore')

declare global {
  var firebaseApp: any
  var firestoreDb: any
}

function getFirestoreDb() {
  if (global.firestoreDb) {
    return global.firestoreDb
  }

  if (!global.firebaseApp) {
    // Check if we're in build mode (no env vars)
    if (process.env.NEXT_PHASE === 'phase-production-build' || !process.env.FIREBASE_PROJECT_ID) {
      // Return a mock db that throws on use (won't be called during build)
      return {
        collection: () => ({
          doc: () => ({
            get: async () => { throw new Error('Firebase not initialized - build mode') },
            set: async () => { throw new Error('Firebase not initialized - build mode') },
            update: async () => { throw new Error('Firebase not initialized - build mode') },
            ref: { update: async () => { throw new Error('Firebase not initialized - build mode') } }
          }),
          where: () => ({
            get: async () => { throw new Error('Firebase not initialized - build mode') }
          })
        })
      }
    }

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
      throw new Error('Firebase credentials not configured')
    }
    
    global.firebaseApp = initializeApp({
      credential: cert(serviceAccount)
    })
  }

  global.firestoreDb = getFirestore(global.firebaseApp)
  return global.firestoreDb
}

export async function POST(request: NextRequest) {
  try {
    const { userEmail, planId, action } = await request.json()
    
    if (!userEmail || !planId) {
      return NextResponse.json({ error: 'User email and plan ID required' }, { status: 400 })
    }

    const db = getFirestoreDb()
    const userDoc = await db.collection('users').doc(userEmail).get()
    if (!userDoc.exists) {
      return NextResponse.json({ error: 'User not found' }, { status: 404 })
    }

    const userData = userDoc.data()

    switch (action) {
      case 'upgrade':
        return await handleUpgrade(userEmail, planId, userData)
      
      case 'cancel':
        return await handleCancellation(userEmail, userData)
      
      case 'reactivate':
        return await handleReactivation(userEmail, userData)
      
      default:
        return NextResponse.json({ error: 'Invalid action' }, { status: 400 })
    }

  } catch (error) {
    console.error('Error managing subscription:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

async function handleUpgrade(userEmail: string, planId: string, userData: any) {
  try {
    // Create Stripe checkout session
    const session = await stripe.checkout.sessions.create({
      customer_email: userEmail,
      payment_method_types: ['card'],
      line_items: [
        {
          price: getStripePriceId(planId),
          quantity: 1,
        },
      ],
      mode: 'subscription',
      success_url: `${process.env.NEXT_PUBLIC_BASE_URL}/subscription/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${process.env.NEXT_PUBLIC_BASE_URL}/subscription/canceled`,
      metadata: {
        userEmail,
        planId
      }
    })

    return NextResponse.json({ 
      checkoutUrl: session.url,
      sessionId: session.id 
    })

  } catch (error) {
    console.error('Error creating checkout session:', error)
    return NextResponse.json({ error: 'Failed to create checkout session' }, { status: 500 })
  }
}

async function handleCancellation(userEmail: string, userData: any) {
  try {
    // If user has an active Stripe subscription, cancel it
    if (userData.stripeSubscriptionId) {
      await stripe.subscriptions.update(userData.stripeSubscriptionId, {
        cancel_at_period_end: true
      })
    }

    // Update user status in Firestore
    const db = getFirestoreDb()
    await db.collection('users').doc(userEmail).update({
      subscriptionStatus: 'cancelled',
      cancelledAt: new Date().toISOString()
    })

    return NextResponse.json({ success: true })

  } catch (error) {
    console.error('Error canceling subscription:', error)
    return NextResponse.json({ error: 'Failed to cancel subscription' }, { status: 500 })
  }
}

async function handleReactivation(userEmail: string, userData: any) {
  try {
    // Reactivate Stripe subscription if it exists
    if (userData.stripeSubscriptionId) {
      await stripe.subscriptions.update(userData.stripeSubscriptionId, {
        cancel_at_period_end: false
      })
    }

    // Update user status in Firestore
    const db = getFirestoreDb()
    await db.collection('users').doc(userEmail).update({
      subscriptionStatus: 'active',
      reactivatedAt: new Date().toISOString()
    })

    return NextResponse.json({ success: true })

  } catch (error) {
    console.error('Error reactivating subscription:', error)
    return NextResponse.json({ error: 'Failed to reactivate subscription' }, { status: 500 })
  }
}

function getStripePriceId(planId: string): string {
  const priceIds: { [key: string]: string } = {
    'premium': process.env.STRIPE_PREMIUM_PRICE_ID!,
    'research': process.env.STRIPE_RESEARCH_PRICE_ID!
  }
  
  return priceIds[planId] || ''
}

// Webhook handler for Stripe events
export async function PUT(request: NextRequest) {
  try {
    const sig = request.headers.get('stripe-signature')
    const body = await request.text()
    
    let event: Stripe.Event
    
    try {
      event = stripe.webhooks.constructEvent(body, sig!, process.env.STRIPE_WEBHOOK_SECRET!)
    } catch (err) {
      console.error('Webhook signature verification failed:', err)
      return NextResponse.json({ error: 'Invalid signature' }, { status: 400 })
    }

    // Handle the event
    switch (event.type) {
      case 'checkout.session.completed':
        await handleCheckoutCompleted(event.data.object as Stripe.Checkout.Session)
        break
      
      case 'customer.subscription.updated':
        await handleSubscriptionUpdated(event.data.object as Stripe.Subscription)
        break
      
      case 'customer.subscription.deleted':
        await handleSubscriptionDeleted(event.data.object as Stripe.Subscription)
        break
      
      default:
        console.log(`Unhandled event type ${event.type}`)
    }

    return NextResponse.json({ received: true })

  } catch (error) {
    console.error('Error handling webhook:', error)
    return NextResponse.json({ error: 'Webhook handler failed' }, { status: 500 })
  }
}

async function handleCheckoutCompleted(session: Stripe.Checkout.Session) {
  const userEmail = session.metadata?.userEmail
  const planId = session.metadata?.planId
  
  if (!userEmail || !planId) return

  const subscription = await stripe.subscriptions.retrieve(session.subscription as string)
  const db = getFirestoreDb()
  await db.collection('users').doc(userEmail).update({
    subscriptionTier: planId,
    subscriptionStatus: 'active',
    stripeCustomerId: session.customer as string,
    stripeSubscriptionId: session.subscription as string,
    subscribedAt: new Date().toISOString()
  })
}

async function handleSubscriptionUpdated(subscription: Stripe.Subscription) {
  // Find user by subscription ID and update status
  const db = getFirestoreDb()
  const usersQuery = await db.collection('users')
    .where('stripeSubscriptionId', '==', subscription.id)
    .get()
  
  for (const doc of usersQuery.docs) {
    await doc.ref.update({
      subscriptionStatus: subscription.status === 'active' ? 'active' : 'cancelled',
      updatedAt: new Date().toISOString()
    })
  }
}

async function handleSubscriptionDeleted(subscription: Stripe.Subscription) {
  // Find user by subscription ID and mark as expired
  const db = getFirestoreDb()
  const usersQuery = await db.collection('users')
    .where('stripeSubscriptionId', '==', subscription.id)
    .get()
  
  for (const doc of usersQuery.docs) {
    await doc.ref.update({
      subscriptionStatus: 'expired',
      expiredAt: new Date().toISOString()
    })
  }
}
