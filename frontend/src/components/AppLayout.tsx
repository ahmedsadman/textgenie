import { useEffect, useState } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";

import {
  Landmark,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  Shield,
  User,
  X,
} from "lucide-react";

import { Button, buttonVariants } from "@/components/ui/button";
import { useLogout, useMe } from "@/hooks/queries/useAuth";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "Dashboard", path: "/", icon: LayoutDashboard },
  { label: "Finance", path: "/finance", icon: Landmark },
  { label: "Profile", path: "/profile", icon: User },
  { label: "Settings", path: "/settings", icon: Settings },
  { label: "Admin", path: "/admin", icon: Shield, adminOnly: true },
];

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { data: user, isPending, isError } = useMe();
  const logout = useLogout();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (isError) navigate("/login", { replace: true });
  }, [isError, navigate]);

  function handleLogout() {
    logout.mutate(undefined, {
      onSuccess: () => navigate("/login"),
    });
  }

  if (isPending) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="flex min-h-screen">
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 cursor-pointer bg-black/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r bg-background transition-transform duration-200 md:static md:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-14 items-center justify-between border-b px-4">
          <span className="text-lg font-semibold">TextGenie</span>
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        <nav className="flex-1 space-y-1 p-2">
          {NAV_ITEMS.filter((item) => !item.adminOnly || user.is_admin).map(
            (item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setSidebarOpen(false)}
                  className={cn(
                    buttonVariants({
                      variant: isActive ? "secondary" : "ghost",
                    }),
                    "h-10 w-full justify-start gap-3 text-base",
                  )}
                >
                  <item.icon className="h-5 w-5" />
                  {item.label}
                </Link>
              );
            },
          )}
        </nav>

        <div className="border-t p-2">
          <Button
            variant="ghost"
            className="h-10 w-full justify-start gap-3 text-base"
            onClick={handleLogout}
          >
            <LogOut className="h-5 w-5" />
            Logout
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center border-b px-4 md:hidden">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <span className="ml-2 text-lg font-semibold">TextGenie</span>
        </header>

        <main className="flex-1 p-4 md:p-6">
          <div className="mx-auto w-full max-w-6xl">
            <Outlet context={{ user }} />
          </div>
        </main>
      </div>
    </div>
  );
}
