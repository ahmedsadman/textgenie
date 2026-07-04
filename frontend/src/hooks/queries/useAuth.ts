import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { authKeys } from "@/hooks/queries/keys";
import { ApiError, api } from "@/lib/api";

export function useMe() {
  return useQuery({
    queryKey: authKeys.me(),
    queryFn: api.getMe,
    // A 401 on this endpoint is an expected "not logged in" signal — used by
    // GuestRoute to decide whether to render the login form. Suppress the
    // global error toast so guests don't see a spurious "Not authenticated".
    meta: { silent: true },
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      api.login(email, password),
    onSuccess: () => {
      // Drop any cached "not logged in" error so downstream useMe() consumers
      // (AppLayout) refetch with the new session.
      qc.invalidateQueries({ queryKey: authKeys.all });
    },
    onError: (error) => {
      toast.error(
        error instanceof ApiError ? error.message : "Something went wrong",
      );
    },
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.logout(),
    onSuccess: () => {
      // Wipe every cache entry so the next user's session can't read the
      // previous user's banks, transactions, messages, etc.
      qc.clear();
    },
    onError: (error) => {
      toast.error(error instanceof ApiError ? error.message : "Logout failed");
    },
  });
}
