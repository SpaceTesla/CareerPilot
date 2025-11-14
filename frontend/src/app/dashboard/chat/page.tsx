"use client";

import { useState, useEffect } from "react";
import { FadeIn } from "@/components/animations/fade-in";
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
    <div className="max-w-4xl mx-auto">
      <FadeIn>
        <ChatWidget userId={userId} />
      </FadeIn>
    </div>
  );
}

