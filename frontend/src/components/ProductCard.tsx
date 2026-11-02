import React, { useState } from "react";
import { StoreBadge } from "./StoreBadge";
import { cn, formatCLP } from "@/lib/utils";
import { History, Glasses, Sun, Eye, ArrowUpRight } from "lucide-react";
import { Button, buttonVariants } from "./ui/button";

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

/**
 * Discount percentage for the badge. The badge carries the *rate*; the
 * savings line below carries the *amount*. Showing the same figure twice is
 * noise, so the two never repeat each other.
 */
function formatDiscountPercent(normal: number, discount: number): string {
  if (!normal || discount >= normal) return "0%";
  return `${Math.round(((normal - discount) / normal) * 100)}%`;
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

  const savingsAmount = hasDiscount
    ? product.current_price_normal! - product.current_price_discount!
    : 0;

  const discountPercent = hasDiscount
    ? formatDiscountPercent(
        product.current_price_normal!,
        product.current_price_discount!,
      )
    : "0%";

  const effectivePrice = product.current_price_discount || product.current_price_normal;
  const CategoryIcon = getCategoryIcon(product.category);

  return (
    <article
      onClick={() => onViewHistory(product.id)}
      className={cn(
        "group relative flex flex-col overflow-hidden rounded-xl border border-border bg-card",
        "transition-all duration-fast ease-out cursor-pointer",
        "hover-supported:hover:border-border-strong hover-supported:hover:shadow-overlay"
      )}
    >
      {/* 1. Image container */}
      <div className="relative m-2 sm:m-3 flex aspect-[4/3] items-center justify-center rounded-lg bg-white dark:bg-white/95 well-ring overflow-hidden p-2">
        {/* Floating discount badge on image */}
        {hasDiscount && (
          <div className="absolute top-2 left-2 z-10">
            <span className="rounded-full bg-success px-2 py-0.5 text-[10px] sm:text-xs font-bold tabular-nums text-white shadow-xs">
              -{discountPercent}
            </span>
          </div>
        )}

        {/* Floating history icon button on top right of image */}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onViewHistory(product.id);
          }}
          aria-label={`Ver historial de precios de ${product.model_name}`}
          className="absolute top-2 right-2 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-black/50 hover:bg-black/75 text-white backdrop-blur-xs transition-colors shadow-xs"
        >
          <History className="h-3.5 w-3.5" aria-hidden="true" />
        </button>

        {resolvedImgUrl && !imgError ? (
          <img
            src={resolvedImgUrl}
            alt={product.model_name}
            decoding="async"
            loading="lazy"
            onLoad={() => setImgLoaded(true)}
            onError={() => setImgError(true)}
            className={cn(
              "h-full w-full object-contain transition-transform duration-slow ease-out group-hover:scale-105",
              isOutOfStock && "grayscale opacity-60",
              !imgLoaded && "opacity-0"
            )}
          />
        ) : (
          <div className="flex flex-col items-center justify-center gap-1 p-2 text-center">
            <Glasses
              className="h-5 w-5 text-zinc-400 opacity-60"
              aria-hidden="true"
            />
            <span className="text-[11px] font-medium text-zinc-600 truncate max-w-[120px]">{product.brand}</span>
          </div>
        )}
      </div>

      {/* 2. Content */}
      <div className="flex flex-1 flex-col gap-1.5 p-2.5 sm:px-3.5 sm:pb-3.5 sm:pt-1">
        {/* Store badge & Category */}
        <div className="flex items-center justify-between gap-1 text-[11px] sm:text-xs">
          <StoreBadge store={product.store} />
          <span className="inline-flex shrink-0 items-center gap-1 text-muted-foreground">
            <CategoryIcon className="h-3 w-3" aria-hidden="true" />
            <span className="hidden sm:inline">{formatCategoryLabel(product.category)}</span>
          </span>
        </div>

        {/* Brand + Model */}
        <div className="min-w-0">
          <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-muted-foreground truncate">
            {product.brand}
          </p>
          <h3 className="mt-0.5 line-clamp-2 text-xs sm:text-sm font-semibold text-foreground leading-snug min-h-[2rem]">
            {product.model_name}
          </h3>
        </div>

        {/* Price block */}
        <div className="mt-auto space-y-0.5 pt-1">
          <div className="flex flex-wrap items-baseline gap-1.5">
            {effectivePrice ? (
              <>
                <span className="text-sm sm:text-base font-extrabold tabular-nums text-foreground">
                  {formatCLP(effectivePrice)}
                </span>
                {hasDiscount && (
                  <span className="text-[10px] sm:text-xs tabular-nums text-muted-foreground line-through">
                    {formatCLP(product.current_price_normal)}
                  </span>
                )}
              </>
            ) : (
              <span className="text-xs text-muted-foreground font-medium">
                Precio a consultar
              </span>
            )}
          </div>

          {hasDiscount && savingsAmount > 0 && (
            <p className="text-[10px] sm:text-xs font-bold text-success-foreground truncate">
              Ahorras {formatCLP(savingsAmount)}
            </p>
          )}

          {isOutOfStock && (
            <p className="text-[10px] sm:text-xs font-medium text-destructive">Sin stock</p>
          )}
        </div>

        {/* 3. Actions — Single clean full-width button (No text truncation!) */}
        <div className="pt-1.5">
          {isOutOfStock ? (
            <Button
              type="button"
              variant="secondary"
              size="default"
              disabled
              className="w-full h-8 sm:h-9 text-xs rounded-lg opacity-50 justify-center"
            >
              <span>Agotado</span>
            </Button>
          ) : (
            <a
              href={product.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className={cn(
                buttonVariants({ variant: "default", size: "default" }),
                "w-full h-8 sm:h-9 text-xs font-semibold px-2 gap-1 rounded-lg justify-center shadow-xs"
              )}
            >
              <span>Ver en tienda</span>
              <ArrowUpRight className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            </a>
          )}
        </div>
      </div>
    </article>
  );
}

export function ProductCardSkeleton() {
  return (
    <article className="flex flex-col overflow-hidden rounded-xl border border-border bg-card animate-pulse">
      <div className="m-2 sm:m-3 flex aspect-[4/3] items-center justify-center rounded-lg bg-muted/60" />

      <div className="flex flex-1 flex-col gap-2 p-2.5 sm:px-3.5 sm:pb-3.5 sm:pt-1">
        <div className="flex items-center justify-between gap-2">
          <div className="h-3 w-16 rounded-sm bg-muted/80" />
          <div className="h-3 w-10 rounded-sm bg-muted/60" />
        </div>

        <div className="space-y-1">
          <div className="h-2.5 w-12 rounded-sm bg-muted/70" />
          <div className="h-3.5 w-full rounded-sm bg-muted/90" />
        </div>

        <div className="mt-auto space-y-1 pt-1">
          <div className="h-4 w-20 rounded-sm bg-muted/90" />
          <div className="h-2.5 w-16 rounded-sm bg-muted/60" />
        </div>

        <div className="pt-1.5">
          <div className="h-8 sm:h-9 w-full rounded-lg bg-muted/60" />
        </div>
      </div>
    </article>
  );
}
