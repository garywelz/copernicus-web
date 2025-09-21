import { redirect } from 'next/navigation'

export default function Home() {
  // Redirect to signup for new users
  redirect('/auth/signup')
}

