import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { adminKeys } from "@/hooks/queries/keys";
import {
  ApiError,
  api,
  type AdminListUsersQuery,
  type AdminUserUsageQuery,
} from "@/lib/api";

export function useAdminUsers(params: AdminListUsersQuery, enabled = true) {
  return useQuery({
    queryKey: adminKeys.usersList(params),
    queryFn: () => api.adminListUsers(params),
    enabled,
  });
}

export function useAdminUsageSummary(userIds: number[], enabled = true) {
  return useQuery({
    queryKey: adminKeys.usageSummary(userIds),
    queryFn: () => api.adminUsageSummary(userIds),
    enabled: enabled && userIds.length > 0,
  });
}

export function useAdminUserUsage(
  id: number,
  params: AdminUserUsageQuery,
  enabled = true,
) {
  return useQuery({
    queryKey: adminKeys.userUsage(id, params),
    queryFn: () => api.adminUserUsage(id, params),
    enabled,
  });
}

export function useDeleteAdminUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.adminDeleteUser(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: adminKeys.users() });
      qc.invalidateQueries({ queryKey: [...adminKeys.all, "usageSummary"] });
    },
    onError: (error) => {
      toast.error(
        error instanceof ApiError ? error.message : "Failed to delete user",
      );
    },
  });
}
