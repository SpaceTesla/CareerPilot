"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  MapPin,
  Calendar,
  Trash2,
  ExternalLink,
  ClipboardList,
  Cookie,
  CheckCircle2,
  XCircle,
  Loader2,
  Shield,
  Info,
} from "lucide-react";
import {
  useApplications,
  useUpdateApplication,
  useDeleteApplication,
  useSessionStatus,
  useImportSession,
  useDeleteSession,
} from "@/hooks/queries/useApplications";
import { ApplicationStatus, JobApplication } from "@/types/analysis";
import { cn } from "@/lib/utils";

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  return months === 1 ? "1 month ago" : `${months} months ago`;
}

// ── Supported portals ──────────────────────────────────────────────────────

const PORTALS = [
  { value: "linkedin", label: "LinkedIn" },
  { value: "indeed", label: "Indeed" },
  { value: "naukri", label: "Naukri" },
  { value: "glassdoor", label: "Glassdoor" },
];

// ── Column definitions ──────────────────────────────────────────────────────

const COLUMNS: { status: ApplicationStatus; label: string; color: string }[] = [
  { status: "applied", label: "Applied", color: "bg-blue-500" },
  { status: "interviewing", label: "Interviewing", color: "bg-yellow-500" },
  { status: "offer", label: "Offer", color: "bg-green-500" },
  { status: "rejected", label: "Rejected", color: "bg-red-500" },
];

// ── Status badge colors ─────────────────────────────────────────────────────

function statusVariant(status: ApplicationStatus): "default" | "secondary" | "destructive" | "outline" {
  if (status === "offer") return "default";
  if (status === "rejected") return "destructive";
  if (status === "interviewing") return "secondary";
  return "outline";
}

// ── Import Cookies Panel ───────────────────────────────────────────────────

