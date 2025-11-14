"use client";

import { useState, useEffect } from "react";
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
      <CareerPathTimeline userId={userId} />
      <CourseRecommendations userId={userId} />
    </div>
  );
}
