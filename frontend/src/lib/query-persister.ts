/**
 * LocalStorage-based cache persistence for React Query.
 * Stores query results to avoid refetching on page reload.
 */

const CACHE_PREFIX = "cp_cache_";
const CACHE_VERSION = "v1";
const CACHE_KEY = `${CACHE_PREFIX}${CACHE_VERSION}`;
const MAX_AGE = 24 * 60 * 60 * 1000; // 24 hours

interface CacheEntry<T = unknown> {
  data: T;
  timestamp: number;
  userId: string;
}

interface CacheStore {
  [key: string]: CacheEntry;
}

/**
 * Get the current user ID from localStorage
 */
function getCurrentUserId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("cp_user_id");
}

/**
 * Generate a cache key from query key array
 */
function serializeQueryKey(queryKey: unknown[]): string {
  return JSON.stringify(queryKey);
}

/**
 * Load the entire cache from localStorage
 */
function loadCache(): CacheStore {
  if (typeof window === "undefined") return {};
  
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (!cached) return {};
    return JSON.parse(cached) as CacheStore;
  } catch {
    return {};
  }
}

/**
 * Save the entire cache to localStorage
 */
function saveCache(cache: CacheStore): void {
  if (typeof window === "undefined") return;
  
  try {
    // Clean up expired entries before saving
    const now = Date.now();
    const cleaned: CacheStore = {};
    
    for (const [key, entry] of Object.entries(cache)) {
      if (now - entry.timestamp < MAX_AGE) {
        cleaned[key] = entry;
      }
    }
    
    localStorage.setItem(CACHE_KEY, JSON.stringify(cleaned));
  } catch (e) {
    // Storage might be full - clear old entries
    console.warn("Cache storage failed, clearing old entries", e);
    clearCache();
  }
}

/**
 * Get a cached value for a query key
 */
export function getCachedData<T>(queryKey: unknown[]): T | undefined {
  const userId = getCurrentUserId();
  if (!userId) return undefined;
  
  const cache = loadCache();
  const key = serializeQueryKey(queryKey);
  const entry = cache[key];
  
  if (!entry) return undefined;
  
  // Check if entry belongs to current user
  if (entry.userId !== userId) return undefined;
  
  // Check if entry is expired
  if (Date.now() - entry.timestamp > MAX_AGE) {
    // Remove expired entry
    delete cache[key];
    saveCache(cache);
    return undefined;
  }
  
  return entry.data as T;
}

/**
 * Set a cached value for a query key
 */
export function setCachedData<T>(queryKey: unknown[], data: T): void {
  const userId = getCurrentUserId();
  if (!userId) return;
  
  const cache = loadCache();
  const key = serializeQueryKey(queryKey);
  
  cache[key] = {
    data,
    timestamp: Date.now(),
    userId,
  };
  
  saveCache(cache);
}

/**
 * Remove a cached value for a query key
 */
export function removeCachedData(queryKey: unknown[]): void {
  const cache = loadCache();
  const key = serializeQueryKey(queryKey);
  delete cache[key];
  saveCache(cache);
}

/**
 * Clear all cached data
 */
export function clearCache(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(CACHE_KEY);
}

/**
 * Clear cache for a specific user (call on logout or new resume upload)
 */
export function clearUserCache(userId: string): void {
  const cache = loadCache();
  const cleaned: CacheStore = {};
  
  for (const [key, entry] of Object.entries(cache)) {
    if (entry.userId !== userId) {
      cleaned[key] = entry;
    }
  }
  
  saveCache(cleaned);
}

/**
 * Query keys that should be persisted to localStorage
 */
export const PERSISTABLE_QUERY_KEYS = [
  "analysis",
  "jobs",
  "interview",
  "skills",
  "ats",
  "sessions",
] as const;

/**
 * Check if a query key should be persisted
 */
export function shouldPersistQuery(queryKey: unknown[]): boolean {
  if (!queryKey.length) return false;
  const firstKey = String(queryKey[0]);
  return PERSISTABLE_QUERY_KEYS.some(key => firstKey.includes(key));
}
