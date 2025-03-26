import './globals.css'

export const metadata = {
  title: 'Copernicus AI Podcast',
  description: 'Keeping Current With Engaging AI Podcasts',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
} 