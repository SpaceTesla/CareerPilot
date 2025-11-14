"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { ClipboardList } from "lucide-react";
import { useInterviewPrep } from "@/hooks/queries/useInterview";

interface InterviewPrepTipsProps {
  userId: string | null;
}

export default function InterviewPrepTips({
  userId,
}: InterviewPrepTipsProps) {
  const [targetRole, setTargetRole] = useState("");
  const { data, isLoading, error } = useInterviewPrep(userId, targetRole || undefined);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-64" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-destructive">Failed to load interview prep tips</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ClipboardList className="h-5 w-5" />
          Interview Preparation
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Target Role Input */}
        <div>
          <label className="block text-sm font-medium mb-2">
            Target Role (optional)
          </label>
          <Input
            type="text"
            value={targetRole}
            onChange={(e) => setTargetRole(e.target.value)}
            placeholder="e.g., Backend Developer"
            className="w-full"
          />
        </div>

        {/* Tips */}
        {data.tips && (
          <div>
            <h3 className="text-lg font-semibold mb-3">Preparation Tips</h3>
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <pre className="whitespace-pre-wrap text-sm font-sans bg-muted p-4 rounded-lg">
                {data.tips}
              </pre>
            </div>
          </div>
        )}

        {/* Checklist */}
        {data.preparation_checklist && data.preparation_checklist.length > 0 && (
          <div>
            <h3 className="text-lg font-semibold mb-3">Preparation Checklist</h3>
            <div className="space-y-2">
              {data.preparation_checklist.map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-3 p-3 bg-muted rounded-lg"
                >
                  <Checkbox className="mt-1" />
                  <span className="text-sm flex-1">{item}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
