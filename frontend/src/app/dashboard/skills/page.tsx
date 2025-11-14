"use client";

import { useState, useEffect } from "react";
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
      <SkillsGapChart userId={userId} />
      <ATSKeywordHighlight userId={userId} />
    </div>
  );
}
