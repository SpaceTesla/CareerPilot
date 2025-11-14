"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import type { AnalysisOverview } from "@/types/analysis";

interface ActionItemsChecklistProps {
  data: AnalysisOverview | null;
}

export default function ActionItemsChecklist({
  data,
}: ActionItemsChecklistProps) {
  if (!data || !data.improvements) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-32" />
        </CardContent>
      </Card>
    );
  }

  const priorityItems = data.improvements.priority_improvements || [];
  const optionalItems = data.improvements.optional_enhancements || [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CheckCircle2 className="h-5 w-5" />
          Action Items Checklist
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Priority Items */}
          {priorityItems.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <AlertCircle className="h-4 w-4 text-red-600" />
                <h3 className="font-semibold text-red-700 dark:text-red-400">
                  Priority Improvements
                </h3>
              </div>
              <div className="space-y-3">
                {priorityItems.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-3 p-3 bg-red-50 dark:bg-red-950/20 rounded-lg border border-red-200 dark:border-red-800"
                  >
                    <Checkbox className="mt-1" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-medium text-sm">{item.section}</p>
                        <Badge variant="destructive" className="text-xs">
                          High
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-1">
                        {item.suggestion}
                      </p>
                      <p className="text-xs text-red-600 dark:text-red-400">
                        {item.impact}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Optional Items */}
          {optionalItems.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="h-4 w-4 text-blue-600" />
                <h3 className="font-semibold text-blue-700 dark:text-blue-400">
                  Optional Enhancements
                </h3>
              </div>
              <div className="space-y-2">
                {optionalItems.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-3 p-3 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-800"
                  >
                    <Checkbox className="mt-1" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-medium text-sm">{item.section}</p>
                        <Badge variant="secondary" className="text-xs">
                          Medium
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-1">
                        {item.suggestion}
                      </p>
                      <p className="text-xs text-blue-600 dark:text-blue-400">
                        {item.impact}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {priorityItems.length === 0 && optionalItems.length === 0 && (
            <div className="text-center py-8">
              <CheckCircle2 className="mx-auto h-12 w-12 text-green-500 mb-2" />
              <p className="text-muted-foreground">
                No action items at this time. Great job!
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
