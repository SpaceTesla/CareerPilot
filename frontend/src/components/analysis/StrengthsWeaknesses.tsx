"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import type { AnalysisOverview } from "@/types/analysis";

interface StrengthsWeaknessesProps {
  data: AnalysisOverview | null;
}

export default function StrengthsWeaknesses({
  data,
}: StrengthsWeaknessesProps) {
  if (!data) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5" />
          Strengths & Weaknesses
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Strengths */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              <h3 className="font-semibold text-green-700 dark:text-green-400">
                Strengths
              </h3>
            </div>
            {data.strengths && data.strengths.length > 0 ? (
              <div className="space-y-2">
                {data.strengths.map((strength, idx) => (
                  <Alert key={idx} className="border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-950/20">
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    <AlertDescription className="text-sm">
                      {strength}
                    </AlertDescription>
                  </Alert>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No strengths identified yet.
              </p>
            )}
          </div>

          {/* Weaknesses */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <XCircle className="h-5 w-5 text-red-600" />
              <h3 className="font-semibold text-red-700 dark:text-red-400">
                Areas for Improvement
              </h3>
            </div>
            {data.weaknesses && data.weaknesses.length > 0 ? (
              <div className="space-y-2">
                {data.weaknesses.map((weakness, idx) => (
                  <Alert
                    key={idx}
                    variant="destructive"
                    className="border-red-200 bg-red-50/50 dark:border-red-800 dark:bg-red-950/20"
                  >
                    <XCircle className="h-4 w-4" />
                    <AlertDescription className="text-sm">
                      {weakness}
                    </AlertDescription>
                  </Alert>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No areas for improvement identified.
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
