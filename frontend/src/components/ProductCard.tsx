import React, { useState } from "react";
import { StoreBadge } from "./StoreBadge";
import { formatCLP } from "@/lib/utils";
import { ExternalLink, History, Tag, Glasses, Sun, Eye, ArrowUpRight } from "lucide-react";
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
    <div
      className={`group relative flex flex-col bg-card text-card-foreground rounded-2xl border transition-all duration-300 overflow-hidden ${
        isOutOfStock
          ? "border-border/60 opacity-80 hover:opacity-95 bg-card/60"
          : "border-border/70 hover:border-emerald-500/40 shadow-xs hover:shadow-xl hover:shadow-emerald-500/5 hover:-translate-y-1"
      }`}
    >
      {/* Top Floating Header: Store Badge & Discount Pill */}
      <div className="flex items-center justify-between p-3.5 pb-2 z-10">
        <StoreBadge store={product.store} />
        <div className="flex items-center gap-1.5">
          {hasDiscount && (
            <span className="inline-flex items-center gap-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/25 text-[10.5px] font-mono font-black px-2 py-0.5 rounded-full shadow-xs">
              <Tag className="w-2.5 h-2.5" />
              <span>-{discountPct}%</span>
            </span>
          )}
        </div>
      </div>

      {/* Image Canvas Container (OPV & Luxury Optical style) */}
      <div className="relative aspect-[4/3] w-full mx-auto p-4 flex items-center justify-center bg-gradient-to-b from-slate-100/70 via-slate-50/40 to-slate-100/60 dark:from-slate-900/40 dark:via-slate-950/20 dark:to-slate-900/40 overflow-hidden rounded-xl border-y border-border/30">
        {/* Category Chip in Image Corner */}
        <div className="absolute bottom-2.5 left-3 z-10 flex items-center gap-1 px-2 py-0.5 rounded-md bg-background/80 backdrop-blur-md border border-border/50 text-[10px] font-semibold text-muted-foreground shadow-xs">
          <CategoryIcon className="w-3 h-3 text-emerald-500" />
          <span>{formatCategoryLabel(product.category)}</span>
        </div>

        {/* Out of stock overlay badge */}
        {isOutOfStock && (
          <div className="absolute top-2.5 right-3 z-10 px-2.5 py-0.5 rounded-full bg-slate-900/80 dark:bg-slate-800/90 backdrop-blur-md text-slate-200 border border-slate-700 text-[10px] font-mono font-bold tracking-wider shadow-sm">
            Agotado
          </div>
        )}

        {resolvedImgUrl && !imgError ? (
          <img
            src={resolvedImgUrl}
            alt={product.model_name}
            onLoad={() => setImgLoaded(true)}
            onError={() => setImgError(true)}
            className={`w-full h-full object-contain transform group-hover:scale-105 transition-all duration-300 ${
              isOutOfStock ? "grayscale contrast-75 opacity-60" : "drop-shadow-sm"
            } ${!imgLoaded ? "opacity-0 scale-95" : "opacity-100 scale-100"}`}
            loading="lazy"
          />
        ) : (
          <div className="flex flex-col items-center justify-center text-muted-foreground/60 gap-1.5 p-4 text-center">
            <div className="w-12 h-12 rounded-2xl bg-muted/60 flex items-center justify-center text-muted-foreground">
              <Glasses className="w-6 h-6 opacity-40" />
            </div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground/80">
              {product.brand}
            </span>
          </div>
        )}
      </div>

      {/* Product Information & Details */}
      <div className="flex flex-col flex-1 p-4 pt-3">
        {/* Brand Tag */}
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-muted-foreground group-hover:text-emerald-500 transition-colors">
            {product.brand}
          </span>
        </div>

        {/* Model Title */}
        <h3 className="font-bold text-sm tracking-tight line-clamp-2 mt-1 text-foreground group-hover:text-emerald-500 transition-colors leading-snug">
          {product.model_name}
        </h3>

        {/* Pricing Hierarchy & Savings */}
        <div className="mt-auto pt-3">
          <div className="space-y-0.5">
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
              <p className="text-[10.5px] font-mono text-emerald-600 dark:text-emerald-400 font-semibold">
                Ahorras {formatCLP(savingsAmount)}
              </p>
            )}
          </div>

          {/* Action Footer Buttons */}
          <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-border/60">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onViewHistory(product.id)}
              className="text-xs gap-1.5 h-8.5 rounded-xl font-medium border-border/70 hover:bg-muted/70 hover:text-foreground transition-all"
            >
              <History className="w-3.5 h-3.5 text-muted-foreground" />
              <span>Historial</span>
            </Button>

            {isOutOfStock ? (
              <Button
                variant="secondary"
                size="sm"
                disabled
                className="text-xs h-8.5 rounded-xl opacity-60 cursor-not-allowed bg-muted/60"
              >
                Sin Stock
              </Button>
            ) : (
              <a
                href={product.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-1 text-xs font-bold h-8.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white transition-all shadow-xs hover:shadow-sm"
              >
                <span>Ver Oferta</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}