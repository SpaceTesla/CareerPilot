"use client";

import * as React from "react";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Upload, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import ExportButton from "@/components/analysis/ExportButton";
import { useAnalysisOverview, useATSScore } from "@/hooks/queries/useAnalysis";
import { Skeleton } from "@/components/ui/skeleton";

export function DashboardHeader() {
  const pathname = usePathname();
  const userId = typeof window !== "undefined" 
    ? localStorage.getItem("cp_user_id") 
    : null;

  // Fetch user profile for name
  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ["resume", "profile", userId],
    queryFn: () => {
      if (!userId) return null;
      const profileId = localStorage.getItem("cp_profile_id");
      if (profileId) {
        return apiRequest(`/resume/${profileId}`);
      }
      return apiRequest(`/resume/user/${userId}`);
    },
    enabled: !!userId,
  });

  const { data: overview } = useAnalysisOverview(userId);
  const { data: atsData } = useATSScore(userId);

  const userName = profile?.name || "User";
  const userInitials = userName
    .split(" ")
    .map((n: string) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  const resumeScore = overview?.overall_score || 0;
  const atsScore = atsData?.ats_score || 0;
  const skillsCount = overview?.section_analysis?.skills?.total_skills || 0;

  // Get page title from pathname
  const getPageTitle = () => {
    if (pathname?.includes("/overview")) return "Overview";
    if (pathname?.includes("/skills")) return "Skills";
    if (pathname?.includes("/jobs")) return "Jobs";
    if (pathname?.includes("/career")) return "Career";
    if (pathname?.includes("/interview")) return "Interview";
    if (pathname?.includes("/chat")) return "Chat";
    return "Dashboard";
  };

  return (
    <header className="group-has-data-[collapsible=icon]/sidebar-wrapper:h-12 flex h-12 shrink-0 items-center gap-2 border-b transition-[width,height] ease-linear">
      <div className="flex w-full items-center gap-1 px-4 lg:gap-2 lg:px-6">
        <SidebarTrigger className="-ml-1" />
        <Separator
          orientation="vertical"
          className="mx-2 data-[orientation=vertical]:h-4"
        />
        <h1 className="text-base font-medium flex-1">{getPageTitle()}</h1>
        
        {/* Quick Stats - Right side */}
        <div className="hidden lg:flex items-center gap-2 flex-shrink-0">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-muted/80">
            <span className="text-xs text-muted-foreground whitespace-nowrap">Resume</span>
            <Badge variant="secondary" className="text-xs font-semibold px-1.5 py-0">
              {Math.round(resumeScore)}
            </Badge>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-muted/80">
            <span className="text-xs text-muted-foreground whitespace-nowrap">ATS</span>
            <Badge variant="secondary" className="text-xs font-semibold px-1.5 py-0">
              {Math.round(atsScore)}
            </Badge>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-muted/80">
            <span className="text-xs text-muted-foreground whitespace-nowrap">Skills</span>
            <Badge variant="secondary" className="text-xs font-semibold px-1.5 py-0">
              {skillsCount}
            </Badge>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {overview && (
            <ExportButton
              analysisData={overview}
              profileName={userName}
            />
          )}
          <Button variant="outline" size="sm" asChild className="hidden sm:flex">
            <Link href="/">
              <Upload className="mr-2 h-4 w-4" />
              <span>Upload</span>
            </Link>
          </Button>
          <Button variant="outline" size="icon" asChild className="sm:hidden">
            <Link href="/">
              <Upload className="h-4 w-4" />
            </Link>
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full">
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="text-xs">{userInitials}</AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">{userName}</p>
                  <p className="text-xs leading-none text-muted-foreground">
                    {profile?.email || "No email"}
                  </p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link href="/">
                  <Upload className="mr-2 h-4 w-4" />
                  Upload New Resume
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href="/dashboard/settings">
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                </Link>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
