// components/MembershipSystem.tsx
// Membership system with tiered benefits for podcast users

import React, { useState } from 'react';

interface MembershipTier {
  id: string;
  name: string;
  price: number;
  interval: 'month' | 'year';
  features: string[];
  highlighted?: boolean;
  color: string;
  icon: string;
}

interface User {
  id: string;
  email: string;
  membershipTier: string | null;
  memberSince?: string;
  episodesGenerated: number;
  favoriteCategories: string[];
}

const MEMBERSHIP_TIERS: MembershipTier[] = [
  {
    id: 'free',
    name: 'Explorer',
    price: 0,
    interval: 'month',
    icon: '🔬',
    color: 'bg-gray-500',
    features: [
      'Access to all podcast episodes',
      'Basic search and filtering',
      'Episode bookmarking',
      '1 custom episode per month',
      'Standard audio quality'
    ]
  },
  {
    id: 'premium',
    name: 'Researcher',
    price: 9.99,
    interval: 'month',
    icon: '🧪',
    color: 'bg-blue-500',
    highlighted: true,
    features: [
      'Everything in Explorer',
      'Unlimited custom episodes',
      'Priority generation queue',
      'High-quality audio (320kbps)',
      'Episode transcripts',
      'Advanced search with AI',
      'Personal episode library',
      'Early access to new features'
    ]
  },
  {
    id: 'scholar',
    name: 'Scholar',
    price: 19.99,
    interval: 'month',
    icon: '🎓',
    color: 'bg-purple-500',
    features: [
      'Everything in Researcher',
      'Multi-voice episode generation',
      'Custom voice training',
      'Episode collaboration tools',
      'API access for integrations',
      'White-label podcast creation',
      'Priority support',
      'Monthly live Q&A sessions'
    ]
  }
];

const MEMBER_BENEFITS = {
  'content': {
    icon: '📚',
    title: 'Exclusive Content',
    description: 'Access to member-only episodes and deep-dive series'
  },
  'generation': {
    icon: '🎙️',
    title: 'Custom Episodes',
    description: 'Generate personalized podcast episodes on any scientific topic'
  },
  'quality': {
    icon: '🎵',
    title: 'Premium Quality',
    description: 'High-fidelity audio and professional transcriptions'
  },
  'community': {
    icon: '👥',
    title: 'Member Community',
    description: 'Connect with fellow science enthusiasts and researchers'
  },
  'early': {
    icon: '⚡',
    title: 'Early Access',
    description: 'Be first to try new features and episode formats'
  },
  'support': {
    icon: '🛟',
    title: 'Priority Support',
    description: 'Get help faster with dedicated member support'
  }
};

interface MembershipSystemProps {
  currentUser?: User;
  onUpgrade: (tierId: string) => void;
  onManageSubscription: () => void;
}

