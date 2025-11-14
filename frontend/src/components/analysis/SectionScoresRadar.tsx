"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { useAnalysisOverview } from "@/hooks/queries/useAnalysis";

interface SectionScoresRadarProps {
  userId: string | null;
}

export default function SectionScoresRadar({
  userId,
}: SectionScoresRadarProps) {
  const { data, isLoading } = useAnalysisOverview(userId);

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

  if (!data || !data.section_analysis) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground text-center py-8">
            No section data available
          </p>
        </CardContent>
      </Card>
    );
  }

  const sections = Object.entries(data.section_analysis).map(
    ([name, sectionData]) => {
      const score = sectionData.score;
      const maxScore = sectionData.max_score;
      const percentage = maxScore
        ? Math.round((score / maxScore) * 100)
        : Math.round(score * 100);

      return {
        section: name.charAt(0).toUpperCase() + name.slice(1),
        score: percentage,
        fullMark: 100,
      };
    }
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Section Scores Radar</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <RadarChart data={sections}>
            <PolarGrid />
            <PolarAngleAxis dataKey="section" />
            <PolarRadiusAxis angle={90} domain={[0, 100]} />
            <Radar
              name="Score"
              dataKey="score"
              stroke="#3b82f6"
              fill="#3b82f6"
              fillOpacity={0.6}
            />
            <Tooltip />
          </RadarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

