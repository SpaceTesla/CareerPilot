import { useState, useEffect } from "react";
import type {
  AnalysisOverview,
  ATSScore,
  SkillsGap,
  JobMatch,
  CareerPath,
} from "@/types/analysis";

const API_BASE = "http://localhost:8000";

export function useAnalysisOverview(userId: string | null) {
  const [data, setData] = useState<AnalysisOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) {
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(
          `${API_BASE}/analysis/overview?user_id=${userId}`
        );
        if (!response.ok) throw new Error("Failed to fetch analysis");
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [userId]);

  return { data, loading, error };
}

export function useATSScore(userId: string | null) {
  const [data, setData] = useState<ATSScore | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) {
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(
          `${API_BASE}/analysis/ats-score?user_id=${userId}`
        );
        if (!response.ok) throw new Error("Failed to fetch ATS score");
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [userId]);

  return { data, loading, error };
}

export function useSkillsGap(userId: string | null, targetRole?: string) {
  const [data, setData] = useState<SkillsGap | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) {
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        setLoading(true);
        const url = new URL(`${API_BASE}/analysis/skills-gap`);
        url.searchParams.set("user_id", userId);
        if (targetRole) url.searchParams.set("target_role", targetRole);

        const response = await fetch(url.toString());
        if (!response.ok) throw new Error("Failed to fetch skills gap");
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [userId, targetRole]);

  return { data, loading, error };
}

export function useJobMatch(userId: string | null, role?: string) {
  const [data, setData] = useState<JobMatch | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) {
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        setLoading(true);
        const url = new URL(`${API_BASE}/analysis/job-match`);
        url.searchParams.set("user_id", userId);
        if (role) url.searchParams.set("role", role);

        const response = await fetch(url.toString());
        if (!response.ok) throw new Error("Failed to fetch job match");
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [userId, role]);

  return { data, loading, error };
}

export function useCareerPath(userId: string | null) {
  const [data, setData] = useState<CareerPath | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!userId) {
      setLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(
          `${API_BASE}/analysis/career-path?user_id=${userId}`
        );
        if (!response.ok) throw new Error("Failed to fetch career path");
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [userId]);

  return { data, loading, error };
}


