"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useState } from "react";
import { toast } from "sonner";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            refetchOnWindowFocus: false,
            retry: 1,
            retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
            onError: (error) => {
              // Global error handler for queries
              if (error instanceof Error) {
                // Don't show toast for 404s (expected errors)
                if (!error.message.includes("404")) {
                  toast.error(error.message || "Failed to fetch data");
                }
              }
            },
          },
          mutations: {
            onError: (error) => {
              if (error instanceof Error) {
                toast.error(error.message || "Operation failed");
              }
            },
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}

