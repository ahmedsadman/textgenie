import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { transactionKeys } from "@/hooks/queries/keys";
import { api, type TransactionsQuery } from "@/lib/api";
import type { PaginatedTransactions, TransactionType } from "@/lib/types";

export function useTransactions(params: TransactionsQuery) {
  return useQuery({
    queryKey: transactionKeys.list(params),
    queryFn: () => api.getTransactions(params),
  });
}

interface UpdateTypeVars {
  id: number;
  type: TransactionType;
}

interface UpdateTypeContext {
  previous: PaginatedTransactions | undefined;
}

export function useUpdateTransactionType(params: TransactionsQuery) {
  const qc = useQueryClient();
  const key = transactionKeys.list(params);

  return useMutation<
    Awaited<ReturnType<typeof api.updateTransaction>>,
    unknown,
    UpdateTypeVars,
    UpdateTypeContext
  >({
    mutationFn: ({ id, type }) => api.updateTransaction(id, type),
    onMutate: async ({ id, type }) => {
      // Prevent an in-flight refetch from clobbering the optimistic write.
      await qc.cancelQueries({ queryKey: key });
      const previous = qc.getQueryData<PaginatedTransactions>(key);
      if (previous) {
        qc.setQueryData<PaginatedTransactions>(key, {
          ...previous,
          transactions: previous.transactions.map((t) =>
            t.id === id ? { ...t, type } : t,
          ),
        });
      }
      return { previous };
    },
    onError: (_error, _vars, context) => {
      if (context?.previous) {
        qc.setQueryData(key, context.previous);
      }
      toast.error("Failed to update transaction");
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: transactionKeys.all });
    },
  });
}
