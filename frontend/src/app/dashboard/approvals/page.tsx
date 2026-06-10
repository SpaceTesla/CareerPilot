"use client";

import { useEffect, useState } from "react";
import ApprovalsView from "@/components/agent/ApprovalsView";
import { ShieldAlert } from "lucide-react";

export default function ApprovalsPage() {
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
          <ShieldAlert className="h-8 w-8 text-primary" />
          Agent Supervisor & Approvals
        </h1>
        <p className="text-muted-foreground">
          Review agent actions, inspect supervisor routing choices, and manage human-in-the-loop overrides.
        </p>
      </div>
      <ApprovalsView userId={userId} />
    </div>
  );
}
