"use client";

import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  MessageCircle,
  Send,
  Bot,
  User,
  History,
  Plus,
  Trash2,
} from "lucide-react";
import { apiRequest } from "@/lib/api";
import { toast } from "sonner";
import {
  useChatHistory,
  useConversationMessages,
  useDeleteConversation,
  type ChatConversation,
} from "@/hooks/queries/useChat";

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
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch chat history
  const { data: historyData, refetch: refetchHistory } = useChatHistory(userId);
  const { data: conversationData } = useConversationMessages(userId, activeConversationId);
  const deleteConversation = useDeleteConversation();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load messages when conversation is selected
  useEffect(() => {
    if (conversationData?.messages) {
      const loadedMessages: Message[] = conversationData.messages.map((msg) => ({
        id: msg.id,
        content: msg.content,
        isUser: msg.role === "user",
        timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
        actionsTaken: msg.metadata?.actions_taken as string[] | undefined,
      }));
      setMessages(loadedMessages);
    }
  }, [conversationData]);

  const handleNewChat = () => {
    setActiveConversationId(null);
    setMessages([]);
    setHistoryOpen(false);
  };

  const handleSelectConversation = (conversation: ChatConversation) => {
    setActiveConversationId(conversation.id);
    setHistoryOpen(false);
  };

  const handleDeleteConversation = async (conversationId: string) => {
    if (!userId) {
      toast.error("User ID is required");
      return;
    }

    try {
      await deleteConversation.mutateAsync({ conversationId, userId });
      if (activeConversationId === conversationId) {
        handleNewChat();
      }
      refetchHistory();
      toast.success("Conversation deleted");
    } catch {
      toast.error("Failed to delete conversation");
    }
  };

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

      const data = await apiRequest<{
        message: string;
        data?: Record<string, unknown> | null;
        sources?: string[];
        actions_taken?: string[];
        confidence?: number;
        model?: string | null;
        timestamp?: string;
        success?: boolean;
        conversation_id?: string;
      }>(`/agent/chat`, {
        method: "POST",
        body: JSON.stringify({
          message: userMessage.content,
          user_id: userId,
          session_id: sessionId,
          conversation_id: activeConversationId,
          include_sources: true,
          context: {},
        }),
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

      // Update active conversation ID from response (for new conversations)
      if (data.conversation_id && !activeConversationId) {
        setActiveConversationId(data.conversation_id);
      }

      // Refetch history to update conversation list
      refetchHistory();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "";
    const date = new Date(dateString);
    const now = new Date();
    const diffDays = Math.floor(
      (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24)
    );

    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  return (
    <Card className="flex flex-col h-[600px]">
      <CardHeader className="border-b pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <MessageCircle className="h-5 w-5" />
            Chat Assistant
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleNewChat}
              className="gap-1"
            >
              <Plus className="h-4 w-4" />
              New
            </Button>
            <Sheet open={historyOpen} onOpenChange={setHistoryOpen}>
              <SheetTrigger asChild>
                <Button variant="outline" size="sm" className="gap-1">
                  <History className="h-4 w-4" />
                  History
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="w-80">
                <SheetHeader>
                  <SheetTitle>Chat History</SheetTitle>
                </SheetHeader>
                <ScrollArea className="h-[calc(100vh-100px)] mt-4">
                  <div className="space-y-2 pr-4">
                    {historyData?.conversations?.length === 0 && (
                      <p className="text-sm text-muted-foreground text-center py-8">
                        No conversations yet
                      </p>
                    )}
                    {historyData?.conversations?.map((conversation) => (
                      <div
                        key={conversation.id}
                        className={`group flex items-center gap-2 p-3 rounded-lg cursor-pointer hover:bg-muted transition-colors ${
                          activeConversationId === conversation.id
                            ? "bg-muted"
                            : ""
                        }`}
                        onClick={() => handleSelectConversation(conversation)}
                      >
                        <MessageCircle className="h-4 w-4 text-muted-foreground shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">
                            {conversation.title}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {formatDate(conversation.updated_at)}
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteConversation(conversation.id);
                          }}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </SheetContent>
            </Sheet>
          </div>
        </div>
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
                    className={`rounded-lg px-4 py-3 ${
                      message.isUser
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap leading-relaxed">
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
