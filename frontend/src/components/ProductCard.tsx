import React, { useState } from "react";
import { StoreBadge } from "./StoreBadge";
import { formatCLP } from "@/lib/utils";
import { History, Glasses, Sun, Eye, ArrowUpRight } from "lucide-react";
import { Button } from "./ui/button";

export interface Product {
  id: string;
  store: string;
  brand: string;
  model_name: string;
  category: string;
  url: string;
  image_url?: string;
  current_price_normal?: number;
  current_price_discount?: number;
  current_in_stock?: boolean;
}

interface Props {
  product: Product;
  onViewHistory: (id: string) => void;
}

function resolveImageUrl(url?: string, store?: string): string | undefined {
  if (!url || typeof url !== "string") return undefined;
  const trimmed = url.trim();
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) return trimmed;
  if (trimmed.startsWith("//")) return `https:${trimmed}`;

  const storeHosts: Record<string, string> = {
    ryk: "https://www.ryk.cl",
    econopticas: "https://www.econopticas.cl",
    schilling: "https://www.schilling.cl",
    gmo: "https://www.gmo.cl",
    place_vendome: "https://www.opv.cl",
    karun: "https://latam.karunworld.com",
    lentesplus: "https://www.lentesplus.com",
  };

  const host = store ? storeHosts[store.toLowerCase()] : undefined;
  if (host) {
    return `${host}/${trimmed.replace(/^\/+/, "")}`;
  }
  return trimmed;
}

function getCategoryIcon(category: string) {
  const c = category.toLowerCase();
  if (c.includes("sol")) return Sun;
  if (c.includes("contacto")) return Eye;
  return Glasses;
}

function formatCategoryLabel(category: string) {
  const c = category.toLowerCase();
  if (c.includes("sol")) return "Sol";
  if (c.includes("contacto")) return "Contacto";
  return "Óptico";
}

