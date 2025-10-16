"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";

interface Message {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
  actionsTaken?: string[];
  sources?: string[];
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize user_id from localStorage and a session_id
  useEffect(() => {
    try {
      const storedUserId = localStorage.getItem("cp_user_id");
      if (storedUserId) setUserId(storedUserId);
    } catch (_) {
      // ignore
    }
    // generate or reuse a session id per tab
    try {
      const existing = sessionStorage.getItem("cp_session_id");
      if (existing) {
        setSessionId(existing);
      } else {
        const newId = crypto.randomUUID
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random()}`;
        sessionStorage.setItem("cp_session_id", newId);
        setSessionId(newId);
      }
    } catch (_) {
      setSessionId(`${Date.now()}-${Math.random()}`);
    }
  }, []);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputMessage,
      isUser: true,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage("");
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch("http://localhost:8000/agent/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userMessage.content,
          user_id: userId,
          session_id: sessionId,
          include_sources: true,
          context: {},
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to get response");
      }

      const data: {
        message: string;
        data?: Record<string, unknown> | null;
        sources?: string[];
        actions_taken?: string[];
        confidence?: number;
        model?: string | null;
        timestamp?: string;
        success?: boolean;
      } = await response.json();

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: data.message ?? "",
        isUser: false,
        timestamp: new Date(),
        actionsTaken: data.actions_taken ?? [],
        sources: data.sources ?? [],
      };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  const handleBackToUpload = () => {
    router.push("/");
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-semibold text-gray-900">
            CareerPilot Chat
          </h1>
          <button
            onClick={handleBackToUpload}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            Upload New Resume
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <div className="bg-blue-50 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <svg
                  className="w-8 h-8 text-blue-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Welcome to CareerPilot!
              </h3>
              <p className="text-gray-600">
                Ask me anything about your career, resume, or job search. I'm
                here to help!
              </p>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${
                message.isUser ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.isUser
                    ? "bg-blue-600 text-white"
                    : "bg-white text-gray-900 border border-gray-200"
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                {!message.isUser &&
                (message.actionsTaken?.length || message.sources?.length) ? (
                  <div className="mt-2 space-y-2 text-xs">
                    {message.actionsTaken &&
                      message.actionsTaken.length > 0 && (
                        <div>
                          <div className="font-semibold text-gray-700">
                            Tool calls
                          </div>
                          <ul className="list-disc ml-4 text-gray-600">
                            {message.actionsTaken.map((action, idx) => (
                              <li key={idx}>{action}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    {message.sources && message.sources.length > 0 && (
                      <div>
                        <div className="font-semibold text-gray-700">
                          Sources
                        </div>
                        <ul className="list-disc ml-4 text-gray-600">
                          {message.sources.map((src, idx) => (
                            <li key={idx}>{src}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : null}
                {isLoading && !message.isUser && !message.content && (
                  <div className="flex space-x-1">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: "0.1s" }}
                    ></div>
                    <div
                      className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: "0.2s" }}
                    ></div>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="px-4 py-2">
          <div className="max-w-4xl mx-auto">
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="bg-white border-t border-gray-200 px-4 py-4">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSendMessage} className="flex space-x-4">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask me anything about your career..."
              className="flex-1 border text-black border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!inputMessage.trim() || isLoading}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? "Sending..." : "Send"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
