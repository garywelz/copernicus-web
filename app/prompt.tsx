import React, { useState } from 'react';

interface PromptFormState {
  subject: string;
  duration: string;
  speakers: string;
  difficulty: string;
  additionalNotes: string;
}

const initialFormState: PromptFormState = {
  subject: '',
  duration: '',
  speakers: '',
  difficulty: '',
  additionalNotes: '',
};

export default function PodcastPromptPage() {
  const [form, setForm] = useState<PromptFormState>(initialFormState);
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [links, setLinks] = useState<string[]>(['']);
  const [documents, setDocuments] = useState<File[]>([]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleLinkChange = (idx: number, value: string) => {
    setLinks((prev) => {
      const newLinks = [...prev];
      newLinks[idx] = value;
      return newLinks;
    });
  };

  const addLinkField = () => setLinks((prev) => [...prev, '']);
  const removeLinkField = (idx: number) => setLinks((prev) => prev.filter((_, i) => i !== idx));

  const handleDocumentChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setDocuments(Array.from(e.target.files));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSubmitted(false);
    try {
      // TODO: Replace with API call to backend, including links and documents
      await new Promise((res) => setTimeout(res, 1000));
      setSubmitted(true);
    } catch (err) {
      setError('Failed to submit prompt. Try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold mb-6">Generate a New Podcast Episode</h1>
      <div className="mb-4 text-blue-700 text-sm font-medium bg-blue-50 rounded px-3 py-2 border border-blue-200">
        <span>
          <strong>Note:</strong> We draw from ArXiv, the internet, and any other online sources we can access. You may also provide your own links or upload documents to be covered.
        </span>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4 bg-white rounded shadow p-6">
        <div>
          <label className="block font-medium mb-1">Subject</label>
          <input
            type="text"
            name="subject"
            value={form.subject}
            onChange={handleChange}
            required
            className="w-full border rounded px-3 py-2"
            placeholder="e.g. Quantum Computing"
          />
        </div>
        <div>
          <label className="block font-medium mb-1">Duration (minutes)</label>
          <input
            type="number"
            name="duration"
            value={form.duration}
            onChange={handleChange}
            required
            min="1"
            max="120"
            className="w-full border rounded px-3 py-2"
            placeholder="e.g. 20"
          />
        </div>
        <div>
          <label className="block font-medium mb-1">Speakers</label>
          <input
            type="text"
            name="speakers"
            value={form.speakers}
            onChange={handleChange}
            required
            className="w-full border rounded px-3 py-2"
            placeholder="e.g. Sarah, Antoni, Josh"
          />
        </div>
        <div>
          <label className="block font-medium mb-1">Difficulty</label>
          <select
            name="difficulty"
            value={form.difficulty}
            onChange={handleChange}
            required
            className="w-full border rounded px-3 py-2"
          >
            <option value="">Select...</option>
            <option value="Beginner">Beginner</option>
            <option value="Intermediate">Intermediate</option>
            <option value="Advanced">Advanced</option>
          </select>
        </div>
        <div>
          <label className="block font-medium mb-1">Additional Notes</label>
          <textarea
            name="additionalNotes"
            value={form.additionalNotes}
            onChange={handleChange}
            className="w-full border rounded px-3 py-2"
            placeholder="Special instructions, themes, etc."
            rows={3}
          />
        </div>
        <div>
          <label className="block font-medium mb-1">Links to Sources</label>
          {links.map((link, idx) => (
            <div key={idx} className="flex items-center mb-2">
              <input
                type="url"
                value={link}
                onChange={e => handleLinkChange(idx, e.target.value)}
                className="w-full border rounded px-3 py-2"
                placeholder="https://arxiv.org/abs/1234.5678 or other source"
              />
              {links.length > 1 && (
                <button type="button" onClick={() => removeLinkField(idx)} className="ml-2 text-red-600 font-bold">&times;</button>
              )}
            </div>
          ))}
          <button type="button" onClick={addLinkField} className="text-blue-600 text-sm mt-1">+ Add another link</button>
        </div>
        <div>
          <label className="block font-medium mb-1">Upload Documents (PDF, DOCX, TXT)</label>
          <input
            type="file"
            accept=".pdf,.doc,.docx,.txt"
            multiple
            onChange={handleDocumentChange}
            className="w-full border rounded px-3 py-2"
          />
          {documents.length > 0 && (
            <div className="text-xs text-gray-600 mt-1">
              {documents.map((file, idx) => <div key={idx}>{file.name}</div>)}
            </div>
          )}
        </div>
        <button
          type="submit"
          className="bg-blue-600 text-white px-6 py-2 rounded font-semibold hover:bg-blue-700 disabled:opacity-60"
          disabled={loading}
        >
          {loading ? 'Submitting...' : 'Generate Podcast'}
        </button>
        {error && <div className="text-red-600 mt-2">{error}</div>}
        {submitted && <div className="text-green-600 mt-2">Prompt submitted! Your podcast will be generated soon.</div>}
      </form>
    </div>
  );
}
