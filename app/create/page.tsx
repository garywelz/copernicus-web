'use client';

import { useEffect } from 'react';

export default function CreatePage() {
  useEffect(() => {
    // Redirect to the new Google Cloud Storage form
    window.location.href = 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/form.html';
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-4">Redirecting to Podcast Generator...</h1>
        <p className="text-gray-600">If you're not redirected automatically, <a href="https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/form.html" className="text-blue-600 hover:underline">click here</a>.</p>
      </div>
    </div>
  );
}
