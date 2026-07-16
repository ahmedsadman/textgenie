import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { billKeys, transactionKeys } from "@/hooks/queries/keys";
import { api, type BillsQuery } from "@/lib/api";

export function useBills(params: BillsQuery) {
  return useQuery({
    queryKey: billKeys.list(params),
    queryFn: () => api.getBills(params),
  });
}

interface UnlinkVars {
  billId: number;
  transactionIds: number[];
}

export function useUnlinkBillPayments() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({ billId, transactionIds }: UnlinkVars) =>
      api.unlinkBillPayments(billId, transactionIds),
    onSuccess: () => {
      toast.success("Payment unlinked from bill");
      qc.invalidateQueries({ queryKey: billKeys.all });
      qc.invalidateQueries({ queryKey: transactionKeys.all });
    },
    onError: () => {
      toast.error("Failed to unlink payment");
    },
  });
}
