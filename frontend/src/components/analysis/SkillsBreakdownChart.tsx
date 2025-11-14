"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import type { AnalysisOverview } from "@/types/analysis";

interface SkillsBreakdownChartProps {
  userId: string | null;
}

const COLORS = ["#3b82f6", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981"];

export default function SkillsBreakdownChart({
  userId,
}: SkillsBreakdownChartProps) {
  const { data: overview, isLoading, error } = useQuery<AnalysisOverview>({
    queryKey: ["analysis", "overview", userId],
    queryFn: () => apiRequest(`/analysis/overview?user_id=${userId}`),
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
          <p className="text-sm text-destructive">
            Failed to load skills breakdown
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!overview || !overview.section_analysis?.skills) {
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

  const skillsData = overview.section_analysis.skills;
  const breakdown = skillsData.breakdown || {};

  const chartData = [
    {
      name: "Languages",
      value: breakdown.languages || 0,
      color: COLORS[0],
    },
    {
      name: "Frameworks",
      value: breakdown.frameworks || 0,
      color: COLORS[1],
    },
    {
      name: "Tools",
      value: breakdown.tools || 0,
      color: COLORS[2],
    },
  ].filter((item) => item.value > 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Skills Breakdown</CardTitle>
      </CardHeader>
      <CardContent>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) =>
                  `${name}: ${(percent * 100).toFixed(0)}%`
                }
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            No skills data available
          </div>
        )}
      </CardContent>
    </Card>
  );
}

