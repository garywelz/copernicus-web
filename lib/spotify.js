const SPOTIFY_API_URL = "https://api.spotify.com/v1"

// Function to get Spotify access token
async function getAccessToken() {
  const clientId = process.env.SPOTIFY_CLIENT_ID
  const clientSecret = process.env.SPOTIFY_CLIENT_SECRET

  if (!clientId || !clientSecret) {
    throw new Error("Missing Spotify credentials")
  }

  try {
    const response = await fetch("https://accounts.spotify.com/api/token", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Authorization: `Basic ${Buffer.from(`${clientId}:${clientSecret}`).toString("base64")}`,
      },
      body: "grant_type=client_credentials",
      cache: "no-store",
    })

    if (!response.ok) {
      throw new Error(`Failed to get access token: ${response.status} ${response.statusText}`)
    }

    const data = await response.json()
    return data.access_token
  } catch (error) {
    console.error("Error getting Spotify access token:", error)
    throw error
  }
}

// Function to search for a podcast by name
async function searchSpotifyPodcast(query) {
  const token = await getAccessToken()
  const response = await fetch(
    `${SPOTIFY_API_URL}/search?q=${encodeURIComponent(query)}&type=show&market=US`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    }
  )

  if (!response.ok) {
    throw new Error(`Failed to search podcasts: ${response.status} ${response.statusText}`)
  }

  const data = await response.json()
  return data.shows.items
}

// Function to fetch podcast data
async function getSpotifyPodcast(showId) {
  const token = await getAccessToken()
  const response = await fetch(`${SPOTIFY_API_URL}/shows/${showId}?market=US`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch podcast: ${response.status} ${response.statusText}`)
  }

  return response.json()
}

// Function to fetch all podcast episodes
async function getSpotifyEpisodes(showId) {
  const token = await getAccessToken()
  const limit = 50
  let offset = 0
  let allEpisodes = []

  while (true) {
    const response = await fetch(
      `${SPOTIFY_API_URL}/shows/${showId}/episodes?market=US&limit=${limit}&offset=${offset}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        cache: "no-store",
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to fetch episodes: ${response.status} ${response.statusText}`)
    }

    const data = await response.json()
    
    if (!data.items || data.items.length === 0) {
      break
    }

    allEpisodes = [...allEpisodes, ...data.items]
    
    if (data.items.length < limit) {
      break
    }
    
    offset += limit
  }

  return allEpisodes
}

export { getAccessToken, searchSpotifyPodcast, getSpotifyPodcast, getSpotifyEpisodes } 