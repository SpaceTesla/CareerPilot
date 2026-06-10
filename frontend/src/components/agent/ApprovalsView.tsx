"use client";

import { useState } from "react";
import { usePendingApprovals, useSubmitApprovalAction, useSupervisorDecisions, useStartAgentRun, useAgentSessionState } from "@/hooks/queries/useAgent";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { 
  CheckCircle, 
  XCircle, 
  ShieldCheck, 
  Clock, 
  Play, 
  Brain, 
  Edit3, 
  Save, 
  CornerDownRight, 
  AlertTriangle,
  History,
  FileText,
  UserCheck
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

interface ApprovalsViewProps {
  userId: string | null;
}

export default function ApprovalsView({ userId }: ApprovalsViewProps) {
  const [activeTab, setActiveTab] = useState<"pending" | "history" | "trigger">("pending");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editPayload, setEditPayload] = useState<string>("");
  const [customMsg, setCustomMsg] = useState("");
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);

  // Queries & Mutations
  const { data: pendingApprovals, isLoading: loadingApprovals, refetch: refetchApprovals } = usePendingApprovals(userId);
  const submitApproval = useSubmitApprovalAction(userId);
  const startAgentRun = useStartAgentRun();
  
  // To show decision log, we'll fetch from the active thread or a static default thread if empty
  const selectedThreadId = pendingApprovals?.[0]?.thread_id || activeThreadId || "";
  const { data: decisionLogsData, isLoading: loadingDecisions } = useSupervisorDecisions(selectedThreadId || null);
  const { data: sessionState } = useAgentSessionState(selectedThreadId || null);

  const handleStartRun = () => {
    if (!customMsg.trim()) return;
    const testThreadId = `thread_${Math.random().toString(36).substring(2, 10)}`;
    setActiveThreadId(testThreadId);
    
    startAgentRun.mutate({
      threadId: testThreadId,
      userMessage: customMsg,
    }, {
      onSuccess: () => {
        setCustomMsg("");
      }
    });
  };

  const handleAction = (approvalId: string, action: "approved" | "rejected") => {
    submitApproval.mutate({
      approvalId,
      action,
    }, {
      onSuccess: () => {
        refetchApprovals();
      }
    });
  };

  const startEditing = (id: string, payload: Record<string, any>) => {
    setEditingId(id);
    setEditPayload(JSON.stringify(payload, null, 2));
  };

  const saveAndApprove = (approvalId: string) => {
    try {
      const parsed = JSON.parse(editPayload);
      submitApproval.mutate({
        approvalId,
        action: "modified",
        editedPayload: parsed,
      }, {
        onSuccess: () => {
          setEditingId(null);
          refetchApprovals();
        }
      });
    } catch (err) {
      alert("Invalid JSON payload structure. Please check and try again.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-gradient-to-br from-primary/5 via-transparent to-transparent border-primary/20">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs uppercase font-semibold text-muted-foreground">Pending Approvals</CardDescription>
            <CardTitle className="text-3xl font-extrabold flex items-center gap-2">
              <UserCheck className="h-6 w-6 text-primary" />
              {pendingApprovals?.length ?? 0}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">Actions requiring human oversight before submitting.</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-green-500/5 via-transparent to-transparent border-green-500/10">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs uppercase font-semibold text-muted-foreground">Supervisor Status</CardDescription>
            <CardTitle className="text-3xl font-extrabold flex items-center gap-2 text-green-500">
              <ShieldCheck className="h-6 w-6" />
              Active
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">Guardrail and agent safety routing layers are operational.</p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-blue-500/5 via-transparent to-transparent border-blue-500/10">
          <CardHeader className="pb-2">
            <CardDescription className="text-xs uppercase font-semibold text-muted-foreground">Agent Thread</CardDescription>
            <CardTitle className="text-lg font-bold flex items-center gap-2 truncate">
              <Brain className="h-5 w-5 text-blue-500" />
              <span className="truncate max-w-[200px] text-xs font-mono">{selectedThreadId || "No Active Thread"}</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground capitalize">
              State: <span className="font-semibold text-blue-500">{sessionState?.status || "Idle"}</span>
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs Layout */}
      <div className="flex gap-2 border-b pb-2">
        <Button 
          variant={activeTab === "pending" ? "default" : "ghost"} 
          onClick={() => setActiveTab("pending")}
          className="flex items-center gap-1.5"
        >
          <Clock className="h-4 w-4" />
          Pending Approvals
          {pendingApprovals && pendingApprovals.length > 0 && (
            <Badge variant="secondary" className="ml-1 px-1.5 py-0.5 text-xs bg-primary/20 text-primary hover:bg-primary/20">
              {pendingApprovals.length}
            </Badge>
          )}
        </Button>
        <Button 
          variant={activeTab === "history" ? "default" : "ghost"} 
          onClick={() => setActiveTab("history")}
          className="flex items-center gap-1.5"
        >
          <History className="h-4 w-4" />
          Supervisor Decision Logs
        </Button>
        <Button 
          variant={activeTab === "trigger" ? "default" : "ghost"} 
          onClick={() => setActiveTab("trigger")}
          className="flex items-center gap-1.5"
        >
          <Play className="h-4 w-4" />
          Interactive Run Test
        </Button>
      </div>

      {/* Tab Contents */}
      <AnimatePresence mode="wait">
        {activeTab === "pending" && (
          <motion.div
            key="pending"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-4"
          >
            {loadingApprovals ? (
              <div className="space-y-3">
                <Skeleton className="h-32 w-full" />
                <Skeleton className="h-32 w-full" />
              </div>
            ) : !pendingApprovals || pendingApprovals.length === 0 ? (
              <div className="text-center py-12 border rounded-lg border-dashed bg-muted/20">
                <ShieldCheck className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
                <h3 className="font-semibold text-lg">No Pending Approvals</h3>
                <p className="text-sm text-muted-foreground max-w-sm mx-auto mt-1">
                  The agents are currently in autopilot mode or waiting for your requests. Try starting a thread.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {pendingApprovals.map((appr) => (
                  <Card key={appr.id} className="overflow-hidden border-l-4 border-l-orange-500">
                    <CardHeader className="bg-orange-500/5 pb-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="h-5 w-5 text-orange-500" />
                          <CardTitle className="text-base font-bold capitalize">
                            Approval Required: {appr.action_type.replace(/_/g, " ")}
                          </CardTitle>
                        </div>
                        <Badge variant="outline" className="font-mono text-xs">
                          Thread: {appr.thread_id.substring(0, 15)}...
                        </Badge>
                      </div>
                      <CardDescription className="text-xs">
                        Created {new Date(appr.created_at).toLocaleString()}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-4">
                      {editingId === appr.id ? (
                        <div className="space-y-3">
                          <p className="text-xs font-semibold text-muted-foreground">Edit JSON Payload Details:</p>
                          <Textarea
                            value={editPayload}
                            onChange={(e) => setEditPayload(e.target.value)}
                            rows={8}
                            className="font-mono text-xs"
                          />
                          <div className="flex gap-2">
                            <Button 
                              size="sm" 
                              onClick={() => saveAndApprove(appr.id)}
                              disabled={submitApproval.isPending}
                            >
                              <Save className="h-3.5 w-3.5 mr-1" />
                              Save & Apply Changes
                            </Button>
                            <Button 
                              size="sm" 
                              variant="outline" 
                              onClick={() => setEditingId(null)}
                            >
                              Cancel
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          <div className="bg-muted p-4 rounded-lg font-mono text-xs overflow-x-auto max-h-60">
                            <pre>{JSON.stringify(appr.payload, null, 2)}</pre>
                          </div>
                          <div className="flex flex-wrap gap-2 pt-2">
                            <Button
                              onClick={() => handleAction(appr.id, "approved")}
                              disabled={submitApproval.isPending}
                              className="bg-green-600 hover:bg-green-500 text-white"
                            >
                              <CheckCircle className="h-4 w-4 mr-1.5" />
                              Approve
                            </Button>
                            <Button
                              onClick={() => startEditing(appr.id, appr.payload)}
                              disabled={submitApproval.isPending}
                              variant="outline"
                            >
                              <Edit3 className="h-4 w-4 mr-1.5" />
                              Modify Payload
                            </Button>
                            <Button
                              onClick={() => handleAction(appr.id, "rejected")}
                              disabled={submitApproval.isPending}
                              variant="destructive"
                            >
                              <XCircle className="h-4 w-4 mr-1.5" />
                              Reject
                            </Button>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </motion.div>
        )}

        {activeTab === "history" && (
          <motion.div
            key="history"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-4"
          >
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <History className="h-5 w-5 text-primary" />
                  Routing Decisions
                </CardTitle>
                <CardDescription>
                  Audit log of routing decisions evaluated by the Supervisor Agent for thread: <span className="font-mono text-xs">{selectedThreadId || "N/A"}</span>
                </CardDescription>
              </CardHeader>
              <CardContent>
                {loadingDecisions ? (
                  <div className="space-y-3">
                    <Skeleton className="h-16 w-full" />
                    <Skeleton className="h-16 w-full" />
                  </div>
                ) : !decisionLogsData || decisionLogsData.decisions.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-6">
                    No supervisor decisions recorded on this thread. Run an agent execution to populate routing actions.
                  </p>
                ) : (
                  <div className="relative border-l pl-6 space-y-6">
                    {decisionLogsData.decisions.map((dec) => (
                      <div key={dec.id} className="relative">
                        <div className="absolute -left-[31px] top-1.5 bg-primary/10 border border-primary h-6 w-6 rounded-full flex items-center justify-center">
                          <CornerDownRight className="h-3 w-3 text-primary" />
                        </div>
                        <div className="bg-muted/40 p-4 rounded-lg border">
                          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                            <span className="font-bold text-sm text-primary">Node: {dec.current_node}</span>
                            <Badge variant="outline" className="capitalize bg-primary/5 text-primary text-xs">
                              Route: {dec.routing_decision.replace(/_/g, " ")}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground mb-2">
                            {new Date(dec.created_at).toLocaleString()}
                          </p>
                          <div className="text-sm bg-background p-3 rounded border font-sans text-muted-foreground italic">
                            &quot;{dec.reasoning_explanation}&quot;
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}

        {activeTab === "trigger" && (
          <motion.div
            key="trigger"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-4"
          >
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Brain className="h-5 w-5 text-primary" />
                  Initiate Multi-Agent Thread
                </CardTitle>
                <CardDescription>
                  Submit a prompt to spark the supervisor agent. The supervisor will coordinate research agents, auto-scoring, and queue form submissions.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-muted-foreground">Agent Prompt</label>
                  <Textarea
                    placeholder="e.g. Verify my skills suitability for Google Senior Software Engineer, perform market research and generate structured recommendation plan."
                    value={customMsg}
                    onChange={(e) => setCustomMsg(e.target.value)}
                    rows={4}
                  />
                </div>
                <Button 
                  onClick={handleStartRun}
                  disabled={startAgentRun.isPending || !customMsg.trim()}
                  className="w-full md:w-auto"
                >
                  {startAgentRun.isPending ? "Starting Run..." : "Trigger Supervisor Pipeline"}
                </Button>

                {startAgentRun.isSuccess && startAgentRun.data && (
                  <Alert className="border-green-500 bg-green-500/5">
                    <ShieldCheck className="h-5 w-5 text-green-500" />
                    <AlertTitle>Workflow Activated</AlertTitle>
                    <AlertDescription className="text-xs space-y-1 font-mono">
                      <div>Run ID: {startAgentRun.data.run_id}</div>
                      <div>Thread ID: {startAgentRun.data.thread_id}</div>
                      <div>Status: {startAgentRun.data.status}</div>
                      <div>Message: {startAgentRun.data.message}</div>
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
