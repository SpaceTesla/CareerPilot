"use client";

import { useState, useEffect } from "react";
import ChatWidget from "@/components/analysis/ChatWidget";

export default function ChatPage() {
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    const storedUserId = localStorage.getItem("cp_user_id");
    if (storedUserId) {
      setUserId(storedUserId);
    }
  }, []);

  return (
    <div className="space-y-6">
      <ChatWidget userId={userId} />
    </div>
  );
}
