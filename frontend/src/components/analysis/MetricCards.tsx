"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TrendingUp, TrendingDown, FileText, Target, Code, BarChart3 } from "lucide-react";
import type { AnalysisOverview } from "@/types/analysis";
import { useATSScore } from "@/hooks/queries/useAnalysis";
import { cn } from "@/lib/utils";

interface MetricCardsProps {
  overview: AnalysisOverview | null;
  userId: string | null;
}

export default function MetricCards({ overview, userId }: MetricCardsProps) {
  const { data: atsData } = useATSScore(userId);

  if (!overview) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-4" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-20 mb-1" />
              <Skeleton className="h-4 w-32" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const resumeScore = Math.round(overview.overall_score);
  const atsScore = Math.round(atsData?.ats_score || 0);
  const skillsCount = overview.section_analysis?.skills?.total_skills || 0;
  
  // Calculate growth rate (mock for now, could be based on historical data)
  const growthRate = resumeScore >= 80 ? 12.5 : resumeScore >= 60 ? 4.5 : -2.5;
  const isPositiveGrowth = growthRate > 0;

  const metrics = [
    {
      title: "Resume Score",
      value: resumeScore,
      description: `${resumeScore >= 80 ? "Excellent" : resumeScore >= 60 ? "Good" : "Needs improvement"} resume quality`,
      icon: FileText,
      trend: isPositiveGrowth ? "+12.5%" : "-2.5%",
      trendPositive: isPositiveGrowth,
      subtitle: "Overall resume performance",
    },
    {
      title: "ATS Score",
      value: atsScore,
      description: atsScore >= 70 ? "Well optimized for ATS" : "Needs ATS optimization",
      icon: Target,
      trend: atsScore >= 70 ? "+8.2%" : "-5.1%",
      trendPositive: atsScore >= 70,
      subtitle: "Applicant tracking system",
    },
    {
      title: "Skills Count",
      value: skillsCount,
      description: `${skillsCount} skills identified`,
      icon: Code,
      trend: skillsCount > 20 ? "+15%" : "+5%",
      trendPositive: true,
      subtitle: "Total skills detected",
    },
    {
      title: "Growth Rate",
      value: `${Math.abs(growthRate)}%`,
      description: isPositiveGrowth ? "Steady performance increase" : "Needs attention",
      icon: BarChart3,
      trend: isPositiveGrowth ? `+${growthRate}%` : `${growthRate}%`,
      trendPositive: isPositiveGrowth,
      subtitle: "Performance trend",
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {metrics.map((metric) => {
        const Icon = metric.icon;
        return (
          <Card key={metric.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{metric.title}</CardTitle>
              <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metric.value}</div>
              <p className="text-xs text-muted-foreground mt-1">{metric.subtitle}</p>
              <div className="flex items-center gap-1 mt-2 flex-wrap">
                {metric.trendPositive ? (
                  <TrendingUp className="h-3 w-3 text-green-600 flex-shrink-0" />
                ) : (
                  <TrendingDown className="h-3 w-3 text-red-600 flex-shrink-0" />
                )}
                <span
                  className={cn(
                    "text-xs font-medium whitespace-nowrap",
                    metric.trendPositive ? "text-green-600" : "text-red-600"
                  )}
                >
                  {metric.trend}
                </span>
                <span className="text-xs text-muted-foreground break-words">
                  {metric.trendPositive ? "from last month" : "this month"}
                </span>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

