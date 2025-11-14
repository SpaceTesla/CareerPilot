"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Info } from "lucide-react";
import { useATSScore } from "@/hooks/queries/useAnalysis";
import { cn } from "@/lib/utils";

interface ATSScoreCardProps {
  userId: string | null;
}

export default function ATSScoreCard({ userId }: ATSScoreCardProps) {
  const { data, isLoading, error } = useATSScore(userId);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-32 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-destructive">Failed to load ATS score</p>
        </CardContent>
      </Card>
    );
  }

  const score = data.ats_score;
  const percentage = Math.round(score);

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-600 dark:text-green-400";
    if (score >= 60) return "text-blue-600 dark:text-blue-400";
    if (score >= 40) return "text-yellow-600 dark:text-yellow-400";
    return "text-red-600 dark:text-red-400";
  };

  const getProgressColor = (score: number) => {
    if (score >= 80) return "bg-green-600";
    if (score >= 60) return "bg-blue-600";
    if (score >= 40) return "bg-yellow-600";
    return "bg-red-600";
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>ATS Optimization Score</CardTitle>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <Info className="h-4 w-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent>
                <p className="max-w-xs">
                  ATS (Applicant Tracking System) score measures how well your resume is optimized for automated screening systems.
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Score Display */}
          <div className="flex items-center gap-6">
            <div className="relative w-24 h-24 flex-shrink-0">
              <svg className="transform -rotate-90 w-24 h-24">
                <circle
                  cx="48"
                  cy="48"
                  r="42"
                  stroke="currentColor"
                  strokeWidth="6"
                  fill="none"
                  className="text-muted"
                />
                <circle
                  cx="48"
                  cy="48"
                  r="42"
                  stroke="currentColor"
                  strokeWidth="6"
                  fill="none"
                  strokeDasharray={`${(percentage / 100) * 263.89} 263.89`}
                  className={getScoreColor(score)}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className={cn("text-2xl font-bold", getScoreColor(score))}>
                  {percentage}
                </span>
              </div>
            </div>
            <div className="flex-1">
              <p className="text-sm text-muted-foreground mb-2">
                Your resume is {percentage >= 70 ? "well" : "moderately"}{" "}
                optimized for ATS systems
              </p>
              {percentage < 70 && (
                <p className="text-xs text-yellow-600 dark:text-yellow-400">
                  Consider improving keyword usage and formatting
                </p>
              )}
            </div>
          </div>

          <Progress value={percentage} className="h-2" />

          {/* Keyword Suggestions */}
          {data.keyword_suggestions && data.keyword_suggestions.length > 0 && (
            <div>
              <h3 className="text-sm font-medium mb-2">Keyword Suggestions</h3>
              <div className="flex flex-wrap gap-2">
                {data.keyword_suggestions.slice(0, 5).map((keyword, idx) => (
                  <Badge key={idx} variant="secondary" className="text-xs">
                    {keyword}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Optimization Tips */}
          {data.optimization_tips && data.optimization_tips.length > 0 && (
            <div>
              <h3 className="text-sm font-medium mb-2">Optimization Tips</h3>
              <ul className="space-y-1">
                {data.optimization_tips.slice(0, 3).map((tip, idx) => (
                  <li key={idx} className="text-sm text-muted-foreground flex items-start gap-2">
                    <span className="text-primary mt-0.5">•</span>
                    {tip}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
