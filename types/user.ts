export interface User {
  id: string
  email: string
  displayName?: string
  bio?: string
  website?: string
  location?: string
  avatar?: string
  membershipTier: 'free' | 'premium' | 'scholar'
  memberSince?: string
  episodesGenerated: number
  favoriteCategories: string[]
  researchInterests: string[]
  isVerified: boolean
  createdAt: string
  updatedAt: string
  settings: UserSettings
}

export interface UserSettings {
  profileVisibility: 'public' | 'private' | 'friends'
  podcastVisibility: 'public' | 'unlisted' | 'private'
  emailNotifications: boolean
  podcastCompletionAlerts: boolean
  marketingEmails: boolean
  language: string
  timezone: string
}

export interface Podcast {
  id: string
  userId: string
  title: string
  description: string
  topic: string
  category: string
  duration: string
  expertiseLevel: 'beginner' | 'intermediate' | 'expert'
  formatType: 'interview' | 'monologue' | 'discussion'
  status: 'draft' | 'processing' | 'completed' | 'published' | 'private'
  visibility: 'public' | 'unlisted' | 'private'
  
  // Media URLs
  audioUrl?: string
  thumbnailUrl?: string
  transcriptUrl?: string
  descriptionUrl?: string
  
  // Metadata
  canonicalFilename?: string
  episodeNumber?: number
  views: number
  likes: number
  shares: number
  downloads: number
  
  // Content
  script?: string
  citations?: Citation[]
  hashtags?: string[]
  speakers?: string[]
  
  // Timestamps
  createdAt: string
  updatedAt: string
  publishedAt?: string
  
  // Generation info
  generationJobId?: string
  ttsProvider?: string
  contentProvider?: string
  generationTime?: number
  
  // Research
  hasResearchPaper?: boolean
  paperTitle?: string
  researchSources?: ResearchSource[]
}

export interface Playlist {
  id: string
  userId: string
  title: string
  description?: string
  visibility: 'public' | 'unlisted' | 'private'
  episodes: string[] // Podcast IDs
  episodeCount: number
  thumbnailUrl?: string
  createdAt: string
  updatedAt: string
}

export interface Citation {
  id: string
  type: 'paper' | 'article' | 'book' | 'website'
  title: string
  authors?: string[]
  journal?: string
  year?: number
  doi?: string
  url?: string
  abstract?: string
}

export interface ResearchSource {
  id: string
  type: 'paper' | 'article' | 'preprint' | 'news'
  title: string
  authors?: string[]
  journal?: string
  year?: number
  doi?: string
  url?: string
  abstract?: string
  relevanceScore?: number
  source: 'pubmed' | 'arxiv' | 'zenodo' | 'user_provided'
}

export interface PodcastGenerationRequest {
  topic: string
  category: string
  duration: string
  expertiseLevel: 'beginner' | 'intermediate' | 'expert'
  formatType: 'interview' | 'monologue' | 'discussion'
  speakers: string
  additionalNotes?: string
  sourceLinks?: string[]
  researchDepth?: 'basic' | 'comprehensive' | 'exhaustive'
  includeCitations?: boolean
  includeHashtags?: boolean
  visibility: 'public' | 'unlisted' | 'private'
  saveAsDraft?: boolean
}

export interface PodcastGenerationJob {
  id: string
  userId: string
  request: PodcastGenerationRequest
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  currentStage?: string
  message?: string
  error?: string
  result?: Podcast
  createdAt: string
  updatedAt: string
  estimatedCompletion?: string
}

export interface UserStats {
  totalEpisodes: number
  totalViews: number
  totalLikes: number
  totalShares: number
  totalDownloads: number
  averageEpisodeLength: number
  mostPopularCategory: string
  generationSuccessRate: number
  monthlyEpisodes: number[]
  monthlyViews: number[]
}

export interface Notification {
  id: string
  userId: string
  type: 'podcast_complete' | 'podcast_published' | 'new_follower' | 'like' | 'comment' | 'system'
  title: string
  message: string
  data?: any
  isRead: boolean
  createdAt: string
}

export interface Comment {
  id: string
  podcastId: string
  userId: string
  userDisplayName: string
  userAvatar?: string
  content: string
  likes: number
  replies: Comment[]
  createdAt: string
  updatedAt: string
}

export interface Subscription {
  id: string
  userId: string
  tier: 'free' | 'premium' | 'scholar'
  status: 'active' | 'cancelled' | 'expired' | 'past_due'
  currentPeriodStart: string
  currentPeriodEnd: string
  cancelAtPeriodEnd: boolean
  stripeCustomerId?: string
  stripeSubscriptionId?: string
  createdAt: string
  updatedAt: string
}
