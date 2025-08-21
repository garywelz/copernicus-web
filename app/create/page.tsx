'use client';

import { useEffect } from 'react';

export default function CreatePage() {
  useEffect(() => {
    // Redirect to the new Google Cloud Storage form
    // Force cache refresh: 2025-01-20 12:45:00 UTC
    window.location.href = 'https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/form.html';
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center bg-white p-8 rounded-lg shadow-md">
        <h1 className="text-2xl font-bold mb-4 text-gray-900">Redirecting to Podcast Generator...</h1>
        <p className="text-gray-600 mb-4">You will be redirected to the new podcast generation form.</p>
        <a 
          href="https://storage.googleapis.com/regal-scholar-453620-r7-podcast-storage/form.html" 
          className="text-blue-600 hover:underline font-medium"
        >
          Click here if you're not redirected automatically
        </a>
      </div>
    </div>
  );
}
