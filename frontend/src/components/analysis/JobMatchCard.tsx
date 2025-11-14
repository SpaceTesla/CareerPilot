"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Label } from "@/components/ui/label";
import { ExternalLink } from "lucide-react";
import { useJobMatch } from "@/hooks/queries/useAnalysis";
import { useJobRecommendations } from "@/hooks/queries/useJobs";
import { cn } from "@/lib/utils";

interface JobMatchCardProps {
  userId: string | null;
}

const commonRoles = [
  "Backend Developer",
  "Frontend Developer",
  "Full-Stack Developer",
  "DevOps Engineer",
  "Data Scientist",
];

export default function JobMatchCard({ userId }: JobMatchCardProps) {
  const [selectedRole, setSelectedRole] = useState<string>("");
  const { data: matchData, isLoading: matchLoading } = useJobMatch(
    userId,
    selectedRole || undefined
  );
  const { data: jobRecs, isLoading: jobsLoading } = useJobRecommendations(
    userId,
    5
  );

  return (
    <div className="space-y-6">
      {/* Job Match Score */}
      <Card>
        <CardHeader>
          <CardTitle>Job Match Score</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Role Selection */}
          <div className="space-y-3">
            <Label>Select Role</Label>
            <div className="flex flex-wrap gap-2">
              {commonRoles.map((role) => (
                <Button
                  key={role}
                  type="button"
                  variant={selectedRole === role ? "default" : "outline"}
                  size="sm"
                  onClick={() => setSelectedRole(role)}
                  className="transition-all"
                >
                  {role}
                </Button>
              ))}
            </div>
          </div>

          {matchLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-4 w-full" />
            </div>
          ) : matchData ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-lg font-semibold">Overall Match</span>
                <Badge
                  variant="outline"
                  className={cn(
                    "text-2xl font-bold px-4 py-1",
                    matchData.match_score >= 70
                      ? "text-green-600 border-green-600"
                      : matchData.match_score >= 50
                      ? "text-yellow-600 border-yellow-600"
                      : "text-red-600 border-red-600"
                  )}
                >
                  {matchData.match_score.toFixed(1)}%
                </Badge>
              </div>
              <Progress
                value={matchData.match_score}
                className={cn(
                  "h-3",
                  matchData.match_score >= 70
                    ? "[&>div]:bg-green-600"
                    : matchData.match_score >= 50
                    ? "[&>div]:bg-yellow-600"
                    : "[&>div]:bg-red-600"
                )}
              />

              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">
                    Skills Match
                  </p>
                  <p className="text-lg font-semibold">
                    {matchData.skills_match.toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">
                    Resume Quality
                  </p>
                  <p className="text-lg font-semibold">
                    {matchData.resume_quality.toFixed(1)}%
                  </p>
                </div>
              </div>

              {matchData.missing_skills &&
                matchData.missing_skills.length > 0 && (
                  <div>
                    <h3 className="text-sm font-medium mb-2">Missing Skills</h3>
                    <div className="flex flex-wrap gap-2">
                      {matchData.missing_skills.map((skill, idx) => (
                        <Badge
                          key={idx}
                          variant="destructive"
                          className="text-xs"
                        >
                          {skill}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              Select a role to see match score
            </p>
          )}
        </CardContent>
      </Card>

      {/* Job Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle>Job Recommendations</CardTitle>
        </CardHeader>
        <CardContent>
          {jobsLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-24 w-full" />
              ))}
            </div>
          ) : jobRecs && jobRecs.jobs && jobRecs.jobs.length > 0 ? (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Found {jobRecs.total_found} jobs matching your profile
              </p>
              {jobRecs.jobs.map((job, idx) => (
                <Card
                  key={idx}
                  className="hover:shadow-md transition-all duration-200 border-l-4 border-l-primary"
                >
                  <CardContent className="">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 space-y-3">
                        <div className="space-y-2">
                          <div className="flex items-start gap-3">
                            <h3 className="font-semibold text-lg leading-tight">
                              {job.title || "Job Opening"}
                            </h3>
                            {job.company && (
                              <Badge
                                variant="secondary"
                                className="text-xs shrink-0"
                              >
                                {job.company}
                              </Badge>
                            )}
                          </div>
                          {job.location && (
                            <p className="text-sm text-muted-foreground flex items-center gap-1">
                              <span className="text-destructive">📍</span>
                              {job.location}
                            </p>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {job.description ||
                            job.content ||
                            "View job details for more information."}
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {job.job_type && (
                            <Badge variant="outline" className="text-xs">
                              {job.job_type}
                            </Badge>
                          )}
                          {job.salary_min && job.salary_max && (
                            <Badge variant="outline" className="text-xs">
                              ${job.salary_min.toLocaleString()} - $
                              {job.salary_max.toLocaleString()}
                            </Badge>
                          )}
                          {job.source && (
                            <Badge variant="outline" className="text-xs">
                              via {job.source}
                            </Badge>
                          )}
                        </div>
                      </div>
                      <Button
                        variant="default"
                        size="sm"
                        className="shrink-0"
                        asChild
                      >
                        <a
                          href={job.url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <ExternalLink className="h-4 w-4 mr-2" />
                          Apply
                        </a>
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              No job recommendations available
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
