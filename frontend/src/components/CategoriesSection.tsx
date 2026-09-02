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
import { Badge } from "@/components/ui/badge";
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
import { getCategoryColor, cn } from "@/lib/utils";
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
              <div className="flex flex-wrap gap-2">
                {sortedCategories.map((category) =>
                  editingId === category.id ? (
                    <div key={category.id} className="flex items-center gap-1">
                      <Input
                        ref={editInputRef}
                        value={editingName}
                        onChange={(e) => setEditingName(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") saveEdit(category.id);
                          if (e.key === "Escape") cancelEditing();
                        }}
                        className="h-7 min-w-[120px] rounded-full text-sm"
                      />
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => saveEdit(category.id)}
                        aria-label="Save"
                      >
                        <Check className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={cancelEditing}
                        aria-label="Cancel"
                      >
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ) : (
                    <Badge
                      key={category.id}
                      variant="outline"
                      className={cn(
                        "min-w-32 justify-center gap-1 rounded-full px-3 py-1 text-sm",
                        getCategoryColor(category.id).text,
                        getCategoryColor(category.id).ring,
                      )}
                    >
                      {category.name}
                      {!category.is_default && (
                        <span className="flex items-center shrink-0">
                          <Button
                            variant="ghost"
                            size="icon-xs"
                            onClick={() => startEditing(category)}
                            aria-label="Edit"
                          >
                            <Pencil />
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger
                              render={
                                <Button
                                  variant="ghost"
                                  size="icon-xs"
                                  className="m-0"
                                  aria-label="Delete"
                                />
                              }
                            >
                              <Trash2 />
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
                        </span>
                      )}
                    </Badge>
                  ),
                )}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
