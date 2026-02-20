/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    unoptimized: true
  },
  // Enable standalone output for Docker/Cloud Run deployment
  output: 'standalone'
}

module.exports = nextConfig