export function ProductCard({ product, onViewHistory }: Props) {
  const [imgError, setImgError] = useState(false);
  const [imgLoaded, setImgLoaded] = useState(false);
  const resolvedImgUrl = resolveImageUrl(product.image_url, product.store);

  const isOutOfStock = product.current_in_stock === false;

  const hasDiscount = Boolean(
    product.current_price_discount &&
      product.current_price_normal &&
      product.current_price_discount < product.current_price_normal
  );

  const discountPct = hasDiscount
    ? Math.round(
        ((product.current_price_normal! - product.current_price_discount!) /
          product.current_price_normal!) *
          100
      )
    : null;

  const savingsAmount = hasDiscount
    ? product.current_price_normal! - product.current_price_discount!
    : 0;

  const effectivePrice = product.current_price_discount || product.current_price_normal;
  const CategoryIcon = getCategoryIcon(product.category);

  return (
    <article
      className={`group relative flex flex-col bg-card text-card-foreground rounded-2xl border transition-all duration-200 overflow-hidden ${
        isOutOfStock
          ? "border-border/60 opacity-75 hover:opacity-90"
          : "border-border/80 hover:border-foreground/30 shadow-xs hover:shadow-md"
      }`}
    >
      {/* 1. Top Specimen Header: Store Origin & Discount Pill */}
      <div className="flex items-center justify-between p-3 pb-2 z-10">
        <StoreBadge store={product.store} />
        {hasDiscount && (
          <span className="font-mono text-[11px] font-bold px-2 py-0.5 rounded-md bg-zinc-900 text-zinc-50 dark:bg-zinc-100 dark:text-zinc-900 shadow-xs tracking-tight">
            -{discountPct}%
          </span>
        )}
      </div>

      {/* 2. Optical Specimen Canvas (Light stage with inset ring) */}
      <div className="relative aspect-[4/3] w-full p-4 flex items-center justify-center bg-zinc-100/70 dark:bg-zinc-900/60 ring-1 ring-inset ring-black/5 dark:ring-white/5 overflow-hidden">
        {/* Category Pill in Corner */}
        <div className="absolute bottom-2.5 left-2.5 z-10 flex items-center gap-1 px-2 py-0.5 rounded bg-background/90 text-[10px] font-mono font-medium text-muted-foreground border border-border/60">
          <CategoryIcon className="w-3 h-3 text-muted-foreground" />
          <span>{formatCategoryLabel(product.category)}</span>
        </div>

        {/* Out of stock label */}
        {isOutOfStock && (
          <div className="absolute top-2.5 right-2.5 z-10 px-2 py-0.5 rounded bg-zinc-900/90 dark:bg-zinc-100/90 text-zinc-100 dark:text-zinc-900 text-[10px] font-mono font-bold uppercase tracking-wider">
            Sin Stock
          </div>
        )}

        {resolvedImgUrl && !imgError ? (
          <img
            src={resolvedImgUrl}
            alt={product.model_name}
            decoding="async"
            loading="lazy"
            onLoad={() => setImgLoaded(true)}
            onError={() => setImgError(true)}
            className={`w-full h-full object-contain transition-all duration-300 ${
              isOutOfStock ? "grayscale contrast-75 opacity-50" : ""
            } ${!imgLoaded ? "opacity-0 scale-95" : "opacity-100 scale-100"}`}
          />
        ) : (
          <div className="flex flex-col items-center justify-center text-muted-foreground/50 gap-1.5 p-4 text-center">
            <Glasses className="w-8 h-8 opacity-40" />
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider">
              {product.brand}
            </span>
          </div>
        )}
      </div>

      {/* 3. Product Details & Pricing Ledger */}
      <div className="flex flex-col flex-1 p-4 pt-3 space-y-3">
        {/* Brand & Model */}
        <div className="space-y-1">
          <p className="text-[11px] font-mono font-bold uppercase tracking-wider text-muted-foreground">
            {product.brand}
          </p>
          <h3 className="font-semibold text-sm text-foreground line-clamp-2 leading-snug tracking-tight">
            {product.model_name}
          </h3>
        </div>

        {/* Pricing & Ledger */}
        <div className="mt-auto pt-2 border-t border-border/50 space-y-1">
          <div className="flex items-baseline gap-2 font-mono">
            {effectivePrice ? (
              <>
                <span className="text-lg font-black text-foreground tracking-tight">
                  {formatCLP(effectivePrice)}
                </span>
                {hasDiscount && (
                  <span className="text-xs text-muted-foreground line-through font-normal">
                    {formatCLP(product.current_price_normal)}
                  </span>
                )}
              </>
            ) : (
              <span className="text-xs font-medium text-muted-foreground italic">
                Precio a consultar
              </span>
            )}
          </div>

          {hasDiscount && savingsAmount > 0 && (
            <p className="text-[11px] font-mono text-emerald-600 dark:text-emerald-400 font-semibold">
              Ahorras {formatCLP(savingsAmount)}
            </p>
          )}
        </div>

        {/* 4. Action Strip */}
        <div className="grid grid-cols-2 gap-2 pt-1">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onViewHistory(product.id)}
            className="text-xs gap-1.5 h-9 rounded-xl font-medium border-border/80 hover:bg-muted text-foreground transition-all"
          >
            <History className="w-3.5 h-3.5 text-muted-foreground" />
            <span>Historial</span>
          </Button>

          {isOutOfStock ? (
            <Button
              variant="secondary"
              size="sm"
              disabled
              className="text-xs h-9 rounded-xl opacity-60 cursor-not-allowed bg-muted"
            >
              Sin Stock
            </Button>
          ) : (
            <a
              href={product.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-1 text-xs font-bold h-9 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-xs"
            >
              <span>Ver Tienda</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </div>
    </article>
  );
}

export function ProductCardSkeleton() {
  return (
    <article className="group relative flex flex-col bg-card text-card-foreground rounded-2xl border border-border/80 overflow-hidden animate-pulse">
      {/* 1. Header Specimen Skeleton */}
      <div className="flex items-center justify-between p-3 pb-2 z-10">
        <div className="w-24 h-5 rounded-full bg-muted/80" />
        <div className="w-10 h-5 rounded-md bg-muted/60" />
      </div>

      {/* 2. Canvas Stage Skeleton */}
      <div className="relative aspect-[4/3] w-full p-4 flex items-center justify-center bg-zinc-100/70 dark:bg-zinc-900/60 ring-1 ring-inset ring-black/5 dark:ring-white/5 overflow-hidden">
        <div className="w-28 h-12 rounded-xl bg-muted/40" />
        <div className="absolute bottom-2.5 left-2.5 w-14 h-4 rounded bg-background/90 border border-border/60" />
      </div>

      {/* 3. Details & Pricing Ledger Skeleton */}
      <div className="flex flex-col flex-1 p-4 pt-3 space-y-3">
        <div className="space-y-1.5">
          <div className="w-16 h-3 rounded bg-muted/80" />
          <div className="w-full h-4 rounded bg-muted/90" />
          <div className="w-3/5 h-4 rounded bg-muted/70" />
        </div>

        <div className="mt-auto pt-2 border-t border-border/50 space-y-1.5">
          <div className="flex items-baseline gap-2">
            <div className="w-24 h-6 rounded bg-muted/90" />
            <div className="w-14 h-3.5 rounded bg-muted/50" />
          </div>
          <div className="w-20 h-3 rounded bg-emerald-500/20" />
        </div>

        {/* 4. Action Buttons Skeleton */}
        <div className="grid grid-cols-2 gap-2 pt-1">
          <div className="h-9 rounded-xl bg-muted/60 border border-border/80" />
          <div className="h-9 rounded-xl bg-muted/90" />
        </div>
      </div>
    </article>
  );
}