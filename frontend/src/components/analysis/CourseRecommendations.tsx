"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ExternalLink, BookOpen } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";

interface CourseRecommendationsProps {
  userId: string | null;
}

interface CourseRecommendation {
  title: string;
  url: string;
  description: string;
  provider?: string;
}

export default function CourseRecommendations({
  userId,
}: CourseRecommendationsProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["courses", "recommendations", userId],
    queryFn: () => apiRequest(`/courses/recommendations?user_id=${userId}&limit=10`),
    enabled: !!userId,
  });

  const courses = (data?.courses as CourseRecommendation[]) || [];

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BookOpen className="h-5 w-5" />
          Course Recommendations
        </CardTitle>
      </CardHeader>
      <CardContent>
        {courses.length > 0 ? (
          <div className="space-y-4">
            {courses.map((course, idx) => (
              <Card key={idx} className="hover:shadow-md transition-shadow">
                <CardContent className="pt-6">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <h3 className="font-semibold mb-1">{course.title}</h3>
                      {course.description && (
                        <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
                          {course.description}
                        </p>
                      )}
                      {course.provider && (
                        <Badge variant="outline" className="text-xs">
                          {course.provider}
                        </Badge>
                      )}
                    </div>
                    {course.url && (
                      <Button variant="outline" size="sm" asChild>
                        <a
                          href={course.url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <ExternalLink className="h-4 w-4 mr-2" />
                          View
                        </a>
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <BookOpen className="mx-auto h-12 w-12 text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">
              No course recommendations available. Try asking the chat agent for
              course suggestions.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
