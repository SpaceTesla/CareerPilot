"use client";

import {
  useState,
  useCallback,
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
} from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { Upload, FileText, AlertCircle, CheckCircle2 } from "lucide-react";
import { apiFormRequest, apiRequest } from "@/lib/api";
import { clearCache, setCachedData } from "@/lib/query-persister";
import { toast } from "sonner";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [isProcessingJob, setIsProcessingJob] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatusMessage, setUploadStatusMessage] = useState("Preparing upload...");
  const router = useRouter();
  const queryClient = useQueryClient();

  type ResumeJobStatus = {
    job_id: string;
    status: "queued" | "processing" | "completed" | "failed";
    progress: number;
    message: string | null;
    error: string | null;
    user_id?: string;
    profile_id?: string;
    session_id?: string;
    resume_session_id?: string;
  };

  const pollResumeJob = async (jobId: string) => {
    const maxAttempts = 240;
    const pollIntervalMs = 1500;

    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      const status = await apiRequest<ResumeJobStatus>(`/resume/jobs/${jobId}`);

      setUploadProgress(Math.max(0, Math.min(100, status.progress ?? 0)));
      setUploadStatusMessage(status.message || "Processing resume...");

      if (status.status === "completed") {
        return status;
      }

      if (status.status === "failed") {
        throw new Error(status.error || "Resume processing failed");
      }

      await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
    }

    throw new Error("Resume processing timed out. Please try again.");
  };

  // Prefetch and persist recommendations data for smoother UX
  const prefetchRecommendations = async (userId: string) => {
    // Clear old cache for fresh data on new resume upload
    clearCache();
    
    // Helper to fetch, cache in React Query, and persist to localStorage
    const fetchAndPersist = async <T,>(queryKey: unknown[], endpoint: string) => {
      try {
        const data = await apiRequest<T>(endpoint);
        // Cache in React Query
        queryClient.setQueryData(queryKey, data);
        // Persist to localStorage
        setCachedData(queryKey, data);
        return data;
      } catch {
        // Silently fail - prefetch is optional
        return null;
      }
    };

    // Prefetch in parallel - these will be cached for when user visits those pages
    const prefetchPromises = [
      fetchAndPersist(
        ["analysis", "overview", userId],
        `/analysis/overview?user_id=${userId}`
      ),
      fetchAndPersist(
        ["jobs", "recommendations", userId, 10],
        `/jobs/recommendations?user_id=${userId}&limit=10`
      ),
      fetchAndPersist(
        ["analysis", "career-path", userId],
        `/analysis/career-path?user_id=${userId}`
      ),
      fetchAndPersist(
        ["analysis", "ats-score", userId],
        `/analysis/ats-score?user_id=${userId}`
      ),
      fetchAndPersist(
        ["interview", "prep", userId, undefined],
        `/interview/prep?user_id=${userId}`
      ),
      fetchAndPersist(
        ["interview", "questions", "category", userId, undefined],
        `/interview/questions-by-category?user_id=${userId}`
      ),
    ];

    // Run in background
    Promise.allSettled(prefetchPromises).catch(() => {
      // Silently fail - these are just prefetches for UX improvement
    });
  };

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      const queuedJob = await apiFormRequest<{
        job_id: string;
        status: string;
        progress: number;
        message: string;
      }>(`/resume/upload/async?enrich=true`, formData);

      setIsProcessingJob(true);
      setUploadProgress(Math.max(queuedJob.progress ?? 5, 5));
      setUploadStatusMessage(queuedJob.message || "Resume queued for processing");

      return pollResumeJob(queuedJob.job_id);
    },
    onSuccess: (data: ResumeJobStatus) => {
      try {
        if (data.user_id) {
          localStorage.setItem("cp_user_id", String(data.user_id));
        }
        if (data.session_id) {
          localStorage.setItem("cp_session_id", String(data.session_id));
        }
        if (data.profile_id) {
          localStorage.setItem("cp_profile_id", String(data.profile_id));
        }
        if (data.resume_session_id) {
          localStorage.setItem("cp_resume_session_id", String(data.resume_session_id));
        }
      } catch {
        // no-op if storage fails
      }

      toast.success("Resume uploaded successfully!");

      if (data.user_id) {
        prefetchRecommendations(data.user_id);
      }

      router.push("/dashboard/overview");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to upload resume");
    },
    onSettled: () => {
      setIsProcessingJob(false);
    },
  });

  const handleDrag = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (validateFile(droppedFile)) {
        setFile(droppedFile);
      }
    }
  }, []);

  const validateFile = (selectedFile: File): boolean => {
    const allowedTypes = ["application/pdf", "text/markdown", "text/plain"];
    const allowedExtensions = [".pdf", ".md", ".txt"];
    const fileExtension = selectedFile.name
      .substring(selectedFile.name.lastIndexOf("."))
      .toLowerCase();

    if (
      !allowedTypes.includes(selectedFile.type) &&
      !allowedExtensions.includes(fileExtension)
    ) {
      toast.error("Please upload a PDF, Markdown, or Text file");
      return false;
    }
    return true;
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && validateFile(selectedFile)) {
      setFile(selectedFile);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) {
      toast.error("Please select a file");
      return;
    }
    uploadMutation.mutate(file);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-muted/20 flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="text-center space-y-2">
          <div className="mx-auto w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-4">
            <Upload className="w-8 h-8 text-primary" />
          </div>
          <CardTitle className="text-3xl font-bold">CareerPilot</CardTitle>
          <CardDescription className="text-base">
            Upload your resume to get started with AI-powered career guidance
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                dragActive
                  ? "border-primary bg-primary/5"
                  : "border-muted-foreground/25 hover:border-primary/50"
              }`}
            >
              <input
                type="file"
                id="resume"
                accept=".pdf,.md,.txt"
                onChange={handleFileChange}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                required
              />
              <div className="space-y-4">
                {file ? (
                  <>
                    <CheckCircle2 className="mx-auto w-12 h-12 text-green-500" />
                    <div>
                      <p className="font-medium text-sm">{file.name}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {(file.size / 1024).toFixed(2)} KB
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setFile(null)}
                    >
                      Change File
                    </Button>
                  </>
                ) : (
                  <>
                    <FileText className="mx-auto w-12 h-12 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">
                        Drag and drop your resume here
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        or click to browse
                      </p>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Supported: PDF, Markdown (.md), Text (.txt)
                    </p>
                  </>
                )}
              </div>
            </div>

            {uploadMutation.isError && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {uploadMutation.error instanceof Error
                    ? uploadMutation.error.message
                    : "An error occurred"}
                </AlertDescription>
              </Alert>
            )}

            {(uploadMutation.isPending || isProcessingJob) && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{uploadStatusMessage}</span>
                  <span className="text-muted-foreground">{uploadProgress}%</span>
                </div>
                <Progress value={uploadProgress} className="h-2" />
              </div>
            )}

            <Button
              type="submit"
              disabled={!file || uploadMutation.isPending || isProcessingJob}
              className="w-full"
              size="lg"
            >
              {uploadMutation.isPending || isProcessingJob ? (
                <>
                  <Upload className="mr-2 h-4 w-4 animate-pulse" />
                  Processing Resume...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload & Process Resume
                </>
              )}
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-xs text-muted-foreground">
              Your resume will be processed and analyzed to provide personalized
              career guidance
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
