import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const CATEGORY_COLORS = [
  {
    bg: "bg-blue-100",
    text: "text-blue-700",
    ring: "ring-blue-300",
    dot: "bg-blue-500",
  },
  {
    bg: "bg-emerald-100",
    text: "text-emerald-700",
    ring: "ring-emerald-300",
    dot: "bg-emerald-500",
  },
  {
    bg: "bg-amber-100",
    text: "text-amber-700",
    ring: "ring-amber-300",
    dot: "bg-amber-500",
  },
  {
    bg: "bg-rose-100",
    text: "text-rose-700",
    ring: "ring-rose-300",
    dot: "bg-rose-500",
  },
  {
    bg: "bg-violet-100",
    text: "text-violet-700",
    ring: "ring-violet-300",
    dot: "bg-violet-500",
  },
  {
    bg: "bg-cyan-100",
    text: "text-cyan-700",
    ring: "ring-cyan-300",
    dot: "bg-cyan-500",
  },
  {
    bg: "bg-orange-100",
    text: "text-orange-700",
    ring: "ring-orange-300",
    dot: "bg-orange-500",
  },
  {
    bg: "bg-teal-100",
    text: "text-teal-700",
    ring: "ring-teal-300",
    dot: "bg-teal-500",
  },
];

export function getCategoryColor(id: number) {
  return CATEGORY_COLORS[id % CATEGORY_COLORS.length];
}

function ordinalSuffix(day: number): string {
  if (day >= 11 && day <= 13) return "th";
  switch (day % 10) {
    case 1:
      return "st";
    case 2:
      return "nd";
    case 3:
      return "rd";
    default:
      return "th";
  }
}

export function formatMessageDateTime(iso: string): string {
  const d = new Date(iso);
  const day = d.getDate();
  const month = d.toLocaleString("en-US", { month: "long" });
  const year = d.getFullYear();
  const time = d.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
  const datePart =
    year === new Date().getFullYear()
      ? `${day}${ordinalSuffix(day)} ${month}`
      : `${day}${ordinalSuffix(day)} ${month}, ${year}`;
  return `${datePart} at ${time}`;
}
