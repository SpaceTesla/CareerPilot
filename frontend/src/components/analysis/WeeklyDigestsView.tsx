"use client";

import { useState } from "react";
import {
  useUserDigests,
  useUserDigestDetail,
  useUpdatePreferences,
} from "@/hooks/queries/useStrategy";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Mail,
  Calendar,
  Clock,
  Settings,
  TrendingUp,
  Briefcase,
  CheckCircle2,
  AlertCircle,
  ChevronRight,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";

export default function WeeklyDigestsView({ userId }: { userId: string | null }) {
  const [selectedDigestId, setSelectedDigestId] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);

  // Fetch digest history
  const { data: historyData, isLoading: historyLoading } = useUserDigests(userId);
  const digests = historyData?.digests ?? [];

  // Determine active digest details
  const activeDigestId = selectedDigestId || (digests.length > 0 ? digests[0].id : null);
  const { data: digestDetail, isLoading: detailLoading } = useUserDigestDetail(activeDigestId);

  // Preference mutations
  const updatePrefs = useUpdatePreferences();
  const [enabled, setEnabled] = useState("true");
  const [day, setDay] = useState("1"); // Default: Monday
  const [hour, setHour] = useState("9"); // Default: 9 AM

  const handleSaveSettings = () => {
    updatePrefs.mutate(
      {
        weekly_digest_enabled: enabled === "true",
        digest_delivery_day: parseInt(day),
        digest_delivery_hour: parseInt(hour),
      },
      {
        onSuccess: () => {
          toast.success("Digest preferences saved!");
          setShowSettings(false);
        },
        onError: (err) => {
          toast.error(err.message || "Failed to update settings");
        },
      }
    );
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "Not Sent Yet";
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Sidebar - Digest History */}
      <div className="lg:col-span-1 space-y-4">
        <Card className="shadow-sm border border-muted/50 backdrop-blur-md bg-card/60">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg font-bold flex items-center gap-2">
                <Mail className="h-5 w-5 text-primary" />
                Weekly Digests
              </CardTitle>
              <CardDescription>Stay updated passively</CardDescription>
            </div>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8 hover:bg-primary/5 hover:text-primary transition-colors duration-200"
              onClick={() => setShowSettings(!showSettings)}
            >
              <Settings className="h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent className="px-2 space-y-1 max-h-[400px] overflow-y-auto">
            {showSettings ? (
              <div className="p-3 space-y-4 animate-fadeIn">
                <h4 className="text-sm font-semibold flex items-center gap-1">
                  <Sparkles className="h-4 w-4 text-yellow-500" />
                  Digest Settings
                </h4>
                <div className="space-y-3">
                  <div className="space-y-1">
                    <Label htmlFor="enabled">Weekly Email Digests</Label>
                    <Select value={enabled} onValueChange={setEnabled}>
                      <SelectTrigger id="enabled">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="true">Enabled</SelectItem>
                        <SelectItem value="false">Disabled</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="day">Delivery Day</Label>
                    <Select value={day} onValueChange={setDay}>
                      <SelectTrigger id="day">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="0">Sunday</SelectItem>
                        <SelectItem value="1">Monday</SelectItem>
                        <SelectItem value="2">Tuesday</SelectItem>
                        <SelectItem value="3">Wednesday</SelectItem>
                        <SelectItem value="4">Thursday</SelectItem>
                        <SelectItem value="5">Friday</SelectItem>
                        <SelectItem value="6">Saturday</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="hour">Delivery Hour</Label>
                    <Select value={hour} onValueChange={setHour}>
                      <SelectTrigger id="hour">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="8">8:00 AM</SelectItem>
                        <SelectItem value="9">9:00 AM</SelectItem>
                        <SelectItem value="10">10:00 AM</SelectItem>
                        <SelectItem value="12">12:00 PM</SelectItem>
                        <SelectItem value="14">2:00 PM</SelectItem>
                        <SelectItem value="17">5:00 PM</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex gap-2 pt-2">
                    <Button
                      size="sm"
                      className="w-full"
                      onClick={handleSaveSettings}
                      disabled={updatePrefs.isPending}
                    >
                      Save
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="w-full"
                      onClick={() => setShowSettings(false)}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              </div>
            ) : historyLoading ? (
              [1, 2, 3].map((i) => (
                <div key={i} className="p-3">
                  <Skeleton className="h-10 w-full" />
                </div>
              ))
            ) : digests.length === 0 ? (
              <div className="p-8 text-center text-sm text-muted-foreground">
                No digests generated yet. Make sure you have weekly digests enabled.
              </div>
            ) : (
              digests.map((d) => {
                const isActive = d.id === activeDigestId;
                return (
                  <button
                    key={d.id}
                    onClick={() => {
                      setSelectedDigestId(d.id);
                      setShowSettings(false);
                    }}
                    className={`w-full flex items-center justify-between p-3 rounded-lg text-left transition-all duration-200 border ${
                      isActive
                        ? "bg-primary/10 border-primary/30 text-primary font-medium shadow-sm translate-x-1"
                        : "border-transparent hover:bg-muted/50 text-foreground hover:translate-x-0.5"
                    }`}
                  >
                    <div className="space-y-1">
                      <p className="text-sm font-semibold">{formatDate(d.sent_at)}</p>
                      <div className="flex items-center gap-2 text-xs">
                        <span className="flex items-center gap-0.5">
                          Health Score: <strong className="ml-0.5">{d.health_score.score}</strong>
                        </span>
                        {d.health_score.delta !== 0 && (
                          <Badge
                            variant={d.health_score.delta > 0 ? "default" : "destructive"}
                            className="scale-90 text-[10px] px-1 py-0"
                          >
                            {d.health_score.delta > 0 ? "+" : ""}
                            {d.health_score.delta.toFixed(1)}
                          </Badge>
                        )}
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

      {/* Main Content - Selected Digest Details */}
      <div className="lg:col-span-2 space-y-6">
        {detailLoading ? (
          <Card className="shadow-sm border border-muted/50">
            <CardHeader>
              <Skeleton className="h-6 w-1/3 mb-2" />
              <Skeleton className="h-4 w-2/3" />
            </CardHeader>
            <CardContent className="space-y-4">
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-24 w-full" />
            </CardContent>
          </Card>
        ) : !digestDetail ? (
          <Card className="shadow-sm border border-muted/50 h-full flex flex-col items-center justify-center p-12 text-center text-muted-foreground">
            <Mail className="h-12 w-12 mb-4 opacity-50" />
            <p className="text-sm">Select a weekly digest to view its detailed career health and market insights.</p>
          </Card>
        ) : (
          <div className="space-y-6 animate-fadeIn">
            {/* Header Card */}
            <Card className="shadow-sm border border-muted/50 overflow-hidden bg-gradient-to-r from-card to-primary/5">
              <CardHeader className="pb-4">
                <div className="flex flex-row items-center justify-between">
                  <Badge variant="outline" className="border-primary/20 text-primary">
                    Digest Overview
                  </Badge>
                  <span className="text-xs text-muted-foreground font-medium flex items-center gap-1">
                    <Calendar className="h-3.5 w-3.5" />
                    Sent {formatDate(digestDetail.sent_at)}
                  </span>
                </div>
                <CardTitle className="text-xl font-bold mt-2">
                  Weekly Career Intelligence Summary
                </CardTitle>
                <CardDescription>
                  Personalized career telemetry and active guidance report
                </CardDescription>
              </CardHeader>
              <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4 border-t pt-4">
                {/* Health Score Summary */}
                <div className="bg-background/40 backdrop-blur-sm rounded-lg p-3 border space-y-1">
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    Career Health
                  </p>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-extrabold tracking-tight">
                      {digestDetail.content.health_score.score}
                    </span>
                    {digestDetail.content.health_score.delta !== 0 && (
                      <span
                        className={`text-xs font-bold ${
                          digestDetail.content.health_score.delta > 0
                            ? "text-green-500"
                            : "text-red-500"
                        }`}
                      >
                        {digestDetail.content.health_score.delta > 0 ? "▲" : "▼"}{" "}
                        {Math.abs(digestDetail.content.health_score.delta).toFixed(1)}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-muted-foreground leading-tight">
                    {digestDetail.content.health_score.primary_insight}
                  </p>
                </div>

                {/* Market Insights */}
                <div className="bg-background/40 backdrop-blur-sm rounded-lg p-3 border md:col-span-2 space-y-1">
                  <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide flex items-center gap-1">
                    <TrendingUp className="h-3.5 w-3.5 text-primary" />
                    Market Pulse
                  </p>
                  <p className="text-xs text-foreground/90 leading-relaxed pt-0.5">
                    {digestDetail.content.market_insights}
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Position Delta (Skills Progress) */}
            <Card className="shadow-sm border border-muted/50">
              <CardHeader className="pb-3">
                <CardTitle className="text-md font-bold flex items-center gap-1.5">
                  <Sparkles className="h-4 w-4 text-primary" />
                  Position Delta Progress
                </CardTitle>
                <CardDescription>
                  Tracking changes in your skills gap relative to target roles
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Resolved Gaps */}
                  <div className="space-y-2">
                    <h5 className="text-xs font-bold text-green-600 flex items-center gap-1 uppercase tracking-wide">
                      <CheckCircle2 className="h-4.5 w-4.5" />
                      Acquired Skills (This Week)
                    </h5>
                    {digestDetail.content.position_delta.resolved_gaps.length === 0 ? (
                      <p className="text-xs text-muted-foreground italic pl-5">
                        No new skills registered this week.
                      </p>
                    ) : (
                      <ul className="space-y-1.5 pl-5 list-disc text-sm text-foreground/90">
                        {digestDetail.content.position_delta.resolved_gaps.map((skill, index) => {
                          const name = typeof skill === "string" ? skill : skill.name;
                          return <li key={index} className="marker:text-green-500 font-medium">{name}</li>;
                        })}
                      </ul>
                    )}
                  </div>

                  {/* Remaining Gaps */}
                  <div className="space-y-2">
                    <h5 className="text-xs font-bold text-amber-500 flex items-center gap-1 uppercase tracking-wide">
                      <AlertCircle className="h-4.5 w-4.5" />
                      Primary Skill Gaps
                    </h5>
                    {digestDetail.content.position_delta.remaining_gaps.length === 0 ? (
                      <p className="text-xs text-muted-foreground italic pl-5">
                        No remaining skill gaps for your active target.
                      </p>
                    ) : (
                      <ul className="space-y-1.5 pl-5 list-disc text-sm text-foreground/90">
                        {digestDetail.content.position_delta.remaining_gaps.map((skill, index) => {
                          const name = typeof skill === "string" ? skill : skill.name;
                          return <li key={index} className="marker:text-amber-500 font-medium">{name}</li>;
                        })}
                      </ul>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Opportunities Spotlight */}
            <Card className="shadow-sm border border-muted/50">
              <CardHeader className="pb-3">
                <CardTitle className="text-md font-bold flex items-center gap-1.5">
                  <Briefcase className="h-4 w-4 text-primary" />
                  Recommended Opportunities
                </CardTitle>
                <CardDescription>
                  Highly-aligned job opportunities tailored for you
                </CardDescription>
              </CardHeader>
              <CardContent>
                {digestDetail.content.recommendations.length === 0 ? (
                  <div className="text-center py-6 text-sm text-muted-foreground">
                    No new job recommendations in this digest.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {digestDetail.content.recommendations.map((rec) => (
                      <div
                        key={rec.id}
                        className="p-3.5 border rounded-lg hover:shadow-md transition-all duration-200 bg-background/50 hover:bg-background/80"
                      >
                        <p className="font-bold text-sm text-foreground line-clamp-1">
                          {rec.title}
                        </p>
                        <p className="text-xs text-muted-foreground font-medium mt-1">
                          {rec.company_name}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
