"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useInterviewQuestions } from "@/hooks/queries/useInterview";
import { MessageSquare, CheckCircle2 } from "lucide-react";

interface InterviewPracticeProps {
  userId: string | null;
}

export default function InterviewPractice({ userId }: InterviewPracticeProps) {
  const { data, isLoading } = useInterviewQuestions(userId);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [showAnswer, setShowAnswer] = useState(false);

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

  if (!data || !data.questions) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">
            No interview questions available
          </p>
        </CardContent>
      </Card>
    );
  }

  // Parse questions from text (simplified - in production, use structured data)
  const questions = data.questions
    .split(/\d+\./)
    .filter((q) => q.trim().length > 0)
    .map((q) => q.trim())
    .slice(0, 10);

  const currentQuestion = questions[currentQuestionIndex];
  const currentAnswer = answers[currentQuestionIndex] || "";

  const handleNext = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
      setShowAnswer(false);
    }
  };

  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
      setShowAnswer(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5" />
          Interview Practice
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Question Counter */}
        <div className="flex items-center justify-between">
          <Badge variant="outline">
            Question {currentQuestionIndex + 1} of {questions.length}
          </Badge>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePrevious}
              disabled={currentQuestionIndex === 0}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleNext}
              disabled={currentQuestionIndex === questions.length - 1}
            >
              Next
            </Button>
          </div>
        </div>

        {/* Current Question */}
        <div>
          <Label className="text-base font-semibold mb-2 block">
            {currentQuestion}
          </Label>
          <Textarea
            placeholder="Type your answer here..."
            value={currentAnswer}
            onChange={(e) =>
              setAnswers({ ...answers, [currentQuestionIndex]: e.target.value })
            }
            className="min-h-32 mt-2"
          />
        </div>

        {/* Tips */}
        <div className="bg-muted p-4 rounded-lg">
          <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" />
            Tips for Answering
          </h4>
          <ul className="text-sm text-muted-foreground space-y-1">
            <li>• Use the STAR method (Situation, Task, Action, Result)</li>
            <li>• Be specific and provide concrete examples</li>
            <li>• Quantify your achievements when possible</li>
            <li>• Keep answers concise (2-3 minutes when speaking)</li>
          </ul>
        </div>

        {/* Progress */}
        <div>
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-muted-foreground">Progress</span>
            <span className="font-medium">
              {Object.keys(answers).length} / {questions.length} answered
            </span>
          </div>
          <div className="w-full bg-muted rounded-full h-2">
            <div
              className="bg-primary h-2 rounded-full transition-all"
              style={{
                width: `${(Object.keys(answers).length / questions.length) * 100}%`,
              }}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

