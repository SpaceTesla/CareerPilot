"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { TrendingUp, Award } from "lucide-react";
import type { AnalysisOverview } from "@/types/analysis";
import { cn } from "@/lib/utils";

interface ResumeScoreCardProps {
  data: AnalysisOverview | null;
}

export default function ResumeScoreCard({ data }: ResumeScoreCardProps) {
  if (!data) {
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

  const score = data.overall_score;
  const grade = data.grade;
  const percentage = Math.round(score);

  const getGradeColor = (grade: string) => {
    switch (grade) {
      case "A":
        return "bg-green-500/10 text-green-700 border-green-500/20 dark:text-green-400 dark:border-green-500/30";
      case "B":
        return "bg-blue-500/10 text-blue-700 border-blue-500/20 dark:text-blue-400 dark:border-blue-500/30";
      case "C":
        return "bg-yellow-500/10 text-yellow-700 border-yellow-500/20 dark:text-yellow-400 dark:border-yellow-500/30";
      case "D":
        return "bg-orange-500/10 text-orange-700 border-orange-500/20 dark:text-orange-400 dark:border-orange-500/30";
      default:
        return "bg-red-500/10 text-red-700 border-red-500/20 dark:text-red-400 dark:border-red-500/30";
    }
  };

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
    <Card className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-primary/10" />
      <CardHeader className="relative">
        <div className="flex items-center justify-between">
          <CardTitle className="text-2xl font-bold">Overall Resume Score</CardTitle>
          <Badge
            variant="outline"
            className={cn(
              "text-lg font-semibold px-4 py-1.5 border-2",
              getGradeColor(grade)
            )}
          >
            <Award className="mr-2 h-4 w-4" />
            Grade: {grade}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="relative">
        <div className="flex items-center justify-between gap-8">
          {/* Circular Progress */}
          <div className="relative w-32 h-32 flex-shrink-0">
            <svg className="transform -rotate-90 w-32 h-32">
              <circle
                cx="64"
                cy="64"
                r="56"
                stroke="currentColor"
                strokeWidth="8"
                fill="none"
                className="text-muted"
              />
              <circle
                cx="64"
                cy="64"
                r="56"
                stroke="currentColor"
                strokeWidth="8"
                fill="none"
                strokeDasharray={`${(percentage / 100) * 351.86} 351.86`}
                className={getScoreColor(score)}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <span className={cn("text-4xl font-bold block", getScoreColor(score))}>
                  {percentage}
                </span>
                <span className="text-xs text-muted-foreground">/ 100</span>
              </div>
            </div>
          </div>

          {/* Details */}
          <div className="flex-1 space-y-4">
            <div>
              <p className="text-sm text-muted-foreground mb-2">Score Breakdown</p>
              <Progress value={percentage} className="h-3 mb-2" />
              <p className="text-sm font-medium">
                Your resume scores {percentage} out of 100
              </p>
            </div>

            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <TrendingUp className="h-4 w-4" />
              <span>
                {percentage >= 80
                  ? "Excellent! Your resume is well-optimized."
                  : percentage >= 60
                  ? "Good! There's room for improvement."
                  : "Needs work. Check the recommendations below."}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
