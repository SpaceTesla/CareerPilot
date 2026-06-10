"use client";

import { useEffect, useState } from "react";
import CalibrationView from "@/components/calibration/CalibrationView";
import { Sliders } from "lucide-react";

export default function CalibrationPage() {
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
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <Sliders className="h-8 w-8 text-primary" />
          Intelligence Calibration
        </h1>
        <p className="text-muted-foreground">
          Analyze peer cohort benchmarks, verify algorithmic accuracy benchmarks, and audit machine learning promotions.
        </p>
      </div>
      <CalibrationView userId={userId} />
    </div>
  );
}
