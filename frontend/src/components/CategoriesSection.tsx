import { useEffect, useRef, useState, type FormEvent } from "react";
import { toast } from "sonner";

import { Check, Pencil, Trash2, X } from "lucide-react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import type { Category } from "@/lib/types";

export default function CategoriesSection() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState("");
  const editInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api
      .getCategories()
      .then(setCategories)
      .catch(() => toast.error("Failed to load categories"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (editingId !== null) {
      editInputRef.current?.focus();
    }
  }, [editingId]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    setSubmitting(true);

    try {
      const category = await api.createCategory(newName);
      setCategories((prev) =>
        [...prev, category].sort((a, b) => a.name.localeCompare(b.name)),
      );
      setNewName("");
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error(error.message);
      } else {
        toast.error("Failed to add category");
      }
    } finally {
      setSubmitting(false);
    }
  }

  function startEditing(category: Category) {
    setEditingId(category.id);
    setEditingName(category.name);
  }

  function cancelEditing() {
    setEditingId(null);
    setEditingName("");
  }

  async function saveEdit(categoryId: number) {
    if (!editingName.trim()) return;

    try {
      const updated = await api.updateCategory(categoryId, editingName);
      setCategories((prev) =>
        prev
          .map((c) => (c.id === categoryId ? updated : c))
          .sort((a, b) => a.name.localeCompare(b.name)),
      );
      setEditingId(null);
      setEditingName("");
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error(error.message);
      } else {
        toast.error("Failed to update category");
      }
    }
  }

  async function handleDelete(categoryId: number) {
    try {
      await api.deleteCategory(categoryId);
      setCategories((prev) => prev.filter((c) => c.id !== categoryId));
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error(error.message);
      } else {
        toast.error("Failed to delete category");
      }
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Categories</CardTitle>
        <CardDescription>
          Group messages so spending and stats can be filtered. Default
          categories cannot be edited or deleted.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {loading ? (
          <p className="text-sm text-muted-foreground">Loading...</p>
        ) : (
          <>
            <form onSubmit={handleAdd} className="flex gap-2">
              <Input
                placeholder="New category name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
              <Button type="submit" disabled={submitting || !newName.trim()}>
                {submitting ? "Adding..." : "Add"}
              </Button>
            </form>

            {categories.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No categories yet. Add one above.
              </p>
            ) : (
              <ul className="divide-y">
                {categories.map((category) => (
                  <li
                    key={category.id}
                    className="flex items-center gap-2 py-2"
                  >
                    {editingId === category.id ? (
                      <>
                        <Input
                          ref={editInputRef}
                          value={editingName}
                          onChange={(e) => setEditingName(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") saveEdit(category.id);
                            if (e.key === "Escape") cancelEditing();
                          }}
                          className="flex-1"
                        />
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => saveEdit(category.id)}
                          aria-label="Save"
                        >
                          <Check className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={cancelEditing}
                          aria-label="Cancel"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </>
                    ) : (
                      <>
                        <span className="flex-1 text-sm">{category.name}</span>
                        {!category.is_default && (
                          <>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => startEditing(category)}
                              aria-label="Edit"
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <AlertDialog>
                              <AlertDialogTrigger
                                render={
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    aria-label="Delete"
                                  />
                                }
                              >
                                <Trash2 className="h-4 w-4" />
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>
                                    Delete category
                                  </AlertDialogTitle>
                                  <AlertDialogDescription>
                                    Are you sure you want to delete &quot;
                                    {category.name}&quot;? This action cannot be
                                    undone.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                                  <AlertDialogAction
                                    variant="destructive"
                                    onClick={() => handleDelete(category.id)}
                                  >
                                    Delete
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          </>
                        )}
                      </>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
