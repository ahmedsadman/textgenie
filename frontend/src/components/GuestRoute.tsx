import { Navigate } from "react-router-dom";

import { useMe } from "@/hooks/queries/useAuth";

export default function GuestRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isPending, isSuccess } = useMe();

  if (isPending) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (isSuccess) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
