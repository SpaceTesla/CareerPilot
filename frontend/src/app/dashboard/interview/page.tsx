"use client";

import { useState, useEffect } from "react";
import InterviewPrepTips from "@/components/analysis/InterviewPrepTips";
import InterviewPractice from "@/components/analysis/InterviewPractice";

export default function InterviewPage() {
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    const storedUserId = localStorage.getItem("cp_user_id");
    if (storedUserId) {
      setUserId(storedUserId);
    }
  }, []);

  return (
    <div className="space-y-6">
      <InterviewPrepTips userId={userId} />
      <InterviewPractice userId={userId} />
    </div>
  );
}
