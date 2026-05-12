"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { TrendingUp, FileText, Info } from "lucide-react";

interface SessionTrend {
  session_id: string;
  session_name: string;
  profile_id: string;
  overall_score: number;
  grade: string;
  created_at: string | null;
  is_active: boolean;
}

interface SessionTrendsResponse {
  user_id: string;
  has_multiple_sessions: boolean;
  trends: SessionTrend[];
  total_sessions: number;
}

interface ProgressChartProps {
  userId: string | null;
}

export default function ProgressChart({ userId }: ProgressChartProps) {
  const { data, isLoading, error } = useQuery<SessionTrendsResponse>({
    queryKey: ["sessions", "scores", "trends", userId],
    queryFn: () => apiRequest<SessionTrendsResponse>(`/sessions/scores/trends?user_id=${userId}`),
    enabled: !!userId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-64" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Score Trends Over Time
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-8">
            Unable to load score trends. Please try again later.
          </p>
        </CardContent>
      </Card>
    );
  }

  // If only one session, show a message
  if (!data.has_multiple_sessions || data.trends.length < 2) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Score Trends Over Time
          </CardTitle>
          <CardDescription>
            Track your resume improvement across multiple uploads
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <FileText className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground mb-2">
              Upload more resume versions to see your progress over time
            </p>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Info className="h-4 w-4" />
              <span>Each resume upload creates a new session you can compare</span>
            </div>
            {data.trends.length === 1 && (
              <Badge variant="outline" className="mt-4">
                Current Score: {Math.round(data.trends[0].overall_score)}
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Transform data for the chart
  const chartData = data.trends.map((trend, index) => ({
    name: trend.session_name.length > 15 
      ? trend.session_name.substring(0, 15) + "..." 
      : trend.session_name,
    fullName: trend.session_name,
    score: Math.round(trend.overall_score),
    grade: trend.grade,
    date: trend.created_at 
      ? new Date(trend.created_at).toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        })
      : `Session ${index + 1}`,
    isActive: trend.is_active,
  }));

  // Calculate improvement
  const firstScore = chartData[0]?.score || 0;
  const lastScore = chartData[chartData.length - 1]?.score || 0;
  const improvement = lastScore - firstScore;

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ payload: typeof chartData[0] }> }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-background border rounded-lg shadow-lg p-3">
          <p className="font-medium">{data.fullName}</p>
          <p className="text-sm text-muted-foreground">{data.date}</p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-lg font-bold">{data.score}</span>
            <Badge variant={data.grade === "A" ? "default" : "secondary"}>
              {data.grade}
            </Badge>
            {data.isActive && (
              <Badge variant="outline" className="text-xs">Current</Badge>
            )}
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Score Trends Over Time
            </CardTitle>
            <CardDescription>
              Comparing {data.total_sessions} resume versions
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {improvement !== 0 && (
              <Badge variant={improvement > 0 ? "default" : "destructive"}>
                {improvement > 0 ? "+" : ""}{improvement} pts
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="opacity-50" />
            <XAxis 
              dataKey="date" 
              tick={{ fontSize: 12 }}
              tickLine={false}
            />
            <YAxis 
              domain={[0, 100]} 
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <ReferenceLine y={70} stroke="#22c55e" strokeDasharray="5 5" label={{ value: "Good", position: "right", fontSize: 10 }} />
            <Line
              type="monotone"
              dataKey="score"
              stroke="#3b82f6"
              strokeWidth={3}
              name="Resume Score"
              dot={{ r: 6, fill: "#3b82f6", strokeWidth: 2, stroke: "#fff" }}
              activeDot={{ r: 8, fill: "#2563eb" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

