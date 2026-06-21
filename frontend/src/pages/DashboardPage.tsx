import { useOutletContext } from "react-router-dom";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { User } from "@/lib/types";

export default function DashboardPage() {
  const { user } = useOutletContext<{ user: User }>();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-2xl">Dashboard</CardTitle>
        <CardDescription>Welcome back, {user.name}!</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="text-sm">
          <p>
            <span className="font-medium">Email:</span> {user.email}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
