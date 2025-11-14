import { useState, useEffect } from "react";
import type {
  JobRecommendations,
  SalaryInsights,
  Keywords,
} from "@/types/analysis";

const API_BASE = "http://localhost:8000";

export function useJobRecommendations(userId: string | null, limit = 10) {
  const [data, setData] = useState<JobRecommendations | null>(null);
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
          `${API_BASE}/jobs/recommendations?user_id=${userId}&limit=${limit}`
        );
        if (!response.ok) throw new Error("Failed to fetch job recommendations");
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [userId, limit]);

  return { data, loading, error };
}

export function useSalaryInsights(userId: string | null, location?: string) {
  const [data, setData] = useState<SalaryInsights | null>(null);
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
        const url = new URL(`${API_BASE}/jobs/salary-insights`);
        url.searchParams.set("user_id", userId);
        if (location) url.searchParams.set("location", location);

        const response = await fetch(url.toString());
        if (!response.ok) throw new Error("Failed to fetch salary insights");
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [userId, location]);

  return { data, loading, error };
}

export function useKeywords(userId: string | null, targetRole?: string) {
  const [data, setData] = useState<Keywords | null>(null);
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
        const url = new URL(`${API_BASE}/jobs/keywords`);
        url.searchParams.set("user_id", userId);
        if (targetRole) url.searchParams.set("target_role", targetRole);

        const response = await fetch(url.toString());
        if (!response.ok) throw new Error("Failed to fetch keywords");
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


