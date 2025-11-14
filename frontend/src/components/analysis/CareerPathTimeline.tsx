"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { TrendingUp, ArrowRight } from "lucide-react";
import { useCareerPath } from "@/hooks/queries/useAnalysis";

interface CareerPathTimelineProps {
  userId: string | null;
}

export default function CareerPathTimeline({
  userId,
}: CareerPathTimelineProps) {
  const { data, isLoading, error } = useCareerPath(userId);

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
        <CardContent className="pt-6">
          <p className="text-sm text-destructive">Failed to load career path</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Career Path Recommendations
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Current Focus */}
        <div>
          <h3 className="text-sm font-medium text-muted-foreground mb-2">
            Current Focus
          </h3>
          <Badge variant="secondary" className="text-base px-4 py-2">
            {data.current_focus}
          </Badge>
        </div>

        {/* Career Paths */}
        {data.career_paths && data.career_paths.length > 0 && (
          <div>
            <h3 className="text-lg font-semibold mb-4">Recommended Career Paths</h3>
            <div className="space-y-4">
              {data.career_paths.map((path, idx) => (
                <div key={idx} className="relative pl-6">
                  <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-primary" />
                  <div className="absolute left-0 top-2 w-3 h-3 rounded-full bg-primary -translate-x-1.5" />
                  <Card className="ml-4 hover:shadow-md transition-shadow">
                    <CardContent className="pt-6">
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-semibold text-lg">{path.title}</h4>
                        <Badge variant="outline" className="text-xs">
                          {path.timeline}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-3">
                        {path.description}
                      </p>
                      {path.required_skills && path.required_skills.length > 0 && (
                        <div>
                          <p className="text-xs font-medium text-muted-foreground mb-2">
                            Required Skills:
                          </p>
                          <div className="flex flex-wrap gap-1">
                            {path.required_skills.map((skill, skillIdx) => (
                              <Badge
                                key={skillIdx}
                                variant="secondary"
                                className="text-xs"
                              >
                                {skill}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              ))}
            </div>
          </div>
        )}

        <Separator />

        {/* Next Steps */}
        {data.next_steps && data.next_steps.length > 0 && (
          <div>
            <h3 className="text-lg font-semibold mb-3">Next Steps</h3>
            <ul className="space-y-2">
              {data.next_steps.map((step, idx) => (
                <li
                  key={idx}
                  className="flex items-start gap-2 text-sm"
                >
                  <ArrowRight className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                  <span>{step}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
