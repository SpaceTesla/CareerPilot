"use client";

import { useState, useEffect } from "react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import CareerPathTimeline from "@/components/analysis/CareerPathTimeline";
import CourseRecommendations from "@/components/analysis/CourseRecommendations";
import StrategyReviewsView from "@/components/analysis/StrategyReviewsView";
import WeeklyDigestsView from "@/components/analysis/WeeklyDigestsView";
import { Compass, Mail, TrendingUp } from "lucide-react";

export default function CareerPage() {
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    const storedUserId = localStorage.getItem("cp_user_id");
    if (storedUserId) {
      setUserId(storedUserId);
    }
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold tracking-tight">Career Management</h1>
        <p className="text-muted-foreground">
          Track monthly strategic checkpoints, read passive weekly updates, and explore your career path.
        </p>
      </div>

      <Tabs defaultValue="reviews" className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="reviews" className="flex items-center gap-1.5">
            <Compass className="h-4 w-4" />
            Strategy Reviews
          </TabsTrigger>
          <TabsTrigger value="digests" className="flex items-center gap-1.5">
            <Mail className="h-4 w-4" />
            Weekly Digests
          </TabsTrigger>
          <TabsTrigger value="path" className="flex items-center gap-1.5">
            <TrendingUp className="h-4 w-4" />
            Career Path & Courses
          </TabsTrigger>
        </TabsList>

        <TabsContent value="reviews" className="space-y-6">
          <StrategyReviewsView userId={userId} />
        </TabsContent>

        <TabsContent value="digests" className="space-y-6">
          <WeeklyDigestsView userId={userId} />
        </TabsContent>

        <TabsContent value="path" className="space-y-6">
          <CareerPathTimeline userId={userId} />
          <CourseRecommendations userId={userId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

