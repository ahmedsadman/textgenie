import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";

import { apiGet } from "@/lib/api";
import type { User } from "@/lib/types";

export default function GuestRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const [checking, setChecking] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    apiGet<User>("/auth/me")
      .then(() => setAuthenticated(true))
      .catch(() => setAuthenticated(false))
      .finally(() => setChecking(false));
  }, []);

  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (authenticated) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
