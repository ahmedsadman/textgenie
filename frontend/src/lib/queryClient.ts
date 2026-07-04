import { QueryCache, QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api";

declare module "@tanstack/react-query" {
  interface Register {
    queryMeta: {
      // When true, QueryCache.onError skips the global toast for this query.
      // Use for expected error states (e.g., auth 401 in guest routes).
      silent?: boolean;
    };
  }
}

export const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error, query) => {
      if (query.meta?.silent) return;
      const message =
        error instanceof ApiError ? error.message : "Request failed";
      toast.error(message);
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: (count, error) => {
        if (
          error instanceof ApiError &&
          error.status >= 400 &&
          error.status < 500
        ) {
          return false;
        }
        return count < 2;
      },
      refetchOnWindowFocus: true,
    },
    mutations: {
      retry: false,
    },
  },
});
