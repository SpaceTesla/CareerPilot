"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      // Validate file type
      const allowedTypes = ["application/pdf", "text/markdown", "text/plain"];
      if (!allowedTypes.includes(selectedFile.type)) {
        setError("Please upload a PDF or Markdown file");
        return;
      }
      setFile(selectedFile);
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        "http://localhost:8000/resume/upload?enrich=true",
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error("Failed to upload resume");
      }

      const data = await response.json();
      console.log("Resume processed:", data);

      // Persist identifiers for future chat sessions
      try {
        const userId =
          (data && (data.user_id ?? data.userId ?? data.id)) ?? null;
        if (userId) {
          localStorage.setItem("cp_user_id", String(userId));
        }

        const sessionId =
          (data && (data.session_id ?? data.sessionId ?? data.conversation_id)) ??
          null;
        if (sessionId) {
          localStorage.setItem("cp_session_id", String(sessionId));
        }
      } catch (_) {
        // no-op if storage fails
      }

      // Redirect to chat page
      router.push("/chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">CareerPilot</h1>
          <p className="text-gray-600">
            Upload your resume to get started with AI-powered career guidance
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label
              htmlFor="resume"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Upload Resume
            </label>
            <div className="relative">
              <input
                type="file"
                id="resume"
                accept=".pdf,.md,.txt"
                onChange={handleFileChange}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                required
              />
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Supported formats: PDF, Markdown (.md), Text (.txt)
            </p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={!file || isUploading}
            className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {isUploading ? "Processing..." : "Upload & Process Resume"}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-xs text-gray-500">
            Your resume will be processed and analyzed to provide personalized
            career guidance
          </p>
        </div>
      </div>
    </div>
  );
}
