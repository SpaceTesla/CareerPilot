"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { Upload, FileText, AlertCircle, CheckCircle2 } from "lucide-react";
import { apiFormRequest } from "@/lib/api";
import { toast } from "sonner";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const router = useRouter();

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return apiFormRequest<{
        user_id: string;
        profile_id: string;
        session_id: string;
        data: unknown;
      }>(`/resume/upload?enrich=true`, formData);
    },
    onSuccess: (data) => {
      // Persist identifiers
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
      } catch (_) {
        // no-op if storage fails
      }

      toast.success("Resume uploaded successfully!");
      
      // Redirect to analysis dashboard
      if (data.profile_id) {
        router.push(`/analysis?profile_id=${data.profile_id}`);
      } else {
        router.push("/analysis");
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to upload resume");
    },
  });

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);

      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        const droppedFile = e.dataTransfer.files[0];
        if (validateFile(droppedFile)) {
          setFile(droppedFile);
        }
      }
    },
    []
  );

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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && validateFile(selectedFile)) {
      setFile(selectedFile);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
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

            {uploadMutation.isPending && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Processing...</span>
                  <span className="text-muted-foreground">Please wait</span>
                </div>
                <Progress value={undefined} className="h-2" />
              </div>
            )}

            <Button
              type="submit"
              disabled={!file || uploadMutation.isPending}
              className="w-full"
              size="lg"
            >
              {uploadMutation.isPending ? (
                <>
                  <Upload className="mr-2 h-4 w-4 animate-pulse" />
                  Processing...
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
