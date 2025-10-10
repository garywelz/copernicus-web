# Copernicus Web

A Next.js website that displays podcast episodes from Spotify with category filtering and a modern UI.

## Features

- Spotify API integration for podcast episodes
- Category-based filtering
- Responsive design
- Modern UI with Tailwind CSS
- Server-side rendering with Next.js

## Setup

1. Clone the repository:
```bash
git clone https://github.com/your-username/copernicus-web.git
cd copernicus-web
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env.local` file with your Spotify credentials:
```
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_SHOW_ID=your_show_id
```

4. Run the development server:
```bash
npm run dev
```

5. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Environment Variables

- `SPOTIFY_CLIENT_ID`: Your Spotify API client ID
- `SPOTIFY_CLIENT_SECRET`: Your Spotify API client secret
- `SPOTIFY_SHOW_ID`: The ID of your Spotify podcast show

## Tech Stack

- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- Spotify Web API # Trigger Vercel deployment