export default function MembershipSystem({ 
  currentUser, 
  onUpgrade, 
  onManageSubscription 
}: MembershipSystemProps) {
  const [selectedInterval, setSelectedInterval] = useState<'month' | 'year'>('month');
  const [showBenefits, setShowBenefits] = useState(false);

  const currentTier = MEMBERSHIP_TIERS.find(tier => tier.id === currentUser?.membershipTier) || MEMBERSHIP_TIERS[0];

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">Join the Copernicus AI Community</h1>
        <p className="text-xl text-gray-600 max-w-3xl mx-auto">
          Unlock premium features, generate unlimited custom episodes, and connect with fellow science enthusiasts
        </p>
      </div>

      {/* Current Member Status */}
      {currentUser && (
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-6 mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 ${currentTier.color} rounded-full flex items-center justify-center text-white text-2xl`}>
                {currentTier.icon}
              </div>
              <div>
                <h3 className="font-bold text-lg">{currentTier.name} Member</h3>
                <p className="text-gray-600">
                  {currentUser.memberSince && `Member since ${new Date(currentUser.memberSince).toLocaleDateString()}`}
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-600">Episodes Generated</p>
              <p className="text-2xl font-bold">{currentUser.episodesGenerated}</p>
            </div>
          </div>
          
          {currentUser.membershipTier !== 'free' && (
            <div className="mt-4 flex gap-3">
              <button
                onClick={onManageSubscription}
                className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Manage Subscription
              </button>
            </div>
          )}
        </div>
      )}

      {/* Billing Toggle */}
      <div className="flex justify-center mb-8">
        <div className="bg-gray-100 p-1 rounded-lg">
          <button
            onClick={() => setSelectedInterval('month')}
            className={`px-6 py-2 rounded-md transition-colors ${
              selectedInterval === 'month' 
                ? 'bg-white shadow-sm text-blue-600' 
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Monthly
          </button>
          <button
            onClick={() => setSelectedInterval('year')}
            className={`px-6 py-2 rounded-md transition-colors ${
              selectedInterval === 'year' 
                ? 'bg-white shadow-sm text-blue-600' 
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Yearly
            <span className="ml-2 bg-green-100 text-green-800 px-2 py-0.5 rounded-full text-xs">
              Save 20%
            </span>
          </button>
        </div>
      </div>

      {/* Membership Tiers */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
        {MEMBERSHIP_TIERS.map((tier) => {
          const yearlyPrice = tier.price * 12 * 0.8; // 20% discount
          const displayPrice = selectedInterval === 'year' ? yearlyPrice : tier.price;
          const isCurrentTier = currentUser?.membershipTier === tier.id;
          
          return (
            <div
              key={tier.id}
              className={`relative bg-white rounded-lg border-2 p-6 ${
                tier.highlighted 
                  ? 'border-blue-500 shadow-lg transform scale-105' 
                  : 'border-gray-200'
              } ${isCurrentTier ? 'ring-2 ring-green-500' : ''}`}
            >
              {tier.highlighted && (
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <span className="bg-blue-500 text-white px-4 py-1 rounded-full text-sm font-medium">
                    Most Popular
                  </span>
                </div>
              )}
              
              {isCurrentTier && (
                <div className="absolute -top-3 right-4">
                  <span className="bg-green-500 text-white px-3 py-1 rounded-full text-sm font-medium">
                    Current Plan
                  </span>
                </div>
              )}

              <div className="text-center mb-6">
                <div className={`w-16 h-16 ${tier.color} rounded-full flex items-center justify-center text-white text-3xl mx-auto mb-4`}>
                  {tier.icon}
                </div>
                <h3 className="text-2xl font-bold mb-2">{tier.name}</h3>
                <div className="text-4xl font-bold mb-1">
                  {tier.price === 0 ? 'Free' : `$${displayPrice.toFixed(2)}`}
                </div>
                {tier.price > 0 && (
                  <p className="text-gray-600">
                    per {selectedInterval}
                    {selectedInterval === 'year' && (
                      <span className="block text-sm text-green-600">
                        Save ${(tier.price * 12 - yearlyPrice).toFixed(2)}/year
                      </span>
                    )}
                  </p>
                )}
              </div>

              <ul className="space-y-3 mb-8">
                {tier.features.map((feature, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <span className="text-green-500 mt-0.5">✓</span>
                    <span className="text-sm">{feature}</span>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => onUpgrade(tier.id)}
                disabled={isCurrentTier}
                className={`w-full py-3 rounded-lg font-medium transition-colors ${
                  isCurrentTier
                    ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
                    : tier.highlighted
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-800 text-white hover:bg-gray-900'
                }`}
              >
                {isCurrentTier ? 'Current Plan' : tier.price === 0 ? 'Get Started' : 'Upgrade Now'}
              </button>
            </div>
          );
        })}
      </div>

      {/* Member Benefits */}
      <div className="bg-gray-50 rounded-lg p-8">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold mb-4">Member Benefits</h2>
          <p className="text-gray-600">
            Discover what makes the Copernicus AI community special
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Object.entries(MEMBER_BENEFITS).map(([key, benefit]) => (
            <div key={key} className="bg-white rounded-lg p-6 text-center">
              <div className="text-4xl mb-4">{benefit.icon}</div>
              <h3 className="font-bold text-lg mb-2">{benefit.title}</h3>
              <p className="text-gray-600 text-sm">{benefit.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* FAQ Section */}
      <div className="mt-12">
        <h2 className="text-3xl font-bold text-center mb-8">Frequently Asked Questions</h2>
        <div className="max-w-3xl mx-auto space-y-6">
          <div className="bg-white rounded-lg p-6 border">
            <h3 className="font-bold mb-2">Can I cancel my subscription anytime?</h3>
            <p className="text-gray-600">
              Yes, you can cancel your subscription at any time. You'll continue to have access to premium features until the end of your billing period.
            </p>
          </div>
          
          <div className="bg-white rounded-lg p-6 border">
            <h3 className="font-bold mb-2">How does custom episode generation work?</h3>
            <p className="text-gray-600">
              Simply describe the topic you want to explore, choose your preferences, and our AI will generate a complete podcast episode with audio, transcript, and thumbnail within minutes.
            </p>
          </div>
          
          <div className="bg-white rounded-lg p-6 border">
            <h3 className="font-bold mb-2">What's included in the API access?</h3>
            <p className="text-gray-600">
              Scholar members get access to our REST API for integrating podcast generation into their own applications, with generous rate limits and comprehensive documentation.
            </p>
          </div>
          
          <div className="bg-white rounded-lg p-6 border">
            <h3 className="font-bold mb-2">Do you offer educational discounts?</h3>
            <p className="text-gray-600">
              Yes! Students and educators can get 50% off any paid plan. Contact us with your institutional email for verification.
            </p>
          </div>
        </div>
      </div>

      {/* Call to Action */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg p-8 mt-12 text-center">
        <h2 className="text-3xl font-bold mb-4">Ready to Explore Science with AI?</h2>
        <p className="text-xl mb-6">
          Join thousands of researchers, students, and science enthusiasts who are already using Copernicus AI
        </p>
        <button
          onClick={() => onUpgrade('premium')}
          className="bg-white text-blue-600 px-8 py-3 rounded-lg font-bold hover:bg-gray-100 transition-colors"
        >
          Start Your Free Trial
        </button>
        <p className="text-sm mt-4 text-blue-100">
          No credit card required • Cancel anytime • 14-day free trial
        </p>
      </div>
    </div>
  );
} 