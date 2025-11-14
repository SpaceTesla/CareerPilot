"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { 
  MessageSquare, 
  CheckCircle2, 
  Sparkles, 
  ArrowRight, 
  ArrowLeft,
  Star,
  TrendingUp,
  Lightbulb,
  AlertCircle,
} from "lucide-react";
import { useInterviewQuestionsByCategory, useEvaluateAnswer } from "@/hooks/queries/useInterview";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface InterviewPracticeProps {
  userId: string | null;
}

type QuestionCategory = "technical" | "behavioral" | "situational" | "all";

export default function InterviewPractice({ userId }: InterviewPracticeProps) {
  const [selectedCategory, setSelectedCategory] = useState<QuestionCategory>("all");
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [evaluatedAnswers, setEvaluatedAnswers] = useState<Record<number, any>>({});
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [showSTAR, setShowSTAR] = useState(false);

  const { data, isLoading } = useInterviewQuestionsByCategory(userId, selectedCategory);
  const evaluateMutation = useEvaluateAnswer();

  // Parse questions from text
  const questions = data?.questions
    ? data.questions
        .split(/\d+\./)
        .filter((q) => q.trim().length > 0)
        .map((q) => {
          const trimmed = q.trim();
          // Extract question type if mentioned
          const typeMatch = trimmed.match(/(Technical|Behavioral|Situational|Project)/i);
          const type = typeMatch ? typeMatch[1].toLowerCase() : "general";
          return {
            text: trimmed.replace(/(Technical|Behavioral|Situational|Project):\s*/i, ""),
            type,
          };
        })
        .slice(0, 15)
    : [];

  const currentQuestion = questions[currentQuestionIndex];
  const currentAnswer = answers[currentQuestionIndex] || "";
  const currentEvaluation = evaluatedAnswers[currentQuestionIndex];

  const handleEvaluate = async () => {
    if (!currentAnswer.trim() || !userId || !currentQuestion) {
      toast.error("Please provide an answer before evaluating");
      return;
    }

    setIsEvaluating(true);
    try {
      const result = await evaluateMutation.mutateAsync({
        userId,
        question: currentQuestion.text,
        answer: currentAnswer,
        questionType: currentQuestion.type,
      });

      setEvaluatedAnswers({
        ...evaluatedAnswers,
        [currentQuestionIndex]: result,
      });
      toast.success("Answer evaluated successfully!");
    } catch (error) {
      toast.error("Failed to evaluate answer. Please try again.");
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleNext = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    }
  };

  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
    }
  };

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

  if (!data || !questions.length) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground text-center py-8">
            No interview questions available. Please try again later.
          </p>
        </CardContent>
      </Card>
    );
  }

  const answeredCount = Object.keys(answers).filter(
    (key) => answers[Number(key)]?.trim().length > 0
  ).length;
  const progress = (answeredCount / questions.length) * 100;

  return (
    <div className="space-y-6">
      {/* Category Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Interview Practice
          </CardTitle>
          <CardDescription>
            Practice answering interview questions and get AI-powered feedback
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={selectedCategory} onValueChange={(v) => {
            setSelectedCategory(v as QuestionCategory);
            setCurrentQuestionIndex(0);
            setAnswers({});
            setEvaluatedAnswers({});
          }}>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="technical">Technical</TabsTrigger>
              <TabsTrigger value="behavioral">Behavioral</TabsTrigger>
              <TabsTrigger value="situational">Situational</TabsTrigger>
            </TabsList>
          </Tabs>
        </CardContent>
      </Card>

      {/* Progress Overview */}
      <Card>
        <CardContent className="pt-6">
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Practice Progress</span>
              <span className="font-medium">
                {answeredCount} / {questions.length} answered
              </span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>
        </CardContent>
      </Card>

      {/* Question and Answer Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Badge variant="outline" className="text-sm">
                Question {currentQuestionIndex + 1} of {questions.length}
              </Badge>
              {currentQuestion && (
                <Badge
                  variant="secondary"
                  className={cn(
                    currentQuestion.type === "technical" && "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
                    currentQuestion.type === "behavioral" && "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
                    currentQuestion.type === "situational" && "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
                  )}
                >
                  {currentQuestion.type.charAt(0).toUpperCase() + currentQuestion.type.slice(1)}
                </Badge>
              )}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handlePrevious}
                disabled={currentQuestionIndex === 0}
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleNext}
                disabled={currentQuestionIndex === questions.length - 1}
              >
                Next
                <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Current Question */}
          <div>
            <Label className="text-lg font-semibold mb-3 block">
              {currentQuestion?.text}
            </Label>
            
            {/* STAR Method Toggle for Behavioral Questions */}
            {currentQuestion?.type === "behavioral" && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowSTAR(!showSTAR)}
                className="mb-4"
              >
                <Star className="h-4 w-4 mr-2" />
                {showSTAR ? "Hide" : "Show"} STAR Method Guide
              </Button>
            )}

            {showSTAR && currentQuestion?.type === "behavioral" && (
              <Alert className="mb-4">
                <Star className="h-4 w-4" />
                <AlertDescription>
                  <div className="space-y-2 mt-2">
                    <div>
                      <strong>Situation:</strong> Set the context and background
                    </div>
                    <div>
                      <strong>Task:</strong> Describe the challenge or goal
                    </div>
                    <div>
                      <strong>Action:</strong> Explain what you did (use "I", not "we")
                    </div>
                    <div>
                      <strong>Result:</strong> Share the outcome and what you learned
                    </div>
                  </div>
                </AlertDescription>
              </Alert>
            )}

            <Textarea
              placeholder={
                currentQuestion?.type === "behavioral"
                  ? "Use the STAR method: Situation, Task, Action, Result..."
                  : "Type your answer here..."
              }
              value={currentAnswer}
              onChange={(e) =>
                setAnswers({ ...answers, [currentQuestionIndex]: e.target.value })
              }
              className="min-h-40 mt-2"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <Button
              onClick={handleEvaluate}
              disabled={!currentAnswer.trim() || isEvaluating}
              className="flex-1"
            >
              {isEvaluating ? (
                <>
                  <Sparkles className="h-4 w-4 mr-2 animate-spin" />
                  Evaluating...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Get AI Feedback
                </>
              )}
            </Button>
          </div>

          {/* AI Feedback */}
          {currentEvaluation && (
            <div className="space-y-4 pt-4 border-t">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-primary" />
                <h3 className="text-lg font-semibold">AI Feedback</h3>
                <Badge variant="secondary" className="ml-auto">
                  Score: {Math.round(currentEvaluation.overall_score * 10)}/10
                </Badge>
              </div>

              {/* Scores Breakdown */}
              {currentEvaluation.feedback?.scores && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {Object.entries(currentEvaluation.feedback.scores).map(([key, value]) => (
                    <div key={key} className="text-center p-3 bg-muted rounded-lg">
                      <div className="text-2xl font-bold text-primary">{value}</div>
                      <div className="text-xs text-muted-foreground capitalize">{key}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* Strengths */}
              {currentEvaluation.feedback?.strengths?.length > 0 && (
                <Alert>
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                  <AlertDescription>
                    <div className="font-semibold mb-2">Strengths:</div>
                    <ul className="list-disc list-inside space-y-1">
                      {currentEvaluation.feedback.strengths.map((strength: string, idx: number) => (
                        <li key={idx} className="text-sm">{strength}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}

              {/* Improvements */}
              {currentEvaluation.feedback?.improvements?.length > 0 && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    <div className="font-semibold mb-2">Areas for Improvement:</div>
                    <ul className="list-disc list-inside space-y-1">
                      {currentEvaluation.feedback.improvements.map((improvement: string, idx: number) => (
                        <li key={idx} className="text-sm">{improvement}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}

              {/* Suggestions */}
              {currentEvaluation.feedback?.suggestions?.length > 0 && (
                <Alert>
                  <Lightbulb className="h-4 w-4 text-yellow-600" />
                  <AlertDescription>
                    <div className="font-semibold mb-2">Suggestions:</div>
                    <ul className="list-disc list-inside space-y-1">
                      {currentEvaluation.feedback.suggestions.map((suggestion: string, idx: number) => (
                        <li key={idx} className="text-sm">{suggestion}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}

              {/* Sample Answer */}
              {currentEvaluation.feedback?.sample_answer && (
                <div className="p-4 bg-muted rounded-lg">
                  <div className="font-semibold mb-2">Sample Improved Answer:</div>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {currentEvaluation.feedback.sample_answer}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Tips */}
          <div className="bg-muted p-4 rounded-lg">
            <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" />
              Tips for Answering
            </h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              {currentQuestion?.type === "behavioral" ? (
                <>
                  <li>• Use the STAR method (Situation, Task, Action, Result)</li>
                  <li>• Be specific and provide concrete examples from your experience</li>
                  <li>• Quantify your achievements when possible</li>
                </>
              ) : currentQuestion?.type === "technical" ? (
                <>
                  <li>• Explain your thought process step by step</li>
                  <li>• Mention relevant technologies and concepts</li>
                  <li>• Discuss trade-offs and alternatives if applicable</li>
                </>
              ) : (
                <>
                  <li>• Be specific and provide concrete examples</li>
                  <li>• Show your problem-solving approach</li>
                  <li>• Keep answers concise and focused</li>
                </>
              )}
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
