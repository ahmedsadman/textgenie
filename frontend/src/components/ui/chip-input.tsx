import {
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export interface ChipInputProps {
  value: string[];
  onChange: (value: string[]) => void;
  suggestions?: string[];
  placeholder?: string;
  disabled?: boolean;
  ariaLabel?: string;
  /**
   * Maximum number of suggestions to render in the dropdown.
   * Defaults to 8.
   */
  maxSuggestions?: number;
}

function eqIgnoreCase(a: string, b: string): boolean {
  return a.toLowerCase() === b.toLowerCase();
}

interface DropdownRect {
  top: number;
  left: number;
  width: number;
}

export function ChipInput({
  value,
  onChange,
  suggestions = [],
  placeholder,
  disabled = false,
  ariaLabel,
  maxSuggestions = 8,
}: ChipInputProps) {
  const [draft, setDraft] = useState("");
  const [open, setOpen] = useState(false);
  const [rawHighlight, setHighlight] = useState(0);
  const [rect, setRect] = useState<DropdownRect | null>(null);
  const listId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLUListElement>(null);

  const trimmedDraft = draft.trim().toLowerCase();
  const filteredSuggestions = suggestions
    .filter((s) => !value.some((v) => eqIgnoreCase(v, s)))
    .filter((s) => !trimmedDraft || s.toLowerCase().includes(trimmedDraft))
    .slice(0, maxSuggestions);

  // Clamp inline rather than via effect so we don't trigger a re-render when
  // suggestions shrink (e.g. when the user types and filters them down).
  const highlight =
    filteredSuggestions.length === 0
      ? 0
      : Math.min(rawHighlight, filteredSuggestions.length - 1);

  // The dropdown is portaled to <body> so it escapes any `overflow-hidden`
  // ancestor (e.g. a Card). We re-measure on open, scroll, and resize so it
  // tracks the input.
  useLayoutEffect(() => {
    if (!open) return;
    function update() {
      if (!containerRef.current) return;
      const r = containerRef.current.getBoundingClientRect();
      setRect({ top: r.bottom, left: r.left, width: r.width });
    }
    update();
    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
    };
  }, [open]);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      const target = e.target as Node;
      if (
        !containerRef.current?.contains(target) &&
        !dropdownRef.current?.contains(target)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  function commit(raw: string) {
    const normalized = raw.trim();
    if (!normalized || normalized.includes(",")) {
      setDraft("");
      return;
    }
    if (value.some((v) => eqIgnoreCase(v, normalized))) {
      setDraft("");
      return;
    }
    onChange([...value, normalized]);
    setDraft("");
  }

  function removeAt(index: number) {
    onChange(value.filter((_, i) => i !== index));
    inputRef.current?.focus();
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      if (open && filteredSuggestions[highlight]) {
        commit(filteredSuggestions[highlight]);
      } else if (draft.trim()) {
        commit(draft);
      }
      return;
    }
    if (e.key === "Backspace" && !draft && value.length > 0) {
      e.preventDefault();
      onChange(value.slice(0, -1));
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setHighlight((h) => Math.min(h + 1, filteredSuggestions.length - 1));
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
      return;
    }
    if (e.key === "Escape") {
      e.preventDefault();
      setOpen(false);
    }
  }

  const showDropdown = open && filteredSuggestions.length > 0 && rect !== null;

  return (
    <div ref={containerRef} className="relative">
      <div
        className={cn(
          "flex min-h-8 w-full flex-wrap items-center gap-1.5 rounded-lg border border-input bg-transparent px-2 py-1.5 text-sm transition-colors focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50",
          disabled && "pointer-events-none cursor-not-allowed opacity-50",
        )}
        onClick={() => inputRef.current?.focus()}
      >
        {value.map((chip, index) => (
          <Badge
            key={`${chip}-${index}`}
            variant="secondary"
            className="gap-1 pr-1"
            data-slot="chip"
          >
            <span className="lowercase">{chip}</span>
            <button
              type="button"
              aria-label={`Remove ${chip}`}
              onClick={(e) => {
                e.stopPropagation();
                removeAt(index);
              }}
              className="cursor-pointer rounded-sm p-0.5 hover:bg-foreground/10"
              disabled={disabled}
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
        <input
          ref={inputRef}
          type="text"
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-label={ariaLabel}
          value={draft}
          disabled={disabled}
          onChange={(e) => {
            setDraft(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={value.length === 0 ? placeholder : undefined}
          className="min-w-[8ch] flex-1 bg-transparent outline-none placeholder:text-muted-foreground"
        />
      </div>

      {showDropdown &&
        createPortal(
          <ul
            ref={dropdownRef}
            id={listId}
            role="listbox"
            style={{
              position: "fixed",
              top: rect.top + 4,
              left: rect.left,
              width: rect.width,
              zIndex: 50,
            }}
            className="max-h-64 overflow-auto rounded-lg border bg-popover p-1 text-popover-foreground shadow-md ring-1 ring-foreground/10"
          >
            {filteredSuggestions.map((s, i) => (
              <li
                key={s}
                role="option"
                aria-selected={i === highlight}
                className={cn(
                  "cursor-pointer rounded-md px-2 py-1.5 text-sm",
                  i === highlight ? "bg-muted" : "hover:bg-muted",
                )}
                onMouseDown={(e) => {
                  e.preventDefault();
                  commit(s);
                }}
                onMouseEnter={() => setHighlight(i)}
              >
                {s}
              </li>
            ))}
          </ul>,
          document.body,
        )}
    </div>
  );
}
