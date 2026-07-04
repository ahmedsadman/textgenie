import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { categoryKeys, messageKeys } from "@/hooks/queries/keys";
import { ApiError, api } from "@/lib/api";

function toastMutationError(error: unknown, fallback: string) {
  toast.error(error instanceof ApiError ? error.message : fallback);
}

export function useCategories() {
  return useQuery({
    queryKey: categoryKeys.lists(),
    queryFn: api.getCategories,
  });
}

export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => api.createCategory(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: categoryKeys.all });
    },
    onError: (error) => toastMutationError(error, "Failed to add category"),
  });
}

export function useUpdateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      api.updateCategory(id, name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: categoryKeys.all });
      // Messages display category.name inline — a rename invalidates them.
      qc.invalidateQueries({ queryKey: messageKeys.all });
    },
    onError: (error) => toastMutationError(error, "Failed to update category"),
  });
}

export function useDeleteCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteCategory(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: categoryKeys.all });
      // Messages carry a nested category — delete may clear it server-side.
      qc.invalidateQueries({ queryKey: messageKeys.all });
    },
    onError: (error) => toastMutationError(error, "Failed to delete category"),
  });
}
