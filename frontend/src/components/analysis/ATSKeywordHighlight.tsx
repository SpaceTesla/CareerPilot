"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useKeywords } from "@/hooks/queries/useJobs";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { CheckCircle2, XCircle, Info } from "lucide-react";
import { cn } from "@/lib/utils";

interface ATSKeywordHighlightProps {
  userId: string | null;
  targetRole?: string;
}

export default function ATSKeywordHighlight({
  userId,
  targetRole,
}: ATSKeywordHighlightProps) {
  const { data: keywords, isLoading: keywordsLoading } = useKeywords(
    userId,
    targetRole
  );

  // Get profile_id from localStorage, fallback to user_id endpoint
  const profileId = typeof window !== "undefined" 
    ? localStorage.getItem("cp_profile_id") 
    : null;

  const { data: resumeData } = useQuery({
    queryKey: ["resume", "profile", profileId || userId],
    queryFn: () => {
      if (profileId) {
        return apiRequest(`/resume/${profileId}`);
      } else if (userId) {
        return apiRequest(`/resume/user/${userId}`);
      }
      throw new Error("No profile_id or user_id available");
    },
    enabled: !!(profileId || userId),
  });

  if (keywordsLoading) {
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

  if (!keywords) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">
            No keyword data available
          </p>
        </CardContent>
      </Card>
    );
  }

  // Extract all text from resume for keyword checking
  const resumeText = resumeData
    ? JSON.stringify(resumeData).toLowerCase()
    : "";

  const checkKeywordPresent = (keyword: string) => {
    return resumeText.includes(keyword.toLowerCase());
  };

  const missingTechnical = keywords.missing_technical || [];
  const missingCommon = keywords.missing_common || [];
  const recommended = keywords.recommended_keywords || [];

  // Calculate keyword density
  const totalKeywords = recommended.length;
  const presentKeywords = recommended.filter(checkKeywordPresent).length;
  const keywordDensity = totalKeywords > 0 ? (presentKeywords / totalKeywords) * 100 : 0;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>ATS Keyword Analysis</CardTitle>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <Info className="h-4 w-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent>
                <p className="max-w-xs">
                  Keywords help ATS systems match your resume to job descriptions.
                  Include relevant keywords from your target role.
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Keyword Density */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Keyword Coverage</span>
            <span className="text-sm font-semibold">
              {Math.round(keywordDensity)}%
            </span>
          </div>
          <Progress value={keywordDensity} className="h-2" />
        </div>

        {/* Present Keywords */}
        {recommended.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              Keywords Found in Resume
            </h3>
            <div className="flex flex-wrap gap-2">
              {recommended
                .filter(checkKeywordPresent)
                .slice(0, 10)
                .map((keyword, idx) => (
                  <Badge
                    key={idx}
                    variant="outline"
                    className="bg-green-50 text-green-700 border-green-200 dark:bg-green-950/20 dark:text-green-400"
                  >
                    {keyword}
                  </Badge>
                ))}
            </div>
          </div>
        )}

        {/* Missing Technical Keywords */}
        {missingTechnical.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <XCircle className="h-4 w-4 text-red-600" />
              Missing Technical Keywords
            </h3>
            <div className="flex flex-wrap gap-2">
              {missingTechnical.slice(0, 10).map((keyword, idx) => (
                <Badge key={idx} variant="destructive" className="text-xs">
                  {keyword}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Missing Common Keywords */}
        {missingCommon.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
              <XCircle className="h-4 w-4 text-yellow-600" />
              Missing Common Keywords
            </h3>
            <div className="flex flex-wrap gap-2">
              {missingCommon.map((keyword, idx) => (
                <Badge
                  key={idx}
                  variant="outline"
                  className="bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-950/20 dark:text-yellow-400 text-xs"
                >
                  {keyword}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Recommendations */}
        <div>
          <h3 className="text-sm font-semibold mb-2">Recommendations</h3>
          <ul className="space-y-1 text-sm text-muted-foreground">
            <li>• Add missing technical keywords to your skills section</li>
            <li>• Include common industry terms in your experience descriptions</li>
            <li>• Use keywords naturally - avoid keyword stuffing</li>
            <li>• Match keywords from job descriptions you're targeting</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}

