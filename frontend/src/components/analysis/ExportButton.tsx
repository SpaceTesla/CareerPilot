"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Download, FileText } from "lucide-react";
import { exportAnalysisReport, exportResumePDF } from "@/lib/pdf-export";
import type { AnalysisOverview } from "@/types/analysis";
import { toast } from "sonner";

interface ExportButtonProps {
  analysisData: AnalysisOverview | null;
  resumeData?: Record<string, unknown> | null;
  profileName?: string;
}

export default function ExportButton({
  analysisData,
  resumeData,
  profileName,
}: ExportButtonProps) {
  const [isExporting, setIsExporting] = useState(false);
  const [open, setOpen] = useState(false);

  const handleExportAnalysis = async () => {
    if (!analysisData) {
      toast.error("No analysis data available");
      return;
    }

    setIsExporting(true);
    try {
      await exportAnalysisReport(analysisData, profileName);
      toast.success("Analysis report exported successfully!");
      setOpen(false);
    } catch (error) {
      toast.error("Failed to export analysis report");
      console.error(error);
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportResume = async () => {
    if (!resumeData) {
      toast.error("No resume data available");
      return;
    }

    setIsExporting(true);
    try {
      await exportResumePDF(resumeData);
      toast.success("Resume exported successfully!");
      setOpen(false);
    } catch (error) {
      toast.error("Failed to export resume");
      console.error(error);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Download className="mr-2 h-4 w-4" />
          Export
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Export Options</DialogTitle>
          <DialogDescription>
            Choose what you want to export
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <Button
            onClick={handleExportAnalysis}
            disabled={!analysisData || isExporting}
            className="w-full justify-start"
            variant="outline"
          >
            <FileText className="mr-2 h-4 w-4" />
            Export Analysis Report (PDF)
          </Button>
          <Button
            onClick={handleExportResume}
            disabled={!resumeData || isExporting}
            className="w-full justify-start"
            variant="outline"
          >
            <FileText className="mr-2 h-4 w-4" />
            Export Resume (PDF)
          </Button>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

