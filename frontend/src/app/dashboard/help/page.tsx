"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  HelpCircle, 
  BookOpen, 
  Bot, 
  Brain, 
  Activity, 
  Key, 
  ShieldAlert, 
  TrendingUp, 
  ChevronRight, 
  Cookie,
  Sliders
} from "lucide-react";
import { motion } from "framer-motion";
import Link from "next/link";

export default function HelpPage() {
  const faqSections = [
    {
      title: "Core Platform Concepts",
      icon: <BookOpen className="h-5 w-5 text-primary" />,
      items: [
        {
          q: "What is the Career Health Score?",
          a: "The Career Health Score is a composite metric (0-100) calculated across five dimensions: skill alignment with target roles, market positioning, job search activity, compensation alignment, and profile completeness. It updates weekly or whenever you upload a new resume.",
        },
        {
          q: "How does the Position Delta Engine work?",
          a: "The Position Delta comparison engine checks your active skill inventory against the target roles set in your goals. It utilizes the Neo4j Knowledge Graph to traverse adjacencies, highlighting missing skills and recommending the top 3 gaps you should prioritize.",
        },
      ],
    },
    {
      title: "Automated Execution & HITL",
      icon: <Bot className="h-5 w-5 text-primary" />,
      items: [
        {
          q: "How do I configure Auto-Fill for job portals?",
          a: "Auto-Fill relies on logged-in sessions. To set it up: 1) Install a cookie editor browser extension (e.g. Cookie-Editor). 2) Log in to the job board (LinkedIn, Indeed). 3) Export cookies as JSON. 4) Go to the Applications tab in CareerPilot and paste the JSON in the 'Portal Sessions' panel.",
        },
        {
          q: "What is Human-in-the-Loop (HITL) review?",
          a: "For privacy and safety, CareerPilot pauses automation workflows before sensitive actions (like submitting form applications). These actions generate a request visible on the 'Agent Approvals' page, where you can inspect, modify, or approve the action.",
        },
        {
          q: "What are Playwright Fallback steps?",
          a: "If a job board lacks structured API support, the Execution Engine falls back to Playwright browser automation. It launches a virtual browser, fills the fields dynamically, takes a screenshot of the filled page, and awaits your approval before submission.",
        },
      ],
    },
    {
      title: "ML Calibration & Benchmarking",
      icon: <Sliders className="h-5 w-5 text-primary" />,
      items: [
        {
          q: "How does Peer Cohort Benchmarking place me?",
          a: "Using K-Means clustering, the Calibration service groups user profiles into cohorts based on skills and experience. It benchmarks your overall fit and compensation targets against peers, rendering your percentile statistics on the Calibration dashboard.",
        },
        {
          q: "What is the ML Registry Promotion model?",
          a: "Model predictions (like predicted opportunity fit probabilities) are calibrated using versioned machine learning estimators. In the Calibration panel, administrators can promote candidate models from Staging to Production after auditing MSE (Mean Squared Error) improvements.",
        },
      ],
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <HelpCircle className="h-8 w-8 text-primary" />
          Help Center
        </h1>
        <p className="text-muted-foreground">
          Find answers to frequently asked questions about AI agents, workflow executions, and career models.
        </p>
      </div>

      {/* Quick Start Setup Card */}
      <Card className="bg-gradient-to-br from-primary/5 via-transparent to-transparent border-primary/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Key className="h-5 w-5 text-primary" />
            Quick Setup: Enable Auto-Fill & Automation
          </CardTitle>
          <CardDescription>Follow these 3 steps to configure your automated execution sessions.</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-2">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Badge variant="default" className="rounded-full h-6 w-6 p-0 flex items-center justify-center font-bold">1</Badge>
              <span className="font-semibold text-sm">Export Browser Cookies</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Install a cookie editor extension, log in to LinkedIn or Indeed, and click export to copy your session cookies as JSON.
            </p>
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Badge variant="default" className="rounded-full h-6 w-6 p-0 flex items-center justify-center font-bold">2</Badge>
              <span className="font-semibold text-sm">Import into Portal Sessions</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Navigate to the{" "}
              <Link href="/dashboard/applications" className="underline text-primary font-medium">
                Applications Page
              </Link>
              , select your portal, paste the JSON array, and click import.
            </p>
          </div>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Badge variant="default" className="rounded-full h-6 w-6 p-0 flex items-center justify-center font-bold">3</Badge>
              <span className="font-semibold text-sm">Review & Approve Actions</span>
            </div>
            <p className="text-xs text-muted-foreground">
              When triggering recommendations, check the{" "}
              <Link href="/dashboard/approvals" className="underline text-primary font-medium">
                Agent Approvals Page
              </Link>
              {" "}to approve or edit filled forms before they submit.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* FAQ Sections */}
      <div className="space-y-6">
        <h2 className="text-xl font-bold tracking-tight flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-muted-foreground" />
          Frequently Asked Questions
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {faqSections.map((section, idx) => (
            <Card key={idx} className="h-fit">
              <CardHeader className="flex flex-row items-center gap-2.5 pb-3">
                {section.icon}
                <CardTitle className="text-base font-bold">{section.title}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {section.items.map((item, itemIdx) => (
                  <div key={itemIdx} className="space-y-1.5 border-b last:border-b-0 pb-3 last:pb-0">
                    <h4 className="font-semibold text-sm text-foreground flex items-start gap-1.5">
                      <span className="text-primary mt-0.5">Q:</span>
                      {item.q}
                    </h4>
                    <p className="text-xs text-muted-foreground leading-relaxed pl-5">
                      {item.a}
                    </p>
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
