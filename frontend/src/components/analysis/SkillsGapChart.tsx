"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useSkillsGap } from "@/hooks/queries/useAnalysis";
import { cn } from "@/lib/utils";

interface SkillsGapChartProps {
  userId: string | null;
}

const commonRoles = [
  "Backend Developer",
  "Frontend Developer",
  "Full-Stack Developer",
  "DevOps Engineer",
  "Data Scientist",
];

export default function SkillsGapChart({ userId }: SkillsGapChartProps) {
  const [targetRole, setTargetRole] = useState<string>("");
  const { data, isLoading, error } = useSkillsGap(
    userId,
    targetRole || undefined
  );

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
          <p className="text-sm text-destructive">Failed to load skills gap analysis</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Skills Gap Analysis</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Role Selection */}
        <div>
          <Label className="mb-2">Target Role</Label>
          <div className="flex flex-wrap gap-2 mb-4">
            {commonRoles.map((role) => (
              <Button
                key={role}
                type="button"
                variant={targetRole === role ? "default" : "outline"}
                size="sm"
                onClick={() => setTargetRole(role)}
              >
                {role}
              </Button>
            ))}
          </div>
          <Input
            type="text"
            value={targetRole}
            onChange={(e) => setTargetRole(e.target.value)}
            placeholder="Or enter a custom role..."
            className="w-full"
          />
        </div>

        {/* Gap Score */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-semibold">Skills Match Score</h3>
            <Badge
              variant="outline"
              className={cn(
                "text-lg font-semibold",
                data.gap_score >= 70
                  ? "text-green-600 border-green-600"
                  : data.gap_score >= 50
                  ? "text-yellow-600 border-yellow-600"
                  : "text-red-600 border-red-600"
              )}
            >
              {data.gap_score.toFixed(1)}%
            </Badge>
          </div>
          <Progress
            value={data.gap_score}
            className={cn(
              "h-3",
              data.gap_score >= 70
                ? "[&>div]:bg-green-600"
                : data.gap_score >= 50
                ? "[&>div]:bg-yellow-600"
                : "[&>div]:bg-red-600"
            )}
          />
        </div>

        {/* Matching Skills */}
        {data.matching_skills && data.matching_skills.length > 0 && (
          <div>
            <h3 className="text-lg font-semibold text-green-700 dark:text-green-400 mb-3">
              Skills You Have
            </h3>
            <div className="flex flex-wrap gap-2">
              {data.matching_skills.map((skill, idx) => (
                <Badge
                  key={idx}
                  variant="outline"
                  className="bg-green-50 text-green-700 border-green-200 dark:bg-green-950/20 dark:text-green-400 dark:border-green-800"
                >
                  {skill}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Missing Required Skills */}
        {data.missing_required && data.missing_required.length > 0 && (
          <div>
            <h3 className="text-lg font-semibold text-red-700 dark:text-red-400 mb-3">
              Missing Required Skills
            </h3>
            <div className="flex flex-wrap gap-2">
              {data.missing_required.map((skill, idx) => (
                <Badge
                  key={idx}
                  variant="destructive"
                >
                  {skill}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Missing Recommended Skills */}
        {data.missing_recommended && data.missing_recommended.length > 0 && (
          <div>
            <h3 className="text-lg font-semibold text-yellow-700 dark:text-yellow-400 mb-3">
              Missing Recommended Skills
            </h3>
            <div className="flex flex-wrap gap-2">
              {data.missing_recommended.slice(0, 10).map((skill, idx) => (
                <Badge
                  key={idx}
                  variant="outline"
                  className="bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-950/20 dark:text-yellow-400 dark:border-yellow-800"
                >
                  {skill}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Recommendations */}
        {data.recommendations && data.recommendations.length > 0 && (
          <div>
            <h3 className="text-lg font-semibold mb-3">Top Recommendations</h3>
            <ul className="space-y-2">
              {data.recommendations.map((rec, idx) => (
                <li
                  key={idx}
                  className="flex items-start text-sm gap-2"
                >
                  <span className="text-primary mt-0.5">→</span>
                  <span>Focus on learning: <strong>{rec}</strong></span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
