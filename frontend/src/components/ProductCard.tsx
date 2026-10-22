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
      className={cn(
        "flex flex-col overflow-hidden rounded-lg border border-border bg-card",
        "transition-[border-color,box-shadow] duration-fast ease-out",
        "hover-supported:hover:border-border-strong hover-supported:hover:shadow-overlay"
      )}
    >
      {/* 1. Image well — white in both themes so transparent frame PNGs read clean. */}
      <div className="m-3 flex aspect-[4/3] items-center justify-center rounded-md bg-white well-ring">
        {resolvedImgUrl && !imgError ? (
          <img
            src={resolvedImgUrl}
            alt={product.model_name}
            decoding="async"
            loading="lazy"
            onLoad={() => setImgLoaded(true)}
            onError={() => setImgError(true)}
            className={cn(
              "h-full w-full object-contain p-4 transition-opacity duration-slow ease-out",
              isOutOfStock && "grayscale opacity-60",
              !imgLoaded && "opacity-0"
            )}
          />
        ) : (
          <div className="flex flex-col items-center justify-center gap-1.5 p-4 text-center">
            <Glasses
              className="h-4 w-4 text-muted-foreground opacity-40"
              aria-hidden="true"
            />
            <span className="text-body-sm text-on-white">{product.brand}</span>
          </div>
        )}
      </div>

      {/* 2. Content */}
      <div className="flex flex-1 flex-col gap-3 px-4 pb-4">
        {hasDiscount && (
          <span className="w-fit rounded-sm bg-success-tint px-2 py-1 text-body-sm font-semibold tabular-nums text-success-foreground">
            -{discountPercent}
            <span className="sr-only"> de descuento</span>
          </span>
        )}

        {/* Chain + category — icon and label, never a hue. */}
        <div className="flex items-center justify-between gap-2">
          <StoreBadge store={product.store} />
          <span className="inline-flex shrink-0 items-center gap-1.5 text-body-sm text-muted-foreground">
            <CategoryIcon className="h-3.5 w-3.5" aria-hidden="true" />
            {formatCategoryLabel(product.category)}
          </span>
        </div>

        {/* Brand + model */}
        <div className="min-w-0">
          <p className="text-body-sm text-muted-foreground">{product.brand}</p>
          <h3 className="mt-0.5 line-clamp-2 text-title text-foreground">
            {product.model_name}
          </h3>
        </div>

        {/* Price block */}
        <div className="mt-auto space-y-1 pt-1">
          <div className="flex flex-wrap items-baseline gap-2">
            {effectivePrice ? (
              <>
                <span className="text-price tabular-nums text-foreground">
                  {formatCLP(effectivePrice)}
                </span>
                {hasDiscount && (
                  <span className="text-body-sm tabular-nums text-ink-subtle line-through">
                    {formatCLP(product.current_price_normal)}
                  </span>
                )}
              </>
            ) : (
              <span className="text-body-sm text-muted-foreground">
                Precio a consultar
              </span>
            )}
          </div>

          {hasDiscount && savingsAmount > 0 && (
            <p className="text-body-sm font-semibold text-success-foreground">
              Ahorrás {formatCLP(savingsAmount)}
            </p>
          )}

          {isOutOfStock && (
            <p className="text-body-sm text-muted-foreground">Sin stock</p>
          )}
        </div>

        {/* 3. Actions — 44px tall, both of them. */}
        <div className="grid grid-cols-2 gap-2">
          <Button
            type="button"
            variant="secondary"
            size="default"
            onClick={() => onViewHistory(product.id)}
            className="min-h-11 gap-1.5 px-3 pointer-fine:min-h-11"
          >
            <History className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Historial</span>
          </Button>

          {isOutOfStock ? (
            <Button
              type="button"
              variant="secondary"
              size="default"
              disabled
              className="min-h-11 gap-1.5 px-3 pointer-fine:min-h-11"
            >
              <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Ver Tienda</span>
            </Button>
          ) : (
            <a
              href={product.url}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                buttonVariants({ variant: "secondary", size: "default" }),
                "min-h-11 gap-1.5 px-3 pointer-fine:min-h-11"
              )}
            >
              <span>Ver Tienda</span>
              <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
            </a>
          )}
        </div>
      </div>
    </article>
  );
}

export function ProductCardSkeleton() {
  return (
    <article className="flex flex-col overflow-hidden rounded-lg border border-border bg-card animate-pulse">
      <div className="m-3 flex aspect-[4/3] items-center justify-center rounded-md bg-white well-ring">
        <div className="h-10 w-24 rounded-md bg-muted" />
      </div>

      <div className="flex flex-1 flex-col gap-3 px-4 pb-4">
        <div className="h-5 w-20 rounded-sm bg-muted" />

        <div className="flex items-center justify-between gap-2">
          <div className="h-4 w-24 rounded-sm bg-muted/80" />
          <div className="h-4 w-14 rounded-sm bg-muted/60" />
        </div>

        <div className="space-y-1.5">
          <div className="h-3.5 w-16 rounded-sm bg-muted/70" />
          <div className="h-4 w-full rounded-sm bg-muted/90" />
        </div>

        <div className="mt-auto space-y-2 pt-1">
          <div className="h-6 w-28 rounded-sm bg-muted/90" />
          <div className="h-3.5 w-24 rounded-sm bg-muted/60" />
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="h-11 rounded-md bg-muted/60" />
          <div className="h-11 rounded-md bg-muted/60" />
        </div>
      </div>
    </article>
  );
}
