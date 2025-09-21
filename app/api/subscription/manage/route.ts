import { NextRequest, NextResponse } from 'next/server'
import Stripe from 'stripe'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2023-10-16'
})

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

export async function POST(request: NextRequest) {
  try {
    const { userEmail, planId, action } = await request.json()
    
    if (!userEmail || !planId) {
      return NextResponse.json({ error: 'User email and plan ID required' }, { status: 400 })
    }

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
