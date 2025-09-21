import './globals.css'
import { SessionProvider } from '@/components/SessionProvider'

export const metadata = {
  title: 'Copernicus AI Podcast',
  description: 'AI-Generated Research Podcasts for Subscribers',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <SessionProvider>
          {children}
        </SessionProvider>
      </body>
    </html>
  )
} 