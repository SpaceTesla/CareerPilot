"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

interface ResumeComparisonProps {
  userId: string | null;
}

export default function ResumeComparison({ userId }: ResumeComparisonProps) {
  const { data: history, isLoading, error } = useQuery({
    queryKey: ["progress", "history", userId],
    queryFn: () => apiRequest(`/progress/history?user_id=${userId}&limit=10`),
    enabled: !!userId,
  });

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

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-destructive text-center py-8">
            Failed to load comparison data
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!history || !history.history || history.history.length < 2) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground text-center py-8">
            Upload at least 2 resume versions to compare them.
          </p>
        </CardContent>
      </Card>
    );
  }

  const versions = history.history;
  const latest = versions[0];
  const previous = versions[1];

  const scoreDiff = latest.overall_score - previous.overall_score;
  const scoreChange = scoreDiff > 0 ? "improved" : scoreDiff < 0 ? "declined" : "unchanged";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Resume Comparison</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Overall Score Comparison */}
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-4 bg-muted rounded-lg">
            <p className="text-sm text-muted-foreground mb-1">Previous Version</p>
            <p className="text-3xl font-bold">{Math.round(previous.overall_score)}</p>
            <Badge variant="outline" className="mt-2">
              {previous.grade}
            </Badge>
          </div>
          <div className="text-center p-4 bg-primary/10 rounded-lg">
            <p className="text-sm text-muted-foreground mb-1">Latest Version</p>
            <p className="text-3xl font-bold">{Math.round(latest.overall_score)}</p>
            <Badge variant="outline" className="mt-2">
              {latest.grade}
            </Badge>
          </div>
        </div>

        {/* Score Change Indicator */}
        <div className="flex items-center justify-center gap-2 p-4 bg-muted rounded-lg">
          {scoreChange === "improved" && (
            <>
              <TrendingUp className="h-5 w-5 text-green-600" />
              <span className="font-semibold text-green-600">
                Improved by {Math.abs(scoreDiff).toFixed(1)} points
              </span>
            </>
          )}
          {scoreChange === "declined" && (
            <>
              <TrendingDown className="h-5 w-5 text-red-600" />
              <span className="font-semibold text-red-600">
                Declined by {Math.abs(scoreDiff).toFixed(1)} points
              </span>
            </>
          )}
          {scoreChange === "unchanged" && (
            <>
              <Minus className="h-5 w-5 text-muted-foreground" />
              <span className="font-semibold text-muted-foreground">
                No change in score
              </span>
            </>
          )}
        </div>

        {/* Section Comparison */}
        {latest.section_scores && previous.section_scores && (
          <div>
            <h3 className="text-lg font-semibold mb-4">Section-by-Section Comparison</h3>
            <div className="space-y-3">
              {Object.keys(latest.section_scores).map((section) => {
                const latestScore = latest.section_scores[section]?.score || 0;
                const previousScore = previous.section_scores[section]?.score || 0;
                const diff = latestScore - previousScore;

                return (
                  <div key={section} className="flex items-center justify-between p-3 bg-muted rounded-lg">
                    <div className="flex-1">
                      <p className="font-medium capitalize">{section}</p>
                      <div className="flex items-center gap-4 mt-1">
                        <span className="text-sm text-muted-foreground">
                          {Math.round(previousScore)} → {Math.round(latestScore)}
                        </span>
                        {diff !== 0 && (
                          <Badge
                            variant={diff > 0 ? "default" : "destructive"}
                            className="text-xs"
                          >
                            {diff > 0 ? "+" : ""}
                            {diff.toFixed(1)}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

