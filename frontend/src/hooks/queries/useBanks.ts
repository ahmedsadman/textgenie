import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { bankKeys, transactionKeys } from "@/hooks/queries/keys";
import { ApiError, api, type BankCreate, type BankUpdate } from "@/lib/api";

function toastMutationError(error: unknown, fallback: string) {
  toast.error(error instanceof ApiError ? error.message : fallback);
}

function invalidateBanksAndTransactions(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: bankKeys.all });
  qc.invalidateQueries({ queryKey: transactionKeys.all });
}

export function useBanks() {
  return useQuery({
    queryKey: bankKeys.lists(),
    queryFn: api.getBanks,
  });
}

export function useCreateBank() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: BankCreate) => api.createBank(data),
    onSuccess: () => invalidateBanksAndTransactions(qc),
    onError: (error) => toastMutationError(error, "Failed to add bank"),
  });
}

export function useUpdateBank() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: BankUpdate }) =>
      api.updateBank(id, data),
    onSuccess: () => invalidateBanksAndTransactions(qc),
    onError: (error) => toastMutationError(error, "Failed to update bank"),
  });
}

export function useDeleteBank() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteBank(id),
    onSuccess: () => invalidateBanksAndTransactions(qc),
    onError: (error) => toastMutationError(error, "Failed to delete bank"),
  });
}
