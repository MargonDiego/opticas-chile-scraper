import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCLP(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return "Consultar";
  return `$${amount.toLocaleString("es-CL")} CLP`;
}