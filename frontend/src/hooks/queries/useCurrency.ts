import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { bankKeys, currencyKeys } from "@/hooks/queries/keys";
import { ApiError, api } from "@/lib/api";
import type { Currency } from "@/lib/types";

function toastMutationError(error: unknown, fallback: string) {
  toast.error(error instanceof ApiError ? error.message : fallback);
}

export function useCurrency() {
  return useQuery({
    queryKey: currencyKeys.detail(),
    queryFn: api.getCurrency,
  });
}

export function useUpdateCurrency() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (currency: Currency) => api.updateCurrency(currency),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: currencyKeys.all });
      // A currency change clears cached bank balances server-side.
      qc.invalidateQueries({ queryKey: bankKeys.all });
    },
    onError: (error) => toastMutationError(error, "Failed to update currency"),
  });
}
