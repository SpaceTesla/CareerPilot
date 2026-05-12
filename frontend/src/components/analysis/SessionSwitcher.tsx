"use client";

import { useState, type MouseEvent } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  FileText,
  ChevronDown,
  Check,
  Trash2,
  Clock,
} from "lucide-react";
import {
  useResumeSessions,
  useSwitchSession,
  useDeleteSession,
  type ResumeSession,
} from "@/hooks/queries/useSessions";
import { toast } from "sonner";

interface SessionSwitcherProps {
  userId: string | null;
  currentProfileId: string | null;
}

export default function SessionSwitcher({
  userId,
  currentProfileId,
}: SessionSwitcherProps) {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<ResumeSession | null>(
    null
  );

  const { data, isLoading } = useResumeSessions(userId);
  const switchSession = useSwitchSession();
  const deleteSession = useDeleteSession();

  const handleSwitchSession = async (session: ResumeSession) => {
    if (session.profile_id === currentProfileId) return;

    try {
      await switchSession.mutateAsync({
        sessionId: session.session_id,
        userId: session.user_id,
      });

      toast.success(`Switched to "${session.name}"`);
    } catch {
      toast.error("Failed to switch session");
    }
  };

  const handleDeleteSession = async () => {
    if (!sessionToDelete) return;

    try {
      await deleteSession.mutateAsync({
        sessionId: sessionToDelete.session_id,
        userId: sessionToDelete.user_id,
      });
      toast.success("Session deleted");
      setDeleteDialogOpen(false);
      setSessionToDelete(null);
    } catch {
      toast.error("Failed to delete session");
    }
  };

  const confirmDelete = (session: ResumeSession, e: MouseEvent) => {
    e.stopPropagation();
    setSessionToDelete(session);
    setDeleteDialogOpen(true);
  };

  if (isLoading) {
    return <Skeleton className="h-9 w-40" />;
  }

  const sessions = data?.sessions || [];
  const activeSession = sessions.find((s) => s.is_active);

  if (sessions.length === 0) {
    return null;
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "";
    const date = new Date(dateString);
    const now = new Date();
    const diffDays = Math.floor(
      (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24)
    );

    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" className="gap-2 max-w-[200px]">
            <FileText className="h-4 w-4 shrink-0" />
            <span className="truncate">
              {activeSession?.name || "Select Resume"}
            </span>
            <ChevronDown className="h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64">
          <DropdownMenuLabel className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Resume Sessions
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          {sessions.map((session) => (
            <DropdownMenuItem
              key={session.session_id}
              className="flex items-center justify-between gap-2 cursor-pointer"
              onClick={() => handleSwitchSession(session)}
            >
              <div className="flex items-center gap-2 flex-1 min-w-0">
                {session.is_active && (
                  <Check className="h-4 w-4 text-green-600 shrink-0" />
                )}
                <span className="truncate">{session.name}</span>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {formatDate(session.last_accessed_at)}
                </span>
                {!session.is_active && sessions.length > 1 && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={(e) => confirmDelete(session, e)}
                  >
                    <Trash2 className="h-3 w-3 text-destructive" />
                  </Button>
                )}
              </div>
            </DropdownMenuItem>
          ))}
          {sessions.length > 1 && (
            <>
              <DropdownMenuSeparator />
              <div className="px-2 py-1.5">
                <Badge variant="secondary" className="text-xs">
                  {sessions.length} resume{sessions.length > 1 ? "s" : ""}
                </Badge>
              </div>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Resume Session?</AlertDialogTitle>
            <AlertDialogDescription>
              This will delete the session "{sessionToDelete?.name}". The
              resume data will still be available, but this session history will
              be removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteSession}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
