"use client";

import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { MessageCircle, Send, Bot, User } from "lucide-react";
import { apiRequest } from "@/lib/api";
import { API_BASE } from "@/lib/config";
import { toast } from "sonner";

interface Message {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
  actionsTaken?: string[];
  sources?: string[];
}

interface ChatWidgetProps {
  userId: string | null;
}

export default function ChatWidget({ userId }: ChatWidgetProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;
    if (!userId) {
      toast.error("User ID is required");
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputMessage,
      isUser: true,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage("");
    setIsLoading(true);

    try {
      const sessionId = localStorage.getItem("cp_session_id");

      const data = await fetch(`${API_BASE}/agent/chat`, {
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
      }).then((res) => {
        if (!res.ok) throw new Error("Failed to get response");
        return res.json();
      });

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
      toast.error(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="flex flex-col h-[600px]">
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2">
          <MessageCircle className="h-5 w-5" />
          Chat Assistant
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col p-0">
        {/* Messages */}
        <ScrollArea className="flex-1 px-4 py-6">
          <div className="space-y-4">
            {messages.length === 0 && (
              <div className="text-center py-12">
                <div className="mx-auto w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-4">
                  <Bot className="w-8 h-8 text-primary" />
                </div>
                <h3 className="text-lg font-semibold mb-2">
                  Start a conversation
                </h3>
                <p className="text-sm text-muted-foreground">
                  Ask me anything about your career, resume, or job search.
                </p>
              </div>
            )}

            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${
                  message.isUser ? "justify-end" : "justify-start"
                }`}
              >
                {!message.isUser && (
                  <Avatar className="h-8 w-8">
                    <AvatarFallback>
                      <Bot className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                )}
                <div
                  className={`flex flex-col gap-1 max-w-[80%] ${
                    message.isUser ? "items-end" : "items-start"
                  }`}
                >
                  <div
                    className={`rounded-lg px-4 py-2 ${
                      message.isUser
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">
                      {message.content}
                    </p>
                  </div>
                  {!message.isUser &&
                    message.actionsTaken &&
                    message.actionsTaken.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {message.actionsTaken.map((action, idx) => (
                          <Badge key={idx} variant="secondary" className="text-xs">
                            {action}
                          </Badge>
                        ))}
                      </div>
                    )}
                </div>
                {message.isUser && (
                  <Avatar className="h-8 w-8">
                    <AvatarFallback>
                      <User className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        {/* Input */}
        <div className="border-t px-4 py-4">
          <form onSubmit={handleSendMessage} className="flex gap-2">
            <Input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask me anything..."
              disabled={isLoading || !userId}
              className="flex-1"
            />
            <Button
              type="submit"
              disabled={!inputMessage.trim() || isLoading || !userId}
              size="icon"
            >
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </div>
      </CardContent>
    </Card>
  );
}
