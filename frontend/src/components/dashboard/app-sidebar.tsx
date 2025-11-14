"use client";

import * as React from "react";
import {
  LayoutDashboard,
  Code,
  Briefcase,
  TrendingUp,
  MessageSquare,
  FileText,
  Settings,
  HelpCircle,
  ArrowUpCircle,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NavDocuments } from "@/components/nav-documents";
import { NavMain } from "@/components/nav-main";
import { NavSecondary } from "@/components/nav-secondary";
import { NavUser } from "@/components/nav-user";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";

const navMain = [
  {
    title: "Overview",
    url: "/dashboard/overview",
    icon: LayoutDashboard,
  },
  {
    title: "Skills",
    url: "/dashboard/skills",
    icon: Code,
  },
  {
    title: "Jobs",
    url: "/dashboard/jobs",
    icon: Briefcase,
  },
  {
    title: "Career",
    url: "/dashboard/career",
    icon: TrendingUp,
  },
  {
    title: "Interview",
    url: "/dashboard/interview",
    icon: MessageSquare,
  },
  {
    title: "Chat",
    url: "/dashboard/chat",
    icon: MessageSquare,
  },
];

const documents = [
  {
    name: "Resume Analysis",
    url: "/dashboard/overview",
    icon: FileText,
  },
  {
    name: "Skills Report",
    url: "/dashboard/skills",
    icon: Code,
  },
  {
    name: "Career Insights",
    url: "/dashboard/career",
    icon: TrendingUp,
  },
];

const navSecondary = [
  {
    title: "Settings",
    url: "/dashboard/settings",
    icon: Settings,
  },
  {
    title: "Get Help",
    url: "/help",
    icon: HelpCircle,
  },
];

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname();
  const userId = typeof window !== "undefined" 
    ? localStorage.getItem("cp_user_id") 
    : null;

  // Fetch user profile for name and avatar
  const { data: profile } = useQuery({
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

  const userName = profile?.name || "User";
  const userEmail = profile?.email || "user@example.com";
  const userInitials = userName
    .split(" ")
    .map((n: string) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  const user = {
    name: userName,
    email: userEmail,
    avatar: `https://api.dicebear.com/7.x/initials/svg?seed=${userName}`,
  };

  return (
    <Sidebar collapsible="offcanvas" variant="inset" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              className="data-[slot=sidebar-menu-button]:!p-1.5"
            >
              <Link href="/dashboard/overview">
                <ArrowUpCircle className="h-5 w-5" />
                <span className="text-base font-semibold">CareerPilot</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={navMain} pathname={pathname} />
        <NavDocuments items={documents} />
        <NavSecondary items={navSecondary} className="mt-auto" />
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={user} />
      </SidebarFooter>
    </Sidebar>
  );
}
