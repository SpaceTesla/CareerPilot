"use client";

import { useState, useEffect } from "react";
import { FadeIn } from "@/components/animations/fade-in";
import SkillsGapChart from "@/components/analysis/SkillsGapChart";
import ATSKeywordHighlight from "@/components/analysis/ATSKeywordHighlight";

export default function SkillsPage() {
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
        <SkillsGapChart userId={userId} />
      </FadeIn>
      <FadeIn delay={0.1}>
        <ATSKeywordHighlight userId={userId} />
      </FadeIn>
    </div>
  );
}

