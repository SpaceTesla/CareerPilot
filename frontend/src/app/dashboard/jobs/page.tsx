"use client";

import { useState, useEffect } from "react";
import JobMatchCard from "@/components/analysis/JobMatchCard";

export default function JobsPage() {
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    const storedUserId = localStorage.getItem("cp_user_id");
    if (storedUserId) {
      setUserId(storedUserId);
    }
  }, []);

  return (
    <div className="space-y-6">
      <JobMatchCard userId={userId} />
    </div>
  );
}
