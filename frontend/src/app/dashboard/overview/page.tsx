"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { FileQuestion } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Upload } from "lucide-react";
import { useAnalysisOverview } from "@/hooks/queries/useAnalysis";
import MetricCards from "@/components/analysis/MetricCards";
import ResumeScoreCard from "@/components/analysis/ResumeScoreCard";
import StrengthsWeaknesses from "@/components/analysis/StrengthsWeaknesses";
import ATSScoreCard from "@/components/analysis/ATSScoreCard";
import SkillsBreakdownChart from "@/components/analysis/SkillsBreakdownChart";
import SectionScoresRadar from "@/components/analysis/SectionScoresRadar";
import ProgressChart from "@/components/analysis/ProgressChart";
import ResumeComparison from "@/components/analysis/ResumeComparison";
import SectionAnalysis from "@/components/analysis/SectionAnalysis";
import ActionItemsChecklist from "@/components/analysis/ActionItemsChecklist";

export default function OverviewPage() {
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    const storedUserId = localStorage.getItem("cp_user_id");
    if (storedUserId) {
      setUserId(storedUserId);
    }
  }, []);

  const { data: overview, isLoading: overviewLoading } =
    useAnalysisOverview(userId);

  if (!userId) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Card className="w-full max-w-md text-center p-8">
          <FileQuestion className="mx-auto w-16 h-16 text-muted-foreground mb-4" />
          <h2 className="text-2xl font-bold mb-4">No Resume Found</h2>
          <p className="text-muted-foreground mb-6">
            Please upload your resume to view the analysis.
          </p>
          <Button asChild>
            <Link href="/">
              <Upload className="mr-2 h-4 w-4" />
              Upload Resume
            </Link>
          </Button>
        </Card>
      </div>
    );
  }

  if (overviewLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <Skeleton className="h-48 w-full" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Metrics - Matching shadcn dashboard-01 style */}
      <MetricCards overview={overview || null} userId={userId} />

      {/* Main Resume Score Card */}
      <ResumeScoreCard data={overview || null} />

      {/* Two Column Layout - Strengths/Weaknesses and ATS Score */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <StrengthsWeaknesses data={overview || null} />
        <ATSScoreCard userId={userId} />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SkillsBreakdownChart userId={userId} />
        <SectionScoresRadar userId={userId} />
      </div>

      {/* Progress Chart */}
      <ProgressChart userId={userId} />

      {/* Resume Comparison */}
      <ResumeComparison userId={userId} />

      {/* Section Analysis */}
      <SectionAnalysis data={overview || null} />

      {/* Action Items */}
      <ActionItemsChecklist data={overview || null} />
    </div>
  );
}
