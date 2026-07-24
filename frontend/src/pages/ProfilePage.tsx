import { type FormEvent, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  useChangePassword,
  useMe,
  useUpdateProfile,
} from "@/hooks/queries/useAuth";

function formatMemberSince(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function ProfilePage() {
  const { data: user, isPending } = useMe();
  const updateProfile = useUpdateProfile();
  const changePassword = useChangePassword();

  const [pendingName, setPendingName] = useState<string | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  if (isPending || !user) {
    return <p className="text-muted-foreground">Loading...</p>;
  }

  const name = pendingName ?? user.name;
  const trimmedName = name.trim();
  const nameDirty = trimmedName.length > 0 && trimmedName !== user.name;

  function handleSaveProfile(e: FormEvent) {
    e.preventDefault();
    if (!nameDirty) return;
    updateProfile.mutate(trimmedName, {
      onSuccess: () => {
        setPendingName(null);
        toast.success("Profile updated");
      },
    });
  }

  const passwordValid = currentPassword.length > 0 && newPassword.length >= 8;

  function handleChangePassword(e: FormEvent) {
    e.preventDefault();
    if (!passwordValid) return;
    changePassword.mutate(
      { currentPassword, newPassword },
      {
        onSuccess: () => {
          toast.success("Password changed");
          setCurrentPassword("");
          setNewPassword("");
        },
      },
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg sm:text-2xl">Profile</CardTitle>
          <CardDescription>
            Manage your account details and password.
          </CardDescription>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Account details</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSaveProfile} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                type="text"
                required
                value={name}
                onChange={(e) => setPendingName(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={user.email}
                readOnly
                disabled
              />
              <p className="text-xs text-muted-foreground">
                Email cannot be changed.
              </p>
            </div>
            <div className="flex flex-col gap-2">
              <Label>Member since</Label>
              <p className="text-sm text-muted-foreground">
                {formatMemberSince(user.created_at)}
              </p>
            </div>
            <div>
              <Button
                type="submit"
                disabled={!nameDirty || updateProfile.isPending}
              >
                {updateProfile.isPending ? "Saving..." : "Save changes"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Change password</CardTitle>
          <CardDescription>
            Enter your current password and choose a new one (at least 8
            characters).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleChangePassword} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="current-password">Current password</Label>
              <Input
                id="current-password"
                type="password"
                autoComplete="current-password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="new-password">New password</Label>
              <Input
                id="new-password"
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </div>
            <div>
              <Button
                type="submit"
                disabled={!passwordValid || changePassword.isPending}
              >
                {changePassword.isPending ? "Updating..." : "Update password"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
