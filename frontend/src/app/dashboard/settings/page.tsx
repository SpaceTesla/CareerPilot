"use client";

import { useEffect, useState } from "react";
import { usePreferences, useUpdatePreferences, useGoals, useUpdateGoals, JobSearchStatus } from "@/hooks/queries/useSettings";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { 
  Settings, 
  Target, 
  User, 
  Briefcase, 
  DollarSign, 
  Building, 
  Calendar, 
  Mail, 
  Bell, 
  Save, 
  Plus, 
  X,
  Loader2 
} from "lucide-react";
import { motion } from "framer-motion";

export default function SettingsPage() {
  const [userId, setUserId] = useState<string | null>(null);
  
  // Goals form state
  const [targetRole, setTargetRole] = useState("");
  const [compMin, setCompMin] = useState(0);
  const [compMax, setCompMax] = useState(0);
  const [companyInput, setCompanyInput] = useState("");
  const [companies, setCompanies] = useState<string[]>([]);
  const [timeline, setTimeline] = useState(12);

  // Preferences form state
  const [searchStatus, setSearchStatus] = useState<JobSearchStatus>("PASSIVE");
  const [digestEnabled, setDigestEnabled] = useState(true);
  const [digestDay, setDigestDay] = useState(1);
  const [digestHour, setDigestHour] = useState(9);
  const [emailNotifications, setEmailNotifications] = useState(true);

  useEffect(() => {
    setUserId(localStorage.getItem("cp_user_id"));
  }, []);

  const { data: preferences, isLoading: loadingPref } = usePreferences(userId);
  const { data: goals, isLoading: loadingGoals } = useGoals(userId);

  const updatePref = useUpdatePreferences(userId);
  const updateGoals = useUpdateGoals(userId);

  // Sync state with fetched database values
  useEffect(() => {
    if (goals) {
      setTargetRole(goals.target_role || "");
      setCompMin(goals.target_compensation_min || 0);
      setCompMax(goals.target_compensation_max || 0);
      setCompanies(goals.target_companies || []);
      setTimeline(goals.timeline_months || 12);
    }
  }, [goals]);

  useEffect(() => {
    if (preferences) {
      setSearchStatus(preferences.job_search_status || "PASSIVE");
      setDigestEnabled(preferences.weekly_digest_enabled);
      setDigestDay(preferences.digest_delivery_day ?? 1);
      setDigestHour(preferences.digest_delivery_hour ?? 9);
      setEmailNotifications(preferences.email_notifications);
    }
  }, [preferences]);

  const handleAddCompany = (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyInput.trim()) return;
    if (companies.includes(companyInput.trim())) {
      setCompanyInput("");
      return;
    }
    setCompanies((prev) => [...prev, companyInput.trim()]);
    setCompanyInput("");
  };

  const handleRemoveCompany = (name: string) => {
    setCompanies((prev) => prev.filter((c) => c !== name));
  };

  const handleSaveGoals = () => {
    if (!targetRole.trim()) {
      toast.error("Target role is required");
      return;
    }
    if (compMin > compMax) {
      toast.error("Minimum compensation cannot exceed maximum compensation");
      return;
    }

    updateGoals.mutate({
      target_role: targetRole,
      target_compensation_min: Number(compMin),
      target_compensation_max: Number(compMax),
      target_companies: companies,
      timeline_months: Number(timeline),
    }, {
      onSuccess: () => {
        toast.success("Career goals saved successfully!");
      },
      onError: (err) => {
        toast.error(err.message || "Failed to save career goals");
      }
    });
  };

  const handleSavePreferences = () => {
    updatePref.mutate({
      job_search_status: searchStatus,
      weekly_digest_enabled: digestEnabled,
      digest_delivery_day: Number(digestDay),
      digest_delivery_hour: Number(digestHour),
      email_notifications: emailNotifications,
    }, {
      onSuccess: () => {
        toast.success("Account preferences saved successfully!");
      },
      onError: (err) => {
        toast.error(err.message || "Failed to save account preferences");
      }
    });
  };

  const daysOfWeek = [
    { value: 0, label: "Sunday" },
    { value: 1, label: "Monday" },
    { value: 2, label: "Tuesday" },
    { value: 3, label: "Wednesday" },
    { value: 4, label: "Thursday" },
    { value: 5, label: "Friday" },
    { value: 6, label: "Saturday" },
  ];

  const hoursOfDay = Array.from({ length: 24 }, (_, i) => ({
    value: i,
    label: `${i === 0 ? 12 : i > 12 ? i - 12 : i} ${i >= 12 ? "PM" : "AM"}`,
  }));

  if (loadingPref || loadingGoals) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-1/4" />
        <Skeleton className="h-4 w-1/2" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="h-96 lg:col-span-2" />
          <Skeleton className="h-48" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <Settings className="h-8 w-8 text-primary" />
          Settings
        </h1>
        <p className="text-muted-foreground">
          Configure your target role search filters, automated digest settings, and communication preferences.
        </p>
      </div>

      <Tabs defaultValue="goals" className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="goals" className="flex items-center gap-1.5">
            <Target className="h-4 w-4" />
            Career Goals
          </TabsTrigger>
          <TabsTrigger value="preferences" className="flex items-center gap-1.5">
            <User className="h-4 w-4" />
            Account Preferences
          </TabsTrigger>
        </TabsList>

        <TabsContent value="goals">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid grid-cols-1 lg:grid-cols-3 gap-6"
          >
            {/* Core Form Card */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-lg">Target Career Specifications</CardTitle>
                <CardDescription>Target role metadata determines skill mismatch scoring weights.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Target Role */}
                <div className="space-y-2">
                  <Label htmlFor="targetRole" className="flex items-center gap-1.5">
                    <Briefcase className="h-4 w-4 text-muted-foreground" />
                    Target Role Title
                  </Label>
                  <Input 
                    id="targetRole"
                    placeholder="e.g. Senior Machine Learning Engineer" 
                    value={targetRole}
                    onChange={(e) => setTargetRole(e.target.value)}
                  />
                </div>

                {/* Compensation Range */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="compMin" className="flex items-center gap-1.5">
                      <DollarSign className="h-4 w-4 text-muted-foreground" />
                      Minimum Annual Compensation (USD)
                    </Label>
                    <Input 
                      id="compMin"
                      type="number"
                      placeholder="e.g. 120000" 
                      value={compMin || ""}
                      onChange={(e) => setCompMin(Number(e.target.value))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="compMax" className="flex items-center gap-1.5">
                      <DollarSign className="h-4 w-4 text-muted-foreground" />
                      Maximum Annual Compensation (USD)
                    </Label>
                    <Input 
                      id="compMax"
                      type="number"
                      placeholder="e.g. 180000" 
                      value={compMax || ""}
                      onChange={(e) => setCompMax(Number(e.target.value))}
                    />
                  </div>
                </div>

                {/* Timeline */}
                <div className="space-y-2">
                  <Label htmlFor="timeline" className="flex items-center gap-1.5">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    Target Transition Timeline (Months)
                  </Label>
                  <select
                    id="timeline"
                    value={timeline}
                    onChange={(e) => setTimeline(Number(e.target.value))}
                    className="w-full bg-background border rounded px-3 py-2 text-sm"
                  >
                    <option value={3}>3 Months</option>
                    <option value={6}>6 Months</option>
                    <option value={12}>12 Months</option>
                    <option value={18}>18 Months</option>
                    <option value={24}>24 Months</option>
                  </select>
                </div>

                {/* Companies list */}
                <div className="space-y-3">
                  <Label className="flex items-center gap-1.5">
                    <Building className="h-4 w-4 text-muted-foreground" />
                    Target Target Companies
                  </Label>
                  <form onSubmit={handleAddCompany} className="flex gap-2">
                    <Input 
                      placeholder="Add company name (e.g. Google)" 
                      value={companyInput}
                      onChange={(e) => setCompanyInput(e.target.value)}
                    />
                    <Button type="submit" variant="secondary" size="icon">
                      <Plus className="h-4 w-4" />
                    </Button>
                  </form>
                  <div className="flex flex-wrap gap-2 pt-1">
                    {companies.length === 0 ? (
                      <span className="text-xs text-muted-foreground italic">No target companies specified. Add one above.</span>
                    ) : (
                      companies.map((c) => (
                        <Badge key={c} variant="secondary" className="pl-2 pr-1 py-1 flex items-center gap-1">
                          {c}
                          <Button 
                            type="button"
                            variant="ghost" 
                            size="icon" 
                            className="h-4 w-4 rounded-full p-0 hover:bg-muted"
                            onClick={() => handleRemoveCompany(c)}
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        </Badge>
                      ))
                    )}
                  </div>
                </div>
              </CardContent>
              <CardFooter className="border-t pt-4">
                <Button 
                  onClick={handleSaveGoals} 
                  disabled={updateGoals.isPending}
                  className="w-full md:w-auto"
                >
                  {updateGoals.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Saving Goals...
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-2" />
                      Save Goals
                    </>
                  )}
                </Button>
              </CardFooter>
            </Card>

            {/* Explanatory Info Card */}
            <Card className="h-fit bg-gradient-to-br from-primary/5 to-transparent">
              <CardHeader>
                <CardTitle className="text-sm uppercase font-semibold text-muted-foreground">Goals Context</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-3 text-muted-foreground">
                <p>
                  Your target career details are integrated into the match algorithms to calculate:
                </p>
                <ul className="list-disc pl-4 space-y-1">
                  <li><strong>Position Deltas</strong>: detects missing skill gaps specifically relative to your target role.</li>
                  <li><strong>Attractiveness Score</strong>: matches salary ranges and company priorities.</li>
                  <li><strong>Passives Weekly digests</strong>: recommends opportunities matching target locations and companies.</li>
                </ul>
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>

        <TabsContent value="preferences">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid grid-cols-1 lg:grid-cols-3 gap-6"
          >
            {/* Core Form Card */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-lg">Account & notification setups</CardTitle>
                <CardDescription>Configure search status visibility and passive updates scheduling.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Search status */}
                <div className="space-y-2">
                  <Label htmlFor="searchStatus" className="flex items-center gap-1.5">
                    <Target className="h-4 w-4 text-muted-foreground" />
                    Job Search Status
                  </Label>
                  <select
                    id="searchStatus"
                    value={searchStatus}
                    onChange={(e) => setSearchStatus(e.target.value as JobSearchStatus)}
                    className="w-full bg-background border rounded px-3 py-2 text-sm"
                  >
                    <option value="ACTIVE">Actively Looking</option>
                    <option value="PASSIVE">Passive Matching</option>
                    <option value="CLOSED">Closed / Not Looking</option>
                  </select>
                </div>

                {/* Email toggle */}
                <div className="flex items-center justify-between border-b pb-4">
                  <div className="space-y-0.5">
                    <Label className="text-sm font-semibold flex items-center gap-1.5">
                      <Bell className="h-4 w-4 text-muted-foreground" />
                      Email Alerts
                    </Label>
                    <p className="text-xs text-muted-foreground">Receive immediate email alerts when workflow runs require approvals.</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={emailNotifications}
                    onChange={(e) => setEmailNotifications(e.target.checked)}
                    className="h-4 w-4 accent-primary"
                  />
                </div>

                {/* Weekly digest toggles */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between border-b pb-4">
                    <div className="space-y-0.5">
                      <Label className="text-sm font-semibold flex items-center gap-1.5">
                        <Mail className="h-4 w-4 text-muted-foreground" />
                        Weekly digest reports
                      </Label>
                      <p className="text-xs text-muted-foreground">Receive weekly passive market intelligence updates, score changes, and top recommendation lists.</p>
                    </div>
                    <input
                      type="checkbox"
                      checked={digestEnabled}
                      onChange={(e) => setDigestEnabled(e.target.checked)}
                      className="h-4 w-4 accent-primary"
                    />
                  </div>

                  {digestEnabled && (
                    <motion.div 
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      className="grid grid-cols-1 md:grid-cols-2 gap-4 pl-6 border-l-2 border-l-primary"
                    >
                      <div className="space-y-2">
                        <Label htmlFor="digestDay">Delivery Day</Label>
                        <select
                          id="digestDay"
                          value={digestDay}
                          onChange={(e) => setDigestDay(Number(e.target.value))}
                          className="w-full bg-background border rounded px-3 py-2 text-xs"
                        >
                          {daysOfWeek.map((d) => (
                            <option key={d.value} value={d.value}>{d.label}</option>
                          ))}
                        </select>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="digestHour">Delivery Hour</Label>
                        <select
                          id="digestHour"
                          value={digestHour}
                          onChange={(e) => setDigestHour(Number(e.target.value))}
                          className="w-full bg-background border rounded px-3 py-2 text-xs"
                        >
                          {hoursOfDay.map((h) => (
                            <option key={h.value} value={h.value}>{h.label}</option>
                          ))}
                        </select>
                      </div>
                    </motion.div>
                  )}
                </div>
              </CardContent>
              <CardFooter className="border-t pt-4">
                <Button 
                  onClick={handleSavePreferences} 
                  disabled={updatePref.isPending}
                  className="w-full md:w-auto"
                >
                  {updatePref.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Saving Preferences...
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-2" />
                      Save Preferences
                    </>
                  )}
                </Button>
              </CardFooter>
            </Card>

            {/* Explanatory Info Card */}
            <Card className="h-fit bg-gradient-to-br from-primary/5 to-transparent">
              <CardHeader>
                <CardTitle className="text-sm uppercase font-semibold text-muted-foreground">Preferences Context</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-3 text-muted-foreground">
                <p>
                  Passive digests run in the background on the scheduler matching your selected timezone.
                </p>
                <p>
                  Disabling weekly digests pauses background path delta scans, saving database traversals until re-enabled.
                </p>
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
