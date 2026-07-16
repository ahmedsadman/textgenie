import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { toast } from "sonner";

import { messageKeys } from "@/hooks/queries/keys";
import { ApiError, api, type MessagesQuery } from "@/lib/api";

export function useMessages(params: MessagesQuery) {
  return useQuery({
    queryKey: messageKeys.list(params),
    queryFn: () => api.getMessages(params),
    placeholderData: keepPreviousData,
  });
}

export function useDeleteMessage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteMessage(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: messageKeys.all });
    },
    onError: (error) => {
      toast.error(
        error instanceof ApiError ? error.message : "Failed to delete message",
      );
    },
  });
}