function ImportCookiesPanel({ userId }: { userId: string }) {
  const [selectedPortal, setSelectedPortal] = useState<string>("");
  const [cookieJson, setCookieJson] = useState<string>("");
  const [parseError, setParseError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showInstructions, setShowInstructions] = useState(false);

  const { data: sessionData, isLoading: sessionsLoading } = useSessionStatus(userId);
  const importSession = useImportSession();
  const deleteSession = useDeleteSession();

  const activeSessions = sessionData?.sessions ?? [];

  const handleImport = () => {
    setParseError(null);
    setSuccessMessage(null);

    if (!selectedPortal) {
      setParseError("Please select a portal.");
      return;
    }
    if (!cookieJson.trim()) {
      setParseError("Please paste the cookie JSON.");
      return;
    }

    let parsed: unknown[];
    try {
      parsed = JSON.parse(cookieJson.trim());
      if (!Array.isArray(parsed) || parsed.length === 0) {
        setParseError("Cookies must be a non-empty JSON array. Check you copied the full export.");
        return;
      }
    } catch {
      setParseError(
        "Invalid JSON. Make sure you copied the full cookie export from the browser extension."
      );
      return;
    }

    importSession.mutate(
      { user_id: userId, portal: selectedPortal, cookies: parsed },
      {
        onSuccess: (data) => {
          setSuccessMessage(data.message);
          setCookieJson("");
          setSelectedPortal("");
        },
        onError: (err) => {
          setParseError(err.message || "Import failed. Please try again.");
        },
      }
    );
  };

  return (
    <Card className="border-dashed border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Cookie className="h-5 w-5 text-primary" />
          Portal Sessions
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 ml-auto"
            onClick={() => setShowInstructions(!showInstructions)}
          >
            <Info className="h-4 w-4" />
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Active sessions */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-muted-foreground">Active Sessions</p>
          {sessionsLoading ? (
            <div className="flex gap-2">
              <Skeleton className="h-8 w-24" />
              <Skeleton className="h-8 w-24" />
            </div>
          ) : activeSessions.length === 0 ? (
            <p className="text-sm text-orange-500 flex items-center gap-1.5">
              <XCircle className="h-4 w-4 flex-shrink-0" />
              No sessions saved. Import cookies below to enable Auto-Fill.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {activeSessions.map((s) => (
                <Badge
                  key={s.portal}
                  variant="secondary"
                  className="flex items-center gap-1.5 pl-2 pr-1 py-1.5 text-sm"
                >
                  <Shield className="h-3.5 w-3.5 text-green-500" />
                  <span className="capitalize font-medium">{s.portal}</span>
                  {s.saved_at && (
                    <span className="text-xs text-muted-foreground ml-1">
                      ({timeAgo(s.saved_at)})
                    </span>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-5 w-5 ml-1 hover:bg-destructive/10"
                    onClick={() => deleteSession.mutate({ userId, portal: s.portal })}
                    disabled={deleteSession.isPending}
                  >
                    <Trash2 className="h-3 w-3 text-destructive" />
                  </Button>
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* Instructions (collapsible) */}
        {showInstructions && (
          <div className="rounded-lg bg-muted/50 p-4 text-sm space-y-2 border">
            <p className="font-semibold">How to export cookies:</p>
            <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
              <li>
                Install{" "}
                <a
                  href="https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline text-primary"
                >
                  Cookie-Editor
                </a>{" "}
                or{" "}
                <a
                  href="https://chromewebstore.google.com/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline text-primary"
                >
                  EditThisCookie
                </a>{" "}
                extension in your browser.
              </li>
              <li>Navigate to the portal (e.g., <code>linkedin.com</code>) while <strong>logged in</strong>.</li>
              <li>Click the extension icon → <strong>Export</strong> (copies JSON to clipboard).</li>
              <li>Come back here, select the portal, paste the JSON, and click <strong>Import</strong>.</li>
            </ol>
            <p className="text-xs text-muted-foreground mt-2">
              ⚠️ Sessions expire with the browser cookie TTL. Re-import when expired.
            </p>
          </div>
        )}

        {/* Import form */}
        <div className="space-y-3">
          <div className="flex gap-2">
            <Select value={selectedPortal} onValueChange={setSelectedPortal}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="Select portal" />
              </SelectTrigger>
              <SelectContent>
                {PORTALS.map((p) => (
                  <SelectItem key={p.value} value={p.value}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              onClick={handleImport}
              disabled={importSession.isPending || !selectedPortal || !cookieJson.trim()}
              className="shrink-0"
            >
              {importSession.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  Importing…
                </>
              ) : (
                <>
                  <Cookie className="h-4 w-4 mr-1" />
                  Import Cookies
                </>
              )}
            </Button>
          </div>

          <Textarea
            value={cookieJson}
            onChange={(e) => {
              setCookieJson(e.target.value);
              setParseError(null);
              setSuccessMessage(null);
            }}
            placeholder='Paste the exported cookie JSON array here... [{"name": "...", "value": "...", ...}]'
            rows={4}
            className="font-mono text-xs"
          />

          {parseError && (
            <p className="text-sm text-destructive flex items-center gap-1.5">
              <XCircle className="h-4 w-4 flex-shrink-0" />
              {parseError}
            </p>
          )}
          {successMessage && (
            <p className="text-sm text-green-600 flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
              {successMessage}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Application detail dialog ───────────────────────────────────────────────

function ApplicationDialog({
  app,
  onClose,
  userId,
}: {
  app: JobApplication | null;
  onClose: () => void;
  userId: string;
}) {
  const [notes, setNotes] = useState(app?.notes ?? "");
  const updateApp = useUpdateApplication();
  const deleteApp = useDeleteApplication();

  useEffect(() => {
    setNotes(app?.notes ?? "");
  }, [app]);

  if (!app) return null;

  const handleStatusChange = (status: ApplicationStatus) => {
    updateApp.mutate({ applicationId: app.id, userId, status });
  };

  const handleSaveNotes = () => {
    updateApp.mutate({ applicationId: app.id, userId, notes });
  };

  const handleDelete = () => {
    deleteApp.mutate(
      { applicationId: app.id, userId },
      { onSuccess: onClose }
    );
  };

  return (
    <Dialog open={!!app} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-lg">{app.job_title}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {app.company && (
            <p className="text-sm text-muted-foreground font-medium">{app.company}</p>
          )}

          {/* Status picker */}
          <div className="space-y-1">
            <p className="text-sm font-medium">Status</p>
            <Select defaultValue={app.status} onValueChange={(v) => handleStatusChange(v as ApplicationStatus)}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {COLUMNS.map((col) => (
                  <SelectItem key={col.status} value={col.status}>
                    {col.label}
                  </SelectItem>
                ))}
                <SelectItem value="withdrawn">Withdrawn</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Location / Source */}
          <div className="flex gap-4 text-sm text-muted-foreground">
            {app.location && <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{app.location}</span>}
            {app.source && <span>via {app.source}</span>}
          </div>

          {/* Applied date */}
          {app.applied_at && (
            <p className="text-sm text-muted-foreground flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              Applied {timeAgo(app.applied_at!)}
            </p>
          )}

          {/* Notes */}
          <div className="space-y-2">
            <p className="text-sm font-medium">Notes</p>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add notes about this application..."
              rows={4}
            />
            <Button size="sm" onClick={handleSaveNotes} disabled={updateApp.isPending}>
              Save Notes
            </Button>
          </div>

          {/* Job link */}
          {app.job_url && (
            <Button variant="outline" size="sm" asChild>
              <a href={app.job_url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-3.5 w-3.5 mr-1" />
                View Job Posting
              </a>
            </Button>
          )}

          {/* Delete */}
          <Button
            variant="ghost"
            size="sm"
            className="text-destructive hover:text-destructive w-full"
            onClick={handleDelete}
            disabled={deleteApp.isPending}
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Remove Application
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ── Kanban card ─────────────────────────────────────────────────────────────

function ApplicationCard({
  app,
  onClick,
}: {
  app: JobApplication;
  onClick: () => void;
}) {
  return (
    <Card
      className="cursor-pointer hover:shadow-md transition-all duration-200 border-l-4 border-l-primary"
      onClick={onClick}
    >
      <CardContent className="pt-4 pb-3 px-4 space-y-2">
        <p className="font-semibold text-sm leading-tight line-clamp-2">{app.job_title}</p>
        {app.company && (
          <p className="text-xs text-muted-foreground font-medium">{app.company}</p>
        )}
        {app.location && (
          <p className="text-xs text-muted-foreground flex items-center gap-1">
            <MapPin className="h-3 w-3" />
            {app.location}
          </p>
        )}
        <div className="flex items-center justify-between pt-1">
          {app.source && (
            <Badge variant="outline" className="text-xs">{app.source}</Badge>
          )}
          {app.applied_at && (
            <span className="text-xs text-muted-foreground">
              {timeAgo(app.applied_at!)}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ── Main page ───────────────────────────────────────────────────────────────

export default function ApplicationsPage() {
  const [userId, setUserId] = useState<string | null>(null);
  const [selectedApp, setSelectedApp] = useState<JobApplication | null>(null);

  useEffect(() => {
    setUserId(localStorage.getItem("cp_user_id"));
  }, []);

  const { data, isLoading } = useApplications(userId);

  const byStatus = (data?.by_status ?? {}) as Record<ApplicationStatus, number>;
  const applications: JobApplication[] = data?.applications ?? [];

  const getAppsForStatus = (status: ApplicationStatus) =>
    applications.filter((a) => a.status === status);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Application Tracker</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {COLUMNS.map((col) => (
            <div key={col.status} className="space-y-3">
              <Skeleton className="h-8 w-full" />
              {[1, 2].map((i) => <Skeleton key={i} className="h-24 w-full" />)}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!userId) {
    return (
      <div className="text-center py-16 text-muted-foreground">
        <ClipboardList className="h-12 w-12 mx-auto mb-4" />
        <p>Upload a resume to start tracking applications.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <ClipboardList className="h-6 w-6" />
        <h1 className="text-2xl font-bold">Application Tracker</h1>
        {data && (
          <Badge variant="secondary" className="ml-auto">
            {applications.length} total
          </Badge>
        )}
      </div>

      {/* Import Cookies Panel */}
      <ImportCookiesPanel userId={userId} />

      {/* Kanban board */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 items-start">
        {COLUMNS.map((col) => {
          const colApps = getAppsForStatus(col.status);
          const count = byStatus[col.status] ?? colApps.length;
          return (
            <div key={col.status} className="space-y-3">
              {/* Column header */}
              <div className={cn("flex items-center gap-2 rounded-md px-3 py-2", `${col.color}/10`)}>
                <span className={cn("w-2 h-2 rounded-full", col.color)} />
                <span className="font-semibold text-sm">{col.label}</span>
                <Badge variant="outline" className="ml-auto text-xs">{count}</Badge>
              </div>

              {/* Cards */}
              <div className="space-y-3 min-h-[4rem]">
                {colApps.length === 0 ? (
                  <div className="border-2 border-dashed rounded-md p-4 text-center text-xs text-muted-foreground">
                    No applications
                  </div>
                ) : (
                  colApps.map((app) => (
                    <ApplicationCard
                      key={app.id}
                      app={app}
                      onClick={() => setSelectedApp(app)}
                    />
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Detail dialog */}
      {selectedApp && userId && (
        <ApplicationDialog
          app={selectedApp}
          onClose={() => setSelectedApp(null)}
          userId={userId}
        />
      )}
    </div>
  );
}
