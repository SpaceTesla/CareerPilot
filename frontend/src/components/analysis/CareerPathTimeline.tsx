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
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-muted-foreground">
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
                <div key={idx} className="relative pl-8">
                  <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-primary/20" />
                  <div className="absolute left-0 top-3 w-4 h-4 rounded-full bg-primary border-2 border-background -translate-x-2.5 z-10" />
                  <Card className="ml-6 hover:shadow-md transition-all duration-200 border-l-4 border-l-primary/50">
                    <CardContent className="pt-6">
                      <div className="flex items-start justify-between mb-3">
                        <h4 className="font-semibold text-lg">{path.title}</h4>
                        <Badge variant="outline" className="text-xs shrink-0">
                          {path.timeline}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
                        {path.description}
                      </p>
                      {path.required_skills && path.required_skills.length > 0 && (
                        <div className="space-y-2">
                          <p className="text-xs font-medium text-muted-foreground">
                            Required Skills:
                          </p>
                          <div className="flex flex-wrap gap-2">
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
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">Next Steps</h3>
            <ul className="space-y-3">
              {data.next_steps.map((step, idx) => (
                <li
                  key={idx}
                  className="flex items-start gap-3 text-sm"
                >
                  <ArrowRight className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                  <span className="leading-relaxed">{step}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
