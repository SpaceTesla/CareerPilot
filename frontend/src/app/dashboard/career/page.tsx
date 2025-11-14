"use client";

import { useState, useEffect } from "react";
import { FadeIn } from "@/components/animations/fade-in";
import CareerPathTimeline from "@/components/analysis/CareerPathTimeline";
import CourseRecommendations from "@/components/analysis/CourseRecommendations";

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
      <FadeIn>
        <CareerPathTimeline userId={userId} />
      </FadeIn>
      <FadeIn delay={0.1}>
        <CourseRecommendations userId={userId} />
      </FadeIn>
    </div>
  );
}

