"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Upload, FileQuestion } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { FadeIn } from "@/components/animations/fade-in";
import ResumeScoreCard from "@/components/analysis/ResumeScoreCard";
import SectionAnalysis from "@/components/analysis/SectionAnalysis";
import StrengthsWeaknesses from "@/components/analysis/StrengthsWeaknesses";
import ATSScoreCard from "@/components/analysis/ATSScoreCard";
import SkillsBreakdownChart from "@/components/analysis/SkillsBreakdownChart";
import SectionScoresRadar from "@/components/analysis/SectionScoresRadar";
import SkillsGapChart from "@/components/analysis/SkillsGapChart";
import ProgressChart from "@/components/analysis/ProgressChart";
import ATSKeywordHighlight from "@/components/analysis/ATSKeywordHighlight";
import ResumeComparison from "@/components/analysis/ResumeComparison";
import JobMatchCard from "@/components/analysis/JobMatchCard";
import CareerPathTimeline from "@/components/analysis/CareerPathTimeline";
import CourseRecommendations from "@/components/analysis/CourseRecommendations";
import InterviewPrepTips from "@/components/analysis/InterviewPrepTips";
import InterviewPractice from "@/components/analysis/InterviewPractice";
import ActionItemsChecklist from "@/components/analysis/ActionItemsChecklist";
import ChatWidget from "@/components/analysis/ChatWidget";
import ExportButton from "@/components/analysis/ExportButton";
import { useAnalysisOverview } from "@/hooks/queries/useAnalysis";

export default function AnalysisPage() {
  const searchParams = useSearchParams();
  const profileId = searchParams.get("profile_id");
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    const storedUserId = localStorage.getItem("cp_user_id");
    if (storedUserId) {
      setUserId(storedUserId);
    }
  }, []);

  const { data: overview, isLoading: overviewLoading } = useAnalysisOverview(userId);

  if (!userId) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
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

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <h1 className="text-2xl font-bold">Resume Analysis</h1>
            <div className="flex items-center gap-2">
              <ThemeToggle />
              <ExportButton
                analysisData={overview || null}
                profileName={overview ? "Resume" : undefined}
              />
              <Button variant="outline" size="sm" asChild>
                <Link href="/">
                  <Upload className="mr-2 h-4 w-4" />
                  Upload New Resume
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b bg-card">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <Tabs defaultValue="overview" className="w-full">
            <TabsList className="h-auto p-1 bg-transparent">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="skills">Skills</TabsTrigger>
              <TabsTrigger value="jobs">Jobs</TabsTrigger>
              <TabsTrigger value="career">Career</TabsTrigger>
              <TabsTrigger value="interview">Interview</TabsTrigger>
              <TabsTrigger value="chat">Chat</TabsTrigger>
            </TabsList>

            {/* Content */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
              <TabsContent value="overview" className="space-y-6 mt-6">
                {overviewLoading ? (
                  <div className="space-y-6">
                    <Skeleton className="h-48 w-full" />
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <Skeleton className="h-64" />
                      <Skeleton className="h-64" />
                    </div>
                    <Skeleton className="h-96" />
                  </div>
                ) : (
                  <>
                    <FadeIn>
                      <ResumeScoreCard data={overview || null} />
                    </FadeIn>
                    <FadeIn delay={0.1}>
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <StrengthsWeaknesses data={overview || null} />
                        <ATSScoreCard userId={userId} />
                      </div>
                    </FadeIn>
                    <FadeIn delay={0.2}>
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <SkillsBreakdownChart userId={userId} />
                        <SectionScoresRadar userId={userId} />
                      </div>
                    </FadeIn>
                    <FadeIn delay={0.3}>
                      <ProgressChart userId={userId} />
                    </FadeIn>
                    <FadeIn delay={0.35}>
                      <ResumeComparison userId={userId} />
                    </FadeIn>
                    <FadeIn delay={0.4}>
                      <SectionAnalysis data={overview || null} />
                    </FadeIn>
                    <FadeIn delay={0.5}>
                      <ActionItemsChecklist data={overview || null} />
                    </FadeIn>
                  </>
                )}
              </TabsContent>

              <TabsContent value="skills" className="space-y-6 mt-6">
                <SkillsGapChart userId={userId} />
                <ATSKeywordHighlight userId={userId} />
              </TabsContent>

              <TabsContent value="jobs" className="space-y-6 mt-6">
                <JobMatchCard userId={userId} />
              </TabsContent>

              <TabsContent value="career" className="space-y-6 mt-6">
                <CareerPathTimeline userId={userId} />
                <CourseRecommendations userId={userId} />
              </TabsContent>

              <TabsContent value="interview" className="space-y-6 mt-6">
                <InterviewPrepTips userId={userId} />
                <InterviewPractice userId={userId} />
              </TabsContent>

              <TabsContent value="chat" className="mt-6">
                <div className="max-w-4xl mx-auto">
                  <ChatWidget userId={userId} />
                </div>
              </TabsContent>
            </div>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
