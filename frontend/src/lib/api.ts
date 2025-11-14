/**
 * API client utility
 * Centralized API calls with error handling
 */

import { API_BASE } from "./config";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// Request timeout in milliseconds
const REQUEST_TIMEOUT = 30000; // 30 seconds for regular requests
const FORM_REQUEST_TIMEOUT = 120000; // 2 minutes for file uploads (resume processing takes longer)

export async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  let timeoutId: ReturnType<typeof setTimeout> | undefined;

  try {
    const controller = new AbortController();
    timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (timeoutId) clearTimeout(timeoutId);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || `Request failed: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return await response.json();
  } catch (error) {
    if (timeoutId) clearTimeout(timeoutId);
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiError("Request timeout", 408, error);
    }
    throw new ApiError(
      error instanceof Error ? error.message : "Network error",
      0,
      error
    );
  }
}

export async function apiFormRequest<T>(
  endpoint: string,
  formData: FormData
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  let timeoutId: ReturnType<typeof setTimeout> | undefined;

  try {
    const controller = new AbortController();
    // Use longer timeout for form requests (file uploads take longer)
    timeoutId = setTimeout(() => controller.abort(), FORM_REQUEST_TIMEOUT);

    const response = await fetch(url, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });

    if (timeoutId) clearTimeout(timeoutId);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || `Request failed: ${response.statusText}`,
        response.status,
        errorData
      );
    }

    return await response.json();
  } catch (error) {
    if (timeoutId) clearTimeout(timeoutId);
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiError("Request timeout - the server is taking longer than expected. Please try again.", 408, error);
    }
    throw new ApiError(
      error instanceof Error ? error.message : "Network error",
      0,
      error
    );
  }
}

