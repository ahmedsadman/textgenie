import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";

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
import {
  useCategories,
  useCreateCategory,
  useDeleteCategory,
  useUpdateCategory,
} from "@/hooks/queries/useCategories";
import type { Category } from "@/lib/types";

export default function CategoriesSection() {
  const { data: categories, isPending } = useCategories();
  const createCategory = useCreateCategory();
  const updateCategory = useUpdateCategory();
  const deleteCategory = useDeleteCategory();

  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState("");
  const editInputRef = useRef<HTMLInputElement>(null);

  const sortedCategories = useMemo(
    () => [...(categories ?? [])].sort((a, b) => a.name.localeCompare(b.name)),
    [categories],
  );

  useEffect(() => {
    if (editingId !== null) {
      editInputRef.current?.focus();
    }
  }, [editingId]);

  function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    createCategory.mutate(newName, {
      onSuccess: () => setNewName(""),
    });
  }

  function startEditing(category: Category) {
    setEditingId(category.id);
    setEditingName(category.name);
  }

  function cancelEditing() {
    setEditingId(null);
    setEditingName("");
  }

  function saveEdit(categoryId: number) {
    if (!editingName.trim()) return;
    updateCategory.mutate(
      { id: categoryId, name: editingName },
      {
        onSuccess: () => {
          setEditingId(null);
          setEditingName("");
        },
      },
    );
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
        {isPending ? (
          <p className="text-sm text-muted-foreground">Loading...</p>
        ) : (
          <>
            <form onSubmit={handleAdd} className="flex gap-2">
              <Input
                placeholder="New category name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
              <Button
                type="submit"
                disabled={createCategory.isPending || !newName.trim()}
              >
                {createCategory.isPending ? "Adding..." : "Add"}
              </Button>
            </form>

            {sortedCategories.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No categories yet. Add one above.
              </p>
            ) : (
              <ul className="divide-y">
                {sortedCategories.map((category) => (
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
                                    onClick={() =>
                                      deleteCategory.mutate(category.id)
                                    }
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
