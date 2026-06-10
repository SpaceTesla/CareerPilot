"use client";

import { useState } from "react";
import {
  useStrategyReviews,
  useStrategyReviewDetail,
  useUpdateActionItem,
  useCompleteReview,
} from "@/hooks/queries/useStrategy";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
  Compass,
  Calendar,
  CheckCircle2,
  ListTodo,
  TrendingUp,
  AlertTriangle,
  ChevronRight,
  MessageSquare,
  ClipboardCheck,
} from "lucide-react";
import { toast } from "sonner";

export default function StrategyReviewsView({ userId }: { userId: string | null }) {
  const [selectedReviewId, setSelectedReviewId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState("");
  const [acceptItems, setAcceptItems] = useState(true);

  // Fetch reviews list
  const { data: reviewsData, isLoading: listLoading } = useStrategyReviews(userId);
  const reviews = reviewsData?.reviews ?? [];

  // Determine active review details
  const activeReviewId = selectedReviewId || (reviews.length > 0 ? reviews[0].id : null);
  const { data: reviewDetail, isLoading: detailLoading } = useStrategyReviewDetail(activeReviewId);

  // Mutations
  const updateActionItem = useUpdateActionItem();
  const completeReview = useCompleteReview();

  const handleToggleActionItem = (itemId: string, currentStatus: string) => {
    if (!activeReviewId) return;

    const newStatus = currentStatus === "COMPLETED" ? "TODO" : "COMPLETED";
    updateActionItem.mutate(
      {
        itemId,
        reviewId: activeReviewId,
        status: newStatus,
      },
      {
        onSuccess: () => {
          toast.success("Action item status updated");
        },
        onError: (err) => {
          toast.error(err.message || "Failed to update item");
        },
      }
    );
  };

  const handleSubmitReviewCompletion = () => {
    if (!activeReviewId) return;

    completeReview.mutate(
      {
        reviewId: activeReviewId,
        feedbackText: feedback,
        acceptActionItems: acceptItems,
      },
      {
        onSuccess: () => {
          toast.success("Strategy review completed!");
          setFeedback("");
        },
        onError: (err) => {
          toast.error(err.message || "Failed to complete review");
        },
      }
    );
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const getDifficultyColor = (diff: string) => {
    switch (diff.toUpperCase()) {
      case "EASY":
        return "bg-green-500/10 text-green-500 border-green-500/25";
      case "MODERATE":
        return "bg-amber-500/10 text-amber-500 border-amber-500/25";
      case "HARD":
        return "bg-red-500/10 text-red-500 border-red-500/25";
      default:
        return "bg-muted text-muted-foreground border-muted";
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Sidebar - Review Timelines */}
      <div className="lg:col-span-1 space-y-4">
        <Card className="shadow-sm border border-muted/50 backdrop-blur-md bg-card/60">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg font-bold flex items-center gap-2">
              <Compass className="h-5 w-5 text-primary" />
              Strategic Timeline
            </CardTitle>
            <CardDescription>Monthly career checkpoints</CardDescription>
          </CardHeader>
          <CardContent className="px-2 space-y-1 max-h-[400px] overflow-y-auto">
            {listLoading ? (
              [1, 2].map((i) => (
                <div key={i} className="p-3">
                  <Skeleton className="h-12 w-full" />
                </div>
              ))
            ) : reviews.length === 0 ? (
              <div className="p-8 text-center text-sm text-muted-foreground">
                No monthly strategy reviews generated yet. Reviews run automatically every 30 days.
              </div>
            ) : (
              reviews.map((r) => {
                const isActive = r.id === activeReviewId;
                return (
                  <button
                    key={r.id}
                    onClick={() => {
                      setSelectedReviewId(r.id);
                      setFeedback("");
                    }}
                    className={`w-full flex items-center justify-between p-3.5 rounded-lg text-left transition-all duration-200 border ${
                      isActive
                        ? "bg-primary/10 border-primary/30 text-primary font-medium shadow-sm translate-x-1"
                        : "border-transparent hover:bg-muted/50 text-foreground hover:translate-x-0.5"
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold">{formatDate(r.created_at)}</p>
                        <Badge
                          variant={r.status === "COMPLETED" ? "default" : "secondary"}
                          className="scale-90 text-[10px] px-1 py-0 uppercase"
                        >
                          {r.status === "PENDING_REVIEW" ? "Pending" : "Completed"}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>Health change:</span>
                        <strong className="text-foreground">
                          {r.health_score_start.toFixed(0)} → {r.health_score_end.toFixed(0)}
                        </strong>
                      </div>
                    </div>
                    <ChevronRight className={`h-4 w-4 opacity-65 ${isActive ? "text-primary" : "text-muted-foreground"}`} />
                  </button>
                );
              })
            )}
          </CardContent>
        </Card>
      </div>

      {/* Main Content - Review Details & Actions */}
      <div className="lg:col-span-2 space-y-6">
        {detailLoading ? (
          <Card className="shadow-sm border border-muted/50">
            <CardHeader>
              <Skeleton className="h-6 w-1/4 mb-2" />
              <Skeleton className="h-4 w-1/2" />
            </CardHeader>
            <CardContent className="space-y-6">
              <Skeleton className="h-28 w-full" />
              <Skeleton className="h-36 w-full" />
            </CardContent>
          </Card>
        ) : !reviewDetail ? (
          <Card className="shadow-sm border border-muted/50 h-full flex flex-col items-center justify-center p-12 text-center text-muted-foreground">
            <Compass className="h-12 w-12 mb-4 opacity-50" />
            <p className="text-sm">Select a monthly checkpoint from the timeline to audit your strategic progress.</p>
          </Card>
        ) : (
          <div className="space-y-6 animate-fadeIn">
            {/* Main Insight Card */}
            <Card className="shadow-sm border border-muted/50 overflow-hidden bg-gradient-to-r from-card to-primary/5">
              <CardHeader className="pb-4">
                <div className="flex flex-row items-center justify-between">
                  <Badge variant={reviewDetail.status === "COMPLETED" ? "default" : "secondary"} className="uppercase">
                    {reviewDetail.status === "PENDING_REVIEW" ? "Pending User Feedback" : "Review Completed"}
                  </Badge>
                  <span className="text-xs text-muted-foreground font-medium flex items-center gap-1">
                    <Calendar className="h-3.5 w-3.5" />
                    Generated {formatDate(reviewDetail.id)}
                  </span>
                </div>
                <CardTitle className="text-xl font-bold mt-2">
                  Monthly Strategic Career Audit
                </CardTitle>
                <CardDescription>
                  Target Profile alignment, skill delta review, and prioritized action mapping
                </CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4 border-t pt-4">
                {/* Stats block */}
                <div className="bg-background/40 backdrop-blur-sm rounded-lg p-3.5 border space-y-2">
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    Career Direction
                  </p>
                  <div className="space-y-1">
                    <p className="text-sm font-bold text-foreground">
                      {reviewDetail.goals?.target_role || "Not Specified"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Target Timeline: {reviewDetail.goals?.timeline_months || 12} months
                    </p>
                  </div>
                  <div className="flex items-center gap-4 pt-1.5 border-t">
                    <div>
                      <p className="text-[10px] text-muted-foreground font-semibold uppercase">Start Health</p>
                      <p className="text-md font-bold">{reviewDetail.metrics.health_score_start}</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground font-semibold uppercase">Audit Health</p>
                      <p className="text-md font-bold">{reviewDetail.metrics.current_health_score}</p>
                    </div>
                    {reviewDetail.metrics.current_health_score - reviewDetail.metrics.health_score_start !== 0 && (
                      <div>
                        <p className="text-[10px] text-muted-foreground font-semibold uppercase">Delta</p>
                        <Badge
                          variant={
                            reviewDetail.metrics.current_health_score > reviewDetail.metrics.health_score_start
                              ? "default"
                              : "destructive"
                          }
                          className="scale-90"
                        >
                          {reviewDetail.metrics.current_health_score > reviewDetail.metrics.health_score_start ? "+" : ""}
                          {(reviewDetail.metrics.current_health_score - reviewDetail.metrics.health_score_start).toFixed(1)}
                        </Badge>
                      </div>
                    )}
                  </div>
                </div>

                {/* AI advice summary */}
                <div className="bg-background/40 backdrop-blur-sm rounded-lg p-3.5 border space-y-1">
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide flex items-center gap-1">
                    <TrendingUp className="h-3.5 w-3.5 text-primary" />
                    Strategic Guidance
                  </p>
                  <p className="text-xs text-foreground/90 leading-relaxed pt-0.5 whitespace-pre-wrap">
                    {reviewDetail.insights_summary}
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Action Items List */}
            <Card className="shadow-sm border border-muted/50">
              <CardHeader className="pb-3">
                <CardTitle className="text-md font-bold flex items-center gap-1.5">
                  <ListTodo className="h-4.5 w-4.5 text-primary" />
                  Prioritized Action Items
                </CardTitle>
                <CardDescription>
                  Follow these customized checkpoints to optimize your career path
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {reviewDetail.action_items.length === 0 ? (
                  <p className="text-sm text-muted-foreground italic text-center py-4">
                    No action items generated for this period.
                  </p>
                ) : (
                  reviewDetail.action_items.map((item) => {
                    const isCompleted = item.status === "COMPLETED";
                    const isCancelled = item.status === "CANCELLED";

                    return (
                      <div
                        key={item.id}
                        onClick={() => !isCancelled && handleToggleActionItem(item.id, item.status)}
                        className={`flex items-start gap-3 p-3 border rounded-lg transition-all duration-200 cursor-pointer ${
                          isCompleted
                            ? "bg-muted/30 border-muted text-muted-foreground line-through"
                            : isCancelled
                            ? "bg-red-500/5 border-red-500/10 text-muted-foreground line-through opacity-60"
                            : "hover:bg-muted/50 bg-background/40 hover:shadow-sm"
                        }`}
                      >
                        <Checkbox
                          checked={isCompleted}
                          disabled={isCancelled}
                          className="mt-0.5"
                          onCheckedChange={() => {}} // Click handled on parent div for easier touch target
                        />
                        <div className="flex-1 space-y-1">
                          <p className="text-sm font-medium leading-normal">
                            {item.description}
                          </p>
                          <div className="flex items-center gap-2 text-xs">
                            <Badge variant="outline" className={`scale-90 px-1 py-0 text-[10px] ${getDifficultyColor(item.difficulty)}`}>
                              {item.difficulty}
                            </Badge>
                            {item.target_date && (
                              <span className="text-muted-foreground">
                                Target: {formatDate(item.target_date)}
                              </span>
                            )}
                            {isCancelled && (
                              <Badge variant="destructive" className="scale-90 px-1 py-0 text-[10px]">
                                Cancelled
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </CardContent>
            </Card>

            {/* Complete Checkpoint Feedback Form (PENDING_REVIEW only) */}
            {reviewDetail.status === "PENDING_REVIEW" && (
              <Card className="shadow-sm border border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
                <CardHeader className="pb-3">
                  <CardTitle className="text-md font-bold flex items-center gap-1.5">
                    <MessageSquare className="h-4.5 w-4.5 text-primary" />
                    Review Validation
                  </CardTitle>
                  <CardDescription>
                    Provide alignment feedback to commit this strategic milestone to your profile
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="feedback" className="text-xs font-semibold">
                      Your Feedback / Notes (e.g. adjustments, focus targets)
                    </Label>
                    <Textarea
                      id="feedback"
                      value={feedback}
                      onChange={(e) => setFeedback(e.target.value)}
                      placeholder="Share your goals and any modifications you want to record..."
                      rows={3}
                      className="bg-card/50"
                    />
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="accept"
                      checked={acceptItems}
                      onCheckedChange={(checked) => setAcceptItems(checked === true)}
                    />
                    <Label htmlFor="accept" className="text-xs font-medium cursor-pointer leading-none">
                      Accept and track these prioritized career action items
                    </Label>
                  </div>

                  {!acceptItems && (
                    <div className="flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-600">
                      <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                      <p>
                        Declining action items will mark all tasks for this month as CANCELLED.
                      </p>
                    </div>
                  )}

                  <Button
                    onClick={handleSubmitReviewCompletion}
                    disabled={completeReview.isPending}
                    className="w-full flex items-center justify-center gap-1"
                  >
                    {completeReview.isPending ? (
                      "Completing Review Checkpoint..."
                    ) : (
                      <>
                        <ClipboardCheck className="h-4.5 w-4.5" />
                        Finalize Strategic Review
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
