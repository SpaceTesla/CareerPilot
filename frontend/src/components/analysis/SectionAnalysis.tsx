"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { AnalysisOverview } from "@/types/analysis";
import { cn } from "@/lib/utils";

interface SectionAnalysisProps {
  data: AnalysisOverview | null;
}

export default function SectionAnalysis({ data }: SectionAnalysisProps) {
  if (!data || !data.section_analysis) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-32" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const sections = Object.entries(data.section_analysis);

  const getScoreColor = (score: number, maxScore?: number) => {
    const percentage = maxScore ? (score / maxScore) * 100 : score * 100;
    if (percentage >= 80) return "text-green-600 dark:text-green-400";
    if (percentage >= 60) return "text-blue-600 dark:text-blue-400";
    if (percentage >= 40) return "text-yellow-600 dark:text-yellow-400";
    return "text-red-600 dark:text-red-400";
  };

  const getProgressColor = (score: number, maxScore?: number) => {
    const percentage = maxScore ? (score / maxScore) * 100 : score * 100;
    if (percentage >= 80) return "bg-green-600";
    if (percentage >= 60) return "bg-blue-600";
    if (percentage >= 40) return "bg-yellow-600";
    return "bg-red-600";
  };

  const formatSectionName = (name: string) => {
    return name.charAt(0).toUpperCase() + name.slice(1);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Section-by-Section Analysis</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sections.map(([sectionName, sectionData]) => {
            const score = sectionData.score;
            const maxScore = sectionData.max_score;
            const percentage = maxScore
              ? Math.round((score / maxScore) * 100)
              : Math.round(score * 100);

            return (
              <Card key={sectionName} className="hover:shadow-md transition-shadow">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-sm">
                      {formatSectionName(sectionName)}
                    </h3>
                    <Badge
                      variant="outline"
                      className={cn(
                        "font-semibold",
                        getScoreColor(score, maxScore)
                      )}
                    >
                      {percentage}%
                    </Badge>
                  </div>
                  <Progress
                    value={percentage}
                    className="h-2 mb-3"
                  />
                  {sectionData.completeness && (
                    <p className="text-xs text-muted-foreground mb-1">
                      Completeness: {sectionData.completeness}
                    </p>
                  )}
                  {sectionData.total_skills !== undefined && (
                    <p className="text-xs text-muted-foreground">
                      Total Skills: {sectionData.total_skills}
                    </p>
                  )}
                  {sectionData.total_positions !== undefined && (
                    <p className="text-xs text-muted-foreground">
                      Positions: {sectionData.total_positions}
                    </p>
                  )}
                  {sectionData.total_projects !== undefined && (
                    <p className="text-xs text-muted-foreground">
                      Projects: {sectionData.total_projects}
                    </p>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
