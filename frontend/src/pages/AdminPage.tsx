import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";

import { AdminUserCard } from "@/components/AdminUserCard";
import { Button } from "@/components/ui/button";
import { useAdminUsageSummary, useAdminUsers } from "@/hooks/queries/useAdmin";
import { useMe } from "@/hooks/queries/useAuth";

const PER_PAGE = 20;

export default function AdminPage() {
  const { data: me, isPending: mePending } = useMe();
  const navigate = useNavigate();

  const [page, setPage] = useState(1);
  const [expandedUserId, setExpandedUserId] = useState<number | null>(null);

  useEffect(() => {
    if (me && !me.is_admin) {
      navigate("/", { replace: true });
    }
  }, [me, navigate]);

  const usersQuery = useAdminUsers(
    { page, page_size: PER_PAGE },
    Boolean(me?.is_admin),
  );
  const userIds = useMemo(
    () => usersQuery.data?.users.map((u) => u.id) ?? [],
    [usersQuery.data],
  );
  const summaryQuery = useAdminUsageSummary(userIds, userIds.length > 0);

  if (mePending) {
    return <p className="text-muted-foreground">Loading...</p>;
  }
  if (!me?.is_admin) {
    return null;
  }

  const totalPages = usersQuery.data
    ? Math.max(1, Math.ceil(usersQuery.data.total / PER_PAGE))
    : 1;

  function changePage(next: number) {
    setPage(next);
    setExpandedUserId(null);
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-semibold">Admin</h1>
        <p className="text-sm text-muted-foreground">
          Manage users and monitor LLM usage across the platform.
        </p>
      </div>

      {usersQuery.isPending ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : usersQuery.isError ? (
        <p className="text-sm text-destructive">Failed to load users.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {usersQuery.data?.users.map((u) => (
            <AdminUserCard
              key={u.id}
              user={u}
              summary={summaryQuery.data?.[String(u.id)]}
              summaryLoading={summaryQuery.isLoading}
              expanded={expandedUserId === u.id}
              onToggle={() =>
                setExpandedUserId((cur) => (cur === u.id ? null : u.id))
              }
              canDelete={u.id !== me.id}
            />
          ))}
          {usersQuery.data?.users.length === 0 && (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No users.
            </p>
          )}
        </div>
      )}

      {usersQuery.data && usersQuery.data.total > PER_PAGE && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {page} of {totalPages} · {usersQuery.data.total} users
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => changePage(Math.max(1, page - 1))}
              disabled={page <= 1}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => changePage(Math.min(totalPages, page + 1))}
              disabled={page >= totalPages}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
