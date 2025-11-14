/**
 * PDF Export Service
 * Generates comprehensive analysis reports as PDF
 */

import jsPDF from "jspdf";
import type { AnalysisOverview } from "@/types/analysis";

export async function exportAnalysisReport(
  data: AnalysisOverview,
  profileName?: string
): Promise<void> {
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  let yPosition = 20;

  // Helper function to add new page if needed
  const checkPageBreak = (requiredSpace: number) => {
    if (yPosition + requiredSpace > pageHeight - 20) {
      doc.addPage();
      yPosition = 20;
    }
  };

  // Title
  doc.setFontSize(20);
  doc.setFont("helvetica", "bold");
  doc.text("Resume Analysis Report", pageWidth / 2, yPosition, {
    align: "center",
  });
  yPosition += 10;

  if (profileName) {
    doc.setFontSize(12);
    doc.setFont("helvetica", "normal");
    doc.text(`Generated for: ${profileName}`, pageWidth / 2, yPosition, {
      align: "center",
    });
    yPosition += 5;
  }

  doc.setFontSize(10);
  doc.text(
    `Generated on: ${new Date().toLocaleDateString()}`,
    pageWidth / 2,
    yPosition,
    { align: "center" }
  );
  yPosition += 15;

  // Overall Score
  checkPageBreak(30);
  doc.setFontSize(16);
  doc.setFont("helvetica", "bold");
  doc.text("Overall Resume Score", 20, yPosition);
  yPosition += 8;

  doc.setFontSize(24);
  doc.setFont("helvetica", "bold");
  doc.text(`${Math.round(data.overall_score)}/100`, 20, yPosition);
  yPosition += 6;

  doc.setFontSize(12);
  doc.setFont("helvetica", "normal");
  doc.text(`Grade: ${data.grade}`, 20, yPosition);
  yPosition += 15;

  // Strengths
  if (data.strengths && data.strengths.length > 0) {
    checkPageBreak(30);
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.text("Strengths", 20, yPosition);
    yPosition += 8;

    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    data.strengths.forEach((strength) => {
      checkPageBreak(8);
      doc.text(`• ${strength}`, 25, yPosition);
      yPosition += 6;
    });
    yPosition += 5;
  }

  // Weaknesses
  if (data.weaknesses && data.weaknesses.length > 0) {
    checkPageBreak(30);
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.text("Areas for Improvement", 20, yPosition);
    yPosition += 8;

    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    data.weaknesses.forEach((weakness) => {
      checkPageBreak(8);
      doc.text(`• ${weakness}`, 25, yPosition);
      yPosition += 6;
    });
    yPosition += 5;
  }

  // Section Analysis
  if (data.section_analysis) {
    checkPageBreak(40);
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.text("Section Analysis", 20, yPosition);
    yPosition += 8;

    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    Object.entries(data.section_analysis).forEach(([section, sectionData]) => {
      checkPageBreak(8);
      const percentage = sectionData.max_score
        ? Math.round((sectionData.score / sectionData.max_score) * 100)
        : Math.round(sectionData.score * 100);
      doc.text(
        `${section.charAt(0).toUpperCase() + section.slice(1)}: ${percentage}%`,
        25,
        yPosition
      );
      yPosition += 6;
    });
    yPosition += 5;
  }

  // Action Items
  if (data.improvements?.priority_improvements) {
    checkPageBreak(30);
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.text("Priority Improvements", 20, yPosition);
    yPosition += 8;

    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    data.improvements.priority_improvements
      .slice(0, 5)
      .forEach((item) => {
        checkPageBreak(10);
        doc.text(`${item.section}:`, 25, yPosition);
        yPosition += 5;
        doc.text(item.suggestion, 30, yPosition, { maxWidth: pageWidth - 40 });
        yPosition += 8;
      });
  }

  // Save PDF
  const fileName = `resume-analysis-${profileName || "report"}-${Date.now()}.pdf`;
  doc.save(fileName);
}

export async function exportResumePDF(
  resumeData: Record<string, unknown>
): Promise<void> {
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  let yPosition = 20;

  // Name
  if (resumeData.name) {
    doc.setFontSize(18);
    doc.setFont("helvetica", "bold");
    doc.text(String(resumeData.name), 20, yPosition);
    yPosition += 10;
  }

  // Contact Info
  doc.setFontSize(10);
  doc.setFont("helvetica", "normal");
  const contactInfo: string[] = [];
  if (resumeData.email) contactInfo.push(String(resumeData.email));
  if (resumeData.phone) contactInfo.push(String(resumeData.phone));
  if (resumeData.location) contactInfo.push(String(resumeData.location));
  if (contactInfo.length > 0) {
    doc.text(contactInfo.join(" | "), 20, yPosition);
    yPosition += 10;
  }

  // Summary
  if (resumeData.summary) {
    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.text("Summary", 20, yPosition);
    yPosition += 8;
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    const summaryLines = doc.splitTextToSize(
      String(resumeData.summary),
      pageWidth - 40
    );
    doc.text(summaryLines, 20, yPosition);
    yPosition += summaryLines.length * 5 + 5;
  }

  // Experience
  if (Array.isArray(resumeData.experience)) {
    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.text("Experience", 20, yPosition);
    yPosition += 8;
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");

    resumeData.experience.forEach((exp: any) => {
      if (yPosition > 250) {
        doc.addPage();
        yPosition = 20;
      }
      if (exp.role) {
        doc.setFont("helvetica", "bold");
        doc.text(exp.role, 20, yPosition);
        yPosition += 5;
      }
      if (exp.company) {
        doc.setFont("helvetica", "normal");
        doc.text(exp.company, 20, yPosition);
        yPosition += 5;
      }
      if (Array.isArray(exp.details)) {
        exp.details.forEach((detail: string) => {
          doc.text(`• ${detail}`, 25, yPosition, {
            maxWidth: pageWidth - 45,
          });
          yPosition += 5;
        });
      }
      yPosition += 3;
    });
  }

  const fileName = `resume-${resumeData.name || "export"}-${Date.now()}.pdf`;
  doc.save(fileName);
}

