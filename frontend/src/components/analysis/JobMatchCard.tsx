"use client";

import { useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  ExternalLink,
  BookmarkPlus,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Monitor,
  Bot,
  Pen,
  Sparkles,
  ThumbsUp,
  ThumbsDown,
  Loader2,
  Send,
  Ban,
  Filter,
} from "lucide-react";
import { useJobMatch } from "@/hooks/queries/useAnalysis";
import { useJobRecommendations } from "@/hooks/queries/useJobs";
import { useSaveApplication, useAutoFillApplication, useAutoFillTask, useConfirmAutoFill } from "@/hooks/queries/useApplications";
import { useFeedback, useSubmitFeedback, useDeleteFeedback } from "@/hooks/queries/useFeedback";
import { cn } from "@/lib/utils";
import { AutoFillStep } from "@/types/analysis";

interface JobMatchCardProps {
  userId: string | null;
}

const commonRoles = [
  "Backend Developer",
  "Frontend Developer",
  "Full-Stack Developer",
  "DevOps Engineer",
  "Data Scientist",
];

export default function JobMatchCard({ userId }: JobMatchCardProps) {
  const [selectedRole, setSelectedRole] = useState<string>("");
  const [autoFillDialog, setAutoFillDialog] = useState<{ open: boolean; taskId: string | null; jobTitle?: string; jobCompany?: string }>({
    open: false,
    taskId: null,
  });
  const [trackedUrls, setTrackedUrls] = useState<Set<string>>(new Set());
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<string>>(new Set()); // empty = all

  const { data: matchData, isLoading: matchLoading } = useJobMatch(userId, selectedRole || undefined);
  const { data: jobRecs, isLoading: jobsLoading } = useJobRecommendations(userId, 5);
  const { feedbackMap } = useFeedback(userId, "job");

  const saveApplication = useSaveApplication();
  const autoFill = useAutoFillApplication();
  const confirmAutoFill = useConfirmAutoFill();
  const taskPoll = useAutoFillTask(autoFillDialog.taskId, userId);
  const submitFeedback = useSubmitFeedback();
  const deleteFeedback = useDeleteFeedback();

  const handleConfirm = (confirmed: boolean) => {
    if (!userId || !autoFillDialog.taskId) return;
    confirmAutoFill.mutate({ taskId: autoFillDialog.taskId, userId, confirmed });
  };

  const handleTrack = (job: { title?: string; company?: string; url?: string; location?: string; source?: string }) => {
    if (!userId || !job.url || trackedUrls.has(job.url)) return;
    saveApplication.mutate(
      {
        user_id: userId,
        job_title: job.title || "Untitled",
        company: job.company,
        job_url: job.url,
        source: job.source,
        location: job.location,
      },
      { onSuccess: () => setTrackedUrls((prev) => new Set(prev).add(job.url!)) }
    );
  };

  const handleAutoFill = async (job: { url?: string; title?: string; company?: string }) => {
    if (!userId || !job.url) return;
    const result = await autoFill.mutateAsync({
      user_id: userId,
      job_url: job.url,
      job_title: job.title,
      job_company: job.company,
    });
    setAutoFillDialog({ open: true, taskId: result.task_id, jobTitle: job.title, jobCompany: job.company });
  };

  const handleFeedback = (itemIdentifier: string, value: "helpful" | "not_helpful") => {
    if (!userId) return;
    const current = feedbackMap.get(itemIdentifier);
    if (current === value) {
      deleteFeedback.mutate({ user_id: userId, item_type: "job", item_identifier: itemIdentifier });
    } else {
      submitFeedback.mutate({ user_id: userId, item_type: "job", item_identifier: itemIdentifier, feedback: value });
    }
  };

  return (
    <div className="space-y-6">
      {/* Job Match Score */}
      <Card>
        <CardHeader>
          <CardTitle>Job Match Score</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Role Selection */}
          <div className="space-y-3">
            <Label>Select Role</Label>
            <div className="flex flex-wrap gap-2">
              {commonRoles.map((role) => (
                <Button
                  key={role}
                  type="button"
                  variant={selectedRole === role ? "default" : "outline"}
                  size="sm"
                  onClick={() => setSelectedRole(role)}
                  className="transition-all"
                >
                  {role}
                </Button>
              ))}
            </div>
          </div>

          {matchLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-4 w-full" />
            </div>
          ) : matchData ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-lg font-semibold">Overall Match</span>
                <Badge
                  variant="outline"
                  className={cn(
                    "text-2xl font-bold px-4 py-1",
                    matchData.match_score >= 70
                      ? "text-green-600 border-green-600"
                      : matchData.match_score >= 50
                        ? "text-yellow-600 border-yellow-600"
                        : "text-red-600 border-red-600"
                  )}
                >
                  {matchData.match_score.toFixed(1)}%
                </Badge>
              </div>
              <Progress
                value={matchData.match_score}
                className={cn(
                  "h-3",
                  matchData.match_score >= 70
                    ? "[&>div]:bg-green-600"
                    : matchData.match_score >= 50
                      ? "[&>div]:bg-yellow-600"
                      : "[&>div]:bg-red-600"
                )}
              />

              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">
                    Skills Match
                  </p>
                  <p className="text-lg font-semibold">
                    {matchData.skills_match.toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">
                    Resume Quality
                  </p>
                  <p className="text-lg font-semibold">
                    {matchData.resume_quality.toFixed(1)}%
                  </p>
                </div>
              </div>

              {matchData.missing_skills &&
                matchData.missing_skills.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium mb-2">Missing Skills</h3>
                    <div className="flex flex-wrap gap-2">
                      {matchData.missing_skills.map((skill, idx) => (
                        <Badge
                          key={idx}
                          variant="destructive"
                          className="text-xs"
                        >
                          {skill}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              Select a role to see match score
            </p>
          )}
        </CardContent>
      </Card>

      {/* Job Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle>Job Recommendations</CardTitle>
        </CardHeader>
        <CardContent>
          {jobsLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-24 w-full" />
              ))}
            </div>
          ) : jobRecs && jobRecs.jobs && jobRecs.jobs.length > 0 ? (
            <div className="space-y-4">
              {/* Platform filter */}
              {(() => {
                const platforms = Array.from(
                  new Set(
                    jobRecs.jobs
                      .map((j) => j.source)
                      .filter((s): s is string => !!s)
                  )
                ).sort();

                if (platforms.length <= 1) return null;

                const isAllSelected = selectedPlatforms.size === 0;
                const togglePlatform = (p: string) => {
                  setSelectedPlatforms((prev) => {
                    const next = new Set(prev);
                    if (next.has(p)) {
                      next.delete(p);
                    } else {
                      next.add(p);
                    }
                    // If all selected again or none left, reset to "all"
                    if (next.size === 0 || next.size === platforms.length) {
                      return new Set();
                    }
                    return next;
                  });
                };

                return (
                  <div className="flex items-center gap-2 flex-wrap">
                    <Filter className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                    <Button
                      type="button"
                      variant={isAllSelected ? "default" : "outline"}
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => setSelectedPlatforms(new Set())}
                    >
                      All
                    </Button>
                    {platforms.map((p) => (
                      <Button
                        key={p}
                        type="button"
                        variant={!isAllSelected && selectedPlatforms.has(p) ? "default" : "outline"}
                        size="sm"
                        className="h-7 text-xs"
                        onClick={() => togglePlatform(p)}
                      >
                        {p}
                      </Button>
                    ))}
                  </div>
                );
              })()}

              {(() => {
                const filteredJobs = selectedPlatforms.size === 0
                  ? jobRecs.jobs
                  : jobRecs.jobs.filter((j) => j.source && selectedPlatforms.has(j.source));

                return (
                  <>
                    <p className="text-sm text-muted-foreground">
                      {selectedPlatforms.size === 0
                        ? `Found ${jobRecs.total_found} jobs matching your profile`
                        : `Showing ${filteredJobs.length} of ${jobRecs.total_found} jobs`}
                    </p>
                    {filteredJobs.length === 0 ? (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        No jobs found for the selected platform(s).
                      </p>
                    ) : filteredJobs.map((job, idx) => (
                      <Card
                        key={idx}
                        className="hover:shadow-md transition-all duration-200 border-l-4 border-l-primary"
                      >
                        <CardContent className="">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 space-y-3">
                              <div className="space-y-2">
                                <div className="flex items-start gap-3">
                                  <h3 className="font-semibold text-lg leading-tight">
                                    {job.title || "Job Opening"}
                                  </h3>
                                  {job.company && (
                                    <Badge
                                      variant="secondary"
                                      className="text-xs shrink-0"
                                    >
                                      {job.company}
                                    </Badge>
                                  )}
                                </div>
                                {job.location && (
                                  <p className="text-sm text-muted-foreground flex items-center gap-1">
                                    <span className="text-destructive">📍</span>
                                    {job.location}
                                  </p>
                                )}
                              </div>
                              <p className="text-sm text-muted-foreground line-clamp-2">
                                {job.description ||
                                  job.content ||
                                  "View job details for more information."}
                              </p>
                              <div className="flex flex-wrap gap-2">
                                {job.job_type && (
                                  <Badge variant="outline" className="text-xs">
                                    {job.job_type}
                                  </Badge>
                                )}
                                {job.salary_min && job.salary_max && (
                                  <Badge variant="outline" className="text-xs">
                                    ${job.salary_min.toLocaleString()} - $
                                    {job.salary_max.toLocaleString()}
                                  </Badge>
                                )}
                                {job.source && (
                                  <Badge variant="outline" className="text-xs">
                                    via {job.source}
                                  </Badge>
                                )}
                              </div>
                            </div>
                            <div className="flex flex-col gap-2 shrink-0 items-end">
                              {/* Apply */}
                              <Button variant="default" size="sm" asChild>
                                <a href={job.url} target="_blank" rel="noopener noreferrer">
                                  <ExternalLink className="h-4 w-4 mr-1" />
                                  Apply
                                </a>
                              </Button>

                              {/* Track */}
                              <Button
                                variant="outline"
                                size="sm"
                                disabled={trackedUrls.has(job.url ?? "") || saveApplication.isPending}
                                onClick={() => handleTrack(job)}
                              >
                                {trackedUrls.has(job.url ?? "") ? (
                                  <><CheckCircle2 className="h-4 w-4 mr-1 text-green-600" />Tracked</>
                                ) : (
                                  <><BookmarkPlus className="h-4 w-4 mr-1" />Track</>
                                )}
                              </Button>

                              {/* Auto-Fill */}
                              <Button
                                variant="outline"
                                size="sm"
                                disabled={autoFill.isPending || !job.url}
                                onClick={() => handleAutoFill({ url: job.url, title: job.title, company: job.company })}
                              >
                                {autoFill.isPending ? (
                                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                                ) : (
                                  <Bot className="h-4 w-4 mr-1" />
                                )}
                                Auto-Fill
                              </Button>

                              {/* Feedback thumbs */}
                              <div className="flex gap-1">
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className={cn("h-7 w-7", feedbackMap.get(job.url ?? "") === "helpful" && "text-green-600")}
                                  onClick={() => handleFeedback(job.url ?? job.title ?? "", "helpful")}
                                >
                                  <ThumbsUp className="h-4 w-4" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className={cn("h-7 w-7", feedbackMap.get(job.url ?? "") === "not_helpful" && "text-red-500")}
                                  onClick={() => handleFeedback(job.url ?? job.title ?? "", "not_helpful")}
                                >
                                  <ThumbsDown className="h-4 w-4" />
                                </Button>
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </>
                );
              })()}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              No job recommendations available
            </p>
          )}
        </CardContent>
      </Card>

      {/* Auto-Fill progress dialog */}
      <Dialog
        open={autoFillDialog.open}
        onOpenChange={(o) => setAutoFillDialog((s) => ({ ...s, open: o }))}
      >
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5" />
              Auto-Fill: {autoFillDialog.jobTitle ? `${autoFillDialog.jobTitle}${autoFillDialog.jobCompany ? ` at ${autoFillDialog.jobCompany}` : ""}` : "Application"}
              {taskPoll.data?.portal && (
                <Badge variant="outline" className="capitalize">{taskPoll.data.portal}</Badge>
              )}
            </DialogTitle>
          </DialogHeader>

          {/* Overall status bar */}
          {taskPoll.data && (
            <div className="flex items-center gap-2">
              {(taskPoll.data.status === "pending" || taskPoll.data.status === "running") && (
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
              )}
              {taskPoll.data?.status === "done" && taskPoll.data?.result_status === "filled" && (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              )}
              {taskPoll.data?.status === "done" && taskPoll.data?.result_status === "submitted" && (
                <CheckCircle2 className="h-4 w-4 text-green-600" />
              )}
              {taskPoll.data?.status === "done" && taskPoll.data?.result_status === "cancelled" && (
                <Ban className="h-4 w-4 text-muted-foreground" />
              )}
              {(taskPoll.data?.status === "error" || taskPoll.data?.result_status === "error") && (
                <XCircle className="h-4 w-4 text-destructive" />
              )}
              {taskPoll.data.result_status === "no_fields_found" && (
                <AlertCircle className="h-4 w-4 text-yellow-500" />
              )}
              <Badge
                variant={
                  taskPoll.data?.status === "done" && (taskPoll.data?.result_status === "filled" || taskPoll.data?.result_status === "submitted")
                    ? "default"
                    : taskPoll.data?.status === "error"
                      ? "destructive"
                      : "secondary"
                }
              >
                {taskPoll.data?.status === "pending" && "Starting…"}
                {taskPoll.data?.status === "running" && "Running…"}
                {taskPoll.data?.status === "awaiting_confirmation" && "⏳ Awaiting confirmation"}
                {taskPoll.data?.status === "done" && taskPoll.data?.result_status === "filled" && `Filled ${taskPoll.data.fields_filled.length} field(s)`}
                {taskPoll.data?.status === "done" && taskPoll.data?.result_status === "submitted" && "✓ Application submitted!"}
                {taskPoll.data?.status === "done" && taskPoll.data?.result_status === "cancelled" && "Cancelled by user"}
                {taskPoll.data?.status === "done" && taskPoll.data?.result_status === "no_fields_found" && "No fields found"}
                {taskPoll.data?.status === "error" && "Error"}
              </Badge>
              {taskPoll.data.fields_filled?.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {taskPoll.data.fields_filled.map((f) => (
                    <Badge key={f} variant="secondary" className="text-xs">{f}</Badge>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Step-by-step progress timeline with screenshots */}
          <div className="space-y-4">
            {(!taskPoll.data || taskPoll.data.steps.length === 0) && (
              <div className="flex items-center gap-3 py-4">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Starting Playwright automation…</p>
              </div>
            )}

            {taskPoll.data?.steps.map((step: AutoFillStep, i: number) => {
              const isLast = i === taskPoll.data!.steps.length - 1;
              const isRunning = isLast && (taskPoll.data!.status === "running" || taskPoll.data!.status === "pending");

              const icon =
                step.step === "navigating" ? <Loader2 className="h-4 w-4 animate-spin text-primary" /> :
                  step.step === "loaded" ? <Monitor className="h-4 w-4 text-blue-500" /> :
                    step.step === "session_missing" ? <AlertCircle className="h-4 w-4 text-orange-500" /> :
                      step.step === "awaiting_confirmation" ? <Send className="h-4 w-4 text-violet-500" /> :
                        step.step === "analyzing" ? (isRunning ? <Sparkles className="h-4 w-4 animate-pulse text-violet-500" /> : <Sparkles className="h-4 w-4 text-violet-500" />) :
                          step.step === "filling" ? (isRunning ? <Loader2 className="h-4 w-4 animate-spin text-primary" /> : <Pen className="h-4 w-4 text-primary" />) :
                            step.step === "done" ? <CheckCircle2 className="h-4 w-4 text-green-500" /> :
                              step.step === "no_fields" ? <AlertCircle className="h-4 w-4 text-yellow-500" /> :
                                <XCircle className="h-4 w-4 text-destructive" />;

              return (
                <div key={i} className="flex gap-3">
                  {/* Timeline line */}
                  <div className="flex flex-col items-center">
                    <div className="mt-1 flex-shrink-0">{icon}</div>
                    {i < taskPoll.data!.steps.length - 1 && (
                      <div className="w-px flex-1 bg-border mt-1 mb-[-8px]" />
                    )}
                  </div>

                  {/* Step content */}
                  <div className="pb-4 flex-1 min-w-0">
                    <p className={`text-sm font-medium capitalize ${step.step === "session_missing" ? "text-orange-500" : ""}`}>
                      {step.step === "session_missing" ? "Session Not Found" : step.step.replace("_", " ")}
                    </p>
                    {step.step === "awaiting_confirmation" ? (
                      <p className="text-xs font-medium text-violet-600 mt-0.5">{step.message}</p>
                    ) : step.step === "session_missing" ? (
                      <p className="text-xs text-orange-500 mt-0.5">
                        {step.message.split("Go to")[0]}
                        <a
                          href="/dashboard/applications"
                          className="underline font-medium"
                          onClick={() => setAutoFillDialog({ open: false, taskId: null })}
                        >
                          Go to Applications → Import Cookies
                        </a>
                        {" "}to restore your login, then try Auto-Fill again.
                      </p>
                    ) : (
                      <p className="text-xs text-muted-foreground mt-0.5">{step.message}</p>
                    )}
                    {step.screenshot && (
                      <div className="mt-2 rounded-md overflow-hidden border bg-muted">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={`data:image/jpeg;base64,${step.screenshot}`}
                          alt={`Screenshot: ${step.step}`}
                          className="w-full object-contain max-h-64 cursor-zoom-in hover:max-h-none transition-all"
                          onClick={(e) => {
                            const img = e.currentTarget;
                            img.style.maxHeight = img.style.maxHeight === "none" ? "16rem" : "none";
                          }}
                        />
                        <p className="text-xs text-muted-foreground px-2 py-1">
                          {new Date(step.timestamp).toLocaleTimeString()} — click image to expand
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Spinner appended while still running after last step */}
            {taskPoll.data && (taskPoll.data.status === "running" || taskPoll.data.status === "pending") &&
              taskPoll.data.steps.length > 0 &&
              taskPoll.data.steps[taskPoll.data.steps.length - 1].step !== "navigating" && (
                <div className="flex items-center gap-2 pl-7">
                  <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                  <p className="text-xs text-muted-foreground">Processing…</p>
                </div>
              )}
          </div>

          {/* ── Confirmation panel (shown when awaiting user decision) ── */}
          {taskPoll.data?.status === "awaiting_confirmation" && (
            <div className="border border-violet-300 dark:border-violet-700 rounded-lg p-4 space-y-3 bg-violet-50 dark:bg-violet-950/30">
              <p className="text-sm font-semibold text-violet-800 dark:text-violet-300 flex items-center gap-2">
                <Send className="h-4 w-4" />
                Ready to submit — please review
              </p>
              {taskPoll.data.confirm_details && (
                <div className="text-xs text-muted-foreground space-y-1">
                  <p><span className="font-medium">Job:</span> {taskPoll.data.confirm_details.job}</p>
                  {taskPoll.data.confirm_details.fields_filled.length > 0 && (
                    <p>
                      <span className="font-medium">Fields filled:</span>{" "}
                      {taskPoll.data.confirm_details.fields_filled.join(", ")}
                    </p>
                  )}
                </div>
              )}
              <p className="text-xs text-muted-foreground">
                Click <span className="font-medium text-green-700 dark:text-green-400">Submit</span> to send your application,
                or <span className="font-medium text-destructive">Cancel</span> to discard.
              </p>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  className="bg-green-600 hover:bg-green-700 text-white"
                  disabled={confirmAutoFill.isPending}
                  onClick={() => handleConfirm(true)}
                >
                  {confirmAutoFill.isPending ? (
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4 mr-1" />
                  )}
                  Submit Application
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={confirmAutoFill.isPending}
                  onClick={() => handleConfirm(false)}
                >
                  <Ban className="h-4 w-4 mr-1" />
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
