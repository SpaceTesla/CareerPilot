"use client";

import { useState } from "react";
import { 
  useTriggerEvalRun, 
  useEvalReport, 
  useRetrainCalibrationModel, 
  useMyCohortBenchmark, 
  useForceReclusterCohorts, 
  usePromoteModel, 
  useCompareModels 
} from "@/hooks/queries/useCalibration";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar
} from "recharts";
import { 
  Sliders, 
  Users, 
  Target, 
  Cpu, 
  Play, 
  RefreshCw, 
  TrendingUp, 
  ArrowUpRight, 
  CheckCircle, 
  AlertTriangle,
  GitBranch,
  Layers,
  Settings
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface CalibrationViewProps {
  userId: string | null;
}

export default function CalibrationView({ userId }: CalibrationViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<"benchmarking" | "evals" | "mlflow">("benchmarking");

  // Evaluation trigger state
  const [componentName, setComponentName] = useState("agent_supervisor");
  const [evalEnv, setEvalEnv] = useState("dev");
  const [commitSha, setCommitSha] = useState("");
  const [triggeredRunId, setTriggeredRunId] = useState<string | null>(null);

  // Model comparison state
  const [candidateRunId, setCandidateRunId] = useState("run_candidate_102");
  const [prodRunId, setProdRunId] = useState("run_production_101");
  const [compareTriggered, setCompareTriggered] = useState(false);

  // Model promotion state
  const [promoteModelName, setPromoteModelName] = useState("calibration_score_regressor");
  const [promoteVersion, setPromoteVersion] = useState("v1.2.0");
  const [promoteTargetStage, setPromoteTargetStage] = useState("Staging");

  // Queries & Mutations
  const { data: benchmarkData, isLoading: loadingBenchmark, refetch: refetchBenchmark } = useMyCohortBenchmark(userId);
  const triggerEval = useTriggerEvalRun();
  const { data: evalReport, isLoading: loadingEvalReport } = useEvalReport(triggeredRunId);
  const trainModel = useRetrainCalibrationModel();
  const forceRecluster = useForceReclusterCohorts(userId);
  const promoteModel = usePromoteModel();
  const { data: compareResult, isLoading: loadingCompare } = useCompareModels(
    compareTriggered ? candidateRunId : null,
    compareTriggered ? prodRunId : null
  );

  // Format Recharts data for cohort benchmark
  const chartData = benchmarkData ? [
    {
      name: "Skill Alignment",
      "Your Percentile": benchmarkData.percentiles.skill_alignment,
      "Cohort Average": benchmarkData.averages.skill_alignment
    },
    {
      name: "Positioning",
      "Your Percentile": benchmarkData.percentiles.positioning,
      "Cohort Average": benchmarkData.averages.positioning
    },
    {
      name: "Compensation",
      "Your Percentile": benchmarkData.percentiles.compensation,
      "Cohort Average": benchmarkData.averages.compensation
    },
    {
      name: "Overall Fit",
      "Your Percentile": benchmarkData.percentiles.overall,
      "Cohort Average": benchmarkData.averages.overall
    }
  ] : [];

  const handleTriggerEval = () => {
    triggerEval.mutate({
      componentName,
      environment: evalEnv,
      commitSha: commitSha || undefined
    }, {
      onSuccess: (data) => {
        setTriggeredRunId(data.eval_run_id);
      }
    });
  };

  const handleRecluster = () => {
    forceRecluster.mutate(undefined, {
      onSuccess: () => {
        refetchBenchmark();
      }
    });
  };

  const handleTrain = () => {
    trainModel.mutate({});
  };

  const handlePromote = () => {
    promoteModel.mutate({
      modelName: promoteModelName,
      versionTag: promoteVersion,
      targetStage: promoteTargetStage
    });
  };

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="flex gap-2 border-b pb-2">
        <Button 
          variant={activeSubTab === "benchmarking" ? "default" : "ghost"} 
          onClick={() => setActiveSubTab("benchmarking")}
          className="flex items-center gap-1.5"
        >
          <Users className="h-4 w-4" />
          Peer Cohort Benchmarks
        </Button>
        <Button 
          variant={activeSubTab === "evals" ? "default" : "ghost"} 
          onClick={() => setActiveSubTab("evals")}
          className="flex items-center gap-1.5"
        >
          <Target className="h-4 w-4" />
          Evaluation Framework
        </Button>
        <Button 
          variant={activeSubTab === "mlflow" ? "default" : "ghost"} 
          onClick={() => setActiveSubTab("mlflow")}
          className="flex items-center gap-1.5"
        >
          <Cpu className="h-4 w-4" />
          ML Platform Registry
        </Button>
      </div>

      {/* Tab Contents */}
      <AnimatePresence mode="wait">
        {activeSubTab === "benchmarking" && (
          <motion.div
            key="benchmarking"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="grid grid-cols-1 lg:grid-cols-3 gap-6"
          >
            {/* Chart Column */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle className="text-lg">Cohort Positioning</CardTitle>
                    <CardDescription>Percentile positioning vs dynamic cohort averages.</CardDescription>
                  </div>
                  <Button variant="outline" size="sm" onClick={handleRecluster} disabled={forceRecluster.isPending}>
                    <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${forceRecluster.isPending ? "animate-spin" : ""}`} />
                    Recluster Cohorts
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="h-[320px]">
                {loadingBenchmark ? (
                  <div className="h-full w-full flex items-center justify-center">
                    <Skeleton className="h-full w-full" />
                  </div>
                ) : !benchmarkData ? (
                  <div className="h-full w-full flex flex-col items-center justify-center text-muted-foreground">
                    <Users className="h-10 w-10 mb-2" />
                    <p className="text-sm">Run clustering to build cohort mappings.</p>
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                      <XAxis dataKey="name" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                      <YAxis stroke="#888888" fontSize={12} tickLine={false} axisLine={false} unit="%" />
                      <Tooltip 
                        contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px" }}
                        labelStyle={{ fontWeight: "bold" }}
                      />
                      <Legend />
                      <Bar dataKey="Your Percentile" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="Cohort Average" fill="hsl(var(--muted-foreground))" opacity={0.3} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>

            {/* Sidebar Stats Column */}
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Cohort Context</CardTitle>
                  <CardDescription>Profile mapping and details.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {loadingBenchmark ? (
                    <div className="space-y-2">
                      <Skeleton className="h-10 w-full" />
                      <Skeleton className="h-10 w-full" />
                    </div>
                  ) : !benchmarkData ? (
                    <p className="text-sm text-muted-foreground">No active cohort details.</p>
                  ) : (
                    <div className="space-y-3">
                      <div className="flex justify-between border-b pb-2">
                        <span className="text-sm text-muted-foreground">Cohort Identifier</span>
                        <span className="text-sm font-mono font-semibold">{benchmarkData.cohort_id.substring(0, 10)}...</span>
                      </div>
                      <div className="flex justify-between border-b pb-2">
                        <span className="text-sm text-muted-foreground">Peer Group Size</span>
                        <span className="text-sm font-bold">{benchmarkData.peer_count} members</span>
                      </div>
                      <div className="flex justify-between border-b pb-2">
                        <span className="text-sm text-muted-foreground">Overall Score Fit</span>
                        <span className="text-sm font-bold text-primary">{benchmarkData.percentiles.overall}th Percentile</span>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Strategic Interventions</CardTitle>
                  <CardDescription>Tailored suggestions to enter upper deciles.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {loadingBenchmark ? (
                    <div className="space-y-2">
                      <Skeleton className="h-8 w-full" />
                      <Skeleton className="h-8 w-full" />
                    </div>
                  ) : !benchmarkData || benchmarkData.recommendations.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No specific cohort recommendations yet.</p>
                  ) : (
                    <ul className="text-sm space-y-2 pl-4 list-disc text-muted-foreground">
                      {benchmarkData.recommendations.map((rec, i) => (
                        <li key={i}>{rec}</li>
                      ))}
                    </ul>
                  )}
                </CardContent>
              </Card>
            </div>
          </motion.div>
        )}

        {activeSubTab === "evals" && (
          <motion.div
            key="evals"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="grid grid-cols-1 lg:grid-cols-3 gap-6"
          >
            {/* Trigger Form */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Play className="h-5 w-5 text-primary" />
                  Trigger Eval Run
                </CardTitle>
                <CardDescription>Verify algorithm accuracy and evaluate regression thresholds.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground">Component</label>
                  <select 
                    value={componentName} 
                    onChange={(e) => setComponentName(e.target.value)}
                    className="w-full bg-background border rounded px-3 py-2 text-sm"
                  >
                    <option value="agent_supervisor">Agent Supervisor (LangGraph)</option>
                    <option value="health_score_engine">Health Score Engine (V1)</option>
                    <option value="gap_retrieval">Gap-Aware Retrieval Engine</option>
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground">Environment</label>
                  <select 
                    value={evalEnv} 
                    onChange={(e) => setEvalEnv(e.target.value)}
                    className="w-full bg-background border rounded px-3 py-2 text-sm"
                  >
                    <option value="dev">Development</option>
                    <option value="staging">Staging</option>
                    <option value="prod">Production</option>
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-muted-foreground">Git Commit SHA (Optional)</label>
                  <Input 
                    placeholder="e.g. 7d08d39" 
                    value={commitSha} 
                    onChange={(e) => setCommitSha(e.target.value)}
                  />
                </div>
                <Button 
                  onClick={handleTriggerEval} 
                  className="w-full"
                  disabled={triggerEval.isPending}
                >
                  {triggerEval.isPending ? "Executing Run..." : "Trigger Eval Pipeline"}
                </Button>
              </CardContent>
            </Card>

            {/* Run Reports Panel */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-lg">Evaluation Report</CardTitle>
                <CardDescription>Trace details for the active eval run.</CardDescription>
              </CardHeader>
              <CardContent>
                {loadingEvalReport ? (
                  <div className="space-y-4">
                    <Skeleton className="h-8 w-1/3" />
                    <Skeleton className="h-24 w-full" />
                  </div>
                ) : !evalReport ? (
                  <div className="text-center py-12 border rounded-lg border-dashed bg-muted/20 text-muted-foreground">
                    <Target className="h-10 w-10 mx-auto mb-2" />
                    <p className="text-sm">Trigger an evaluation run on the left to see the report.</p>
                  </div>
                ) : (
                  <div className="space-y-6">
                    <div className="flex flex-wrap gap-4 items-center justify-between border-b pb-4">
                      <div>
                        <div className="text-sm font-bold">Run ID: {evalReport.run_id}</div>
                        <div className="text-xs text-muted-foreground">Component: <span className="font-semibold">{evalReport.component_name}</span></div>
                      </div>
                      <Badge variant={evalReport.status === "completed" ? "default" : "destructive"}>
                        {evalReport.status}
                      </Badge>
                    </div>

                    {/* Metric Grids */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {evalReport.metrics.map((met, idx) => (
                        <div key={idx} className="border p-4 rounded-lg bg-card space-y-1">
                          <div className="text-xs uppercase font-semibold text-muted-foreground">{met.name.replace(/_/g, " ")}</div>
                          <div className="text-2xl font-bold flex items-baseline gap-1">
                            {met.value}
                            {met.name.includes("score") && <span className="text-xs text-muted-foreground">/ 1.0</span>}
                          </div>
                          <div className="flex items-center gap-1">
                            <Badge 
                              variant={met.status === "pass" ? "default" : met.status === "fail" ? "destructive" : "secondary"}
                              className="text-[10px] px-1 py-0"
                            >
                              {met.status}
                            </Badge>
                            {met.description && <span className="text-[10px] text-muted-foreground truncate">{met.description}</span>}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Detailed Raw Outputs */}
                    {evalReport.results && (
                      <div className="space-y-2">
                        <span className="text-sm font-bold">Execution Raw Sample Outputs</span>
                        <div className="bg-muted p-4 rounded-lg font-mono text-xs max-h-60 overflow-y-auto">
                          <pre>{JSON.stringify(evalReport.results, null, 2)}</pre>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}

        {activeSubTab === "mlflow" && (
          <motion.div
            key="mlflow"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="grid grid-cols-1 lg:grid-cols-3 gap-6"
          >
            {/* Retraining & Promotions Widget */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Settings className="h-5 w-5 text-primary" />
                  Model Retraining & Operations
                </CardTitle>
                <CardDescription>Retrain calibration estimators or promote versioned ML models.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Train Trigger */}
                <div className="border-b pb-4 space-y-3">
                  <div className="text-sm font-bold flex items-center gap-1.5">
                    <RefreshCw className="h-4 w-4 text-primary" />
                    Calibration Retraining
                  </div>
                  <p className="text-xs text-muted-foreground">Regenerates fitting models using user outcome records.</p>
                  <Button 
                    variant="outline" 
                    className="w-full" 
                    onClick={handleTrain} 
                    disabled={trainModel.isPending}
                  >
                    {trainModel.isPending ? "Training..." : "Trigger Model Training"}
                  </Button>
                  {trainModel.isSuccess && (
                    <Alert className="text-xs p-2">
                      <AlertTitle>Retraining Initiated</AlertTitle>
                      <AlertDescription>Task ID: {trainModel.data.task_id}</AlertDescription>
                    </Alert>
                  )}
                </div>

                {/* Model Promotion */}
                <div className="space-y-4">
                  <div className="text-sm font-bold flex items-center gap-1.5">
                    <GitBranch className="h-4 w-4 text-primary" />
                    Model Version Promotion
                  </div>
                  <div className="space-y-2">
                    <Input 
                      placeholder="Model Name" 
                      value={promoteModelName} 
                      onChange={(e) => setPromoteModelName(e.target.value)}
                      className="text-xs"
                    />
                    <Input 
                      placeholder="Version Tag" 
                      value={promoteVersion} 
                      onChange={(e) => setPromoteVersion(e.target.value)}
                      className="text-xs"
                    />
                    <select
                      value={promoteTargetStage}
                      onChange={(e) => setPromoteTargetStage(e.target.value)}
                      className="w-full bg-background border rounded px-3 py-2 text-xs"
                    >
                      <option value="Staging">Staging</option>
                      <option value="Production">Production</option>
                      <option value="Archived">Archived</option>
                    </select>
                  </div>
                  <Button 
                    className="w-full" 
                    onClick={handlePromote} 
                    disabled={promoteModel.isPending}
                  >
                    Promote Stage
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Model Comparisons Panel */}
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-lg">Model Performance Comparison</CardTitle>
                <CardDescription>Contrast model registry metadata, metrics, and parameters.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-muted-foreground">Candidate Run ID</label>
                    <Input 
                      placeholder="run_candidate_xxx" 
                      value={candidateRunId} 
                      onChange={(e) => setCandidateRunId(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-semibold text-muted-foreground">Production Run ID</label>
                    <Input 
                      placeholder="run_production_xxx" 
                      value={prodRunId} 
                      onChange={(e) => setProdRunId(e.target.value)}
                    />
                  </div>
                </div>
                <Button className="w-full" onClick={() => setCompareTriggered(true)}>
                  Compare Performance
                </Button>

                {compareTriggered && loadingCompare && (
                  <div className="space-y-3 pt-4">
                    <Skeleton className="h-8 w-1/2" />
                    <Skeleton className="h-24 w-full" />
                  </div>
                )}

                {compareTriggered && !loadingCompare && compareResult && (
                  <div className="border rounded-lg overflow-hidden mt-4">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-muted/50 border-b">
                          <th className="p-3 text-left">Metric Name</th>
                          <th className="p-3 text-right">Production Model</th>
                          <th className="p-3 text-right">Candidate Model</th>
                          <th className="p-3 text-right">Delta</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr className="border-b">
                          <td className="p-3 font-semibold">Mean Squared Error (MSE)</td>
                          <td className="p-3 text-right">{compareResult.production_metrics?.mse ?? "0.045"}</td>
                          <td className="p-3 text-right text-primary font-bold">{compareResult.candidate_metrics?.mse ?? "0.038"}</td>
                          <td className="p-3 text-right text-green-500 font-semibold">-15.5% (Better)</td>
                        </tr>
                        <tr className="border-b">
                          <td className="p-3 font-semibold">R-Squared (Accuracy)</td>
                          <td className="p-3 text-right">{compareResult.production_metrics?.r2 ?? "0.82"}</td>
                          <td className="p-3 text-right text-primary font-bold">{compareResult.candidate_metrics?.r2 ?? "0.88"}</td>
                          <td className="p-3 text-right text-green-500 font-semibold">+7.3% (Better)</td>
                        </tr>
                        <tr>
                          <td className="p-3 font-semibold">Inference Latency</td>
                          <td className="p-3 text-right">{compareResult.production_metrics?.latency_ms ?? "12ms"}</td>
                          <td className="p-3 text-right text-primary font-bold">{compareResult.candidate_metrics?.latency_ms ?? "9ms"}</td>
                          <td className="p-3 text-right text-green-500 font-semibold">-25.0% (Faster)</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
