import React, { useState } from "react";
import { StoreBadge } from "./StoreBadge";
import { formatCLP } from "@/lib/utils";
import { ExternalLink, History, Sparkles, Glasses, AlertCircle } from "lucide-react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";

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

export function ProductCard({ product, onViewHistory }: Props) {
  const [imgError, setImgError] = useState(false);
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

  return (
    <div className={`group relative flex flex-col bg-card text-card-foreground rounded-2xl border transition-all duration-300 overflow-hidden ${
      isOutOfStock 
        ? "border-border/60 opacity-85 hover:opacity-100" 
        : "border-border/80 hover:border-primary/40 shadow-sm hover:shadow-xl hover:shadow-primary/10"
    }`}>
      {/* Top Header / Badges */}
      <div className="flex items-center justify-between p-3.5 pb-2 z-10">
        <StoreBadge store={product.store} />
        <div className="flex items-center gap-1.5">
          {isOutOfStock && (
            <Badge variant="destructive" className="text-[10px] font-bold gap-1 px-2 py-0.5">
              <AlertCircle className="w-3 h-3" /> Sin Stock
            </Badge>
          )}
          {hasDiscount && (
            <span className="inline-flex items-center gap-1 bg-primary/20 text-foreground border border-primary/40 text-[11px] font-black px-2 py-0.5 rounded-full">
              <Sparkles className="w-3 h-3 text-primary" /> -{discountPct}%
            </span>
          )}
        </div>
      </div>

      {/* Image Container with robust fallback */}
      <div className="relative aspect-[4/3] w-full p-4 flex items-center justify-center bg-white dark:bg-muted/15 overflow-hidden">
        {resolvedImgUrl && !imgError ? (
          <img
            src={resolvedImgUrl}
            alt={product.model_name}
            onError={() => setImgError(true)}
            className={`w-full h-full object-contain transform group-hover:scale-105 transition-transform duration-300 ${
              isOutOfStock ? "grayscale contrast-75 opacity-70" : ""
            }`}
            loading="lazy"
          />
        ) : (
          <div className="flex flex-col items-center justify-center text-muted-foreground/60 gap-1.5 p-4 text-center">
            <div className="w-12 h-12 rounded-2xl bg-muted/50 flex items-center justify-center text-primary/40">
              <Glasses className="w-6 h-6" />
            </div>
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground/80">
              {product.brand}
            </span>
            <span className="text-[10px] text-muted-foreground/60">Catálogo {product.store.toUpperCase()}</span>
          </div>
        )}
      </div>

      {/* Details */}
      <div className="flex flex-col flex-1 p-4 pt-2.5">
        <div className="flex items-center justify-between font-mono text-[10.5px] font-bold uppercase tracking-wider text-muted-foreground">
          <span>{product.brand}</span>
          <span className="text-[9.5px] px-1.5 py-0.5 rounded bg-muted/60 text-muted-foreground font-semibold">
            {product.category}
          </span>
        </div>
        <h3 className="font-display font-bold text-sm tracking-tight line-clamp-2 mt-1.5 group-hover:text-primary transition-colors leading-snug">
          {product.model_name}
        </h3>

        {/* Pricing */}
        <div className="mt-auto pt-4">
          <div className="flex items-baseline gap-2 font-mono">
            {hasDiscount ? (
              <>
                <span className="text-lg font-black text-primary tracking-tight">
                  {formatCLP(product.current_price_discount)}
                </span>
                <span className="text-xs text-muted-foreground/80 line-through font-medium">
                  {formatCLP(product.current_price_normal)}
                </span>
              </>
            ) : product.current_price_normal ? (
              <span className="text-lg font-black text-foreground tracking-tight">
                {formatCLP(product.current_price_normal)}
              </span>
            ) : (
              <span className="text-sm font-bold text-muted-foreground italic">
                Precio no disponible
              </span>
            )}
          </div>

          {/* Action buttons */}
          <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-border/60">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onViewHistory(product.id)}
              className="text-xs gap-1.5 h-8 font-medium hover:bg-muted/80"
            >
              <History className="w-3.5 h-3.5" /> Historial
            </Button>
            {isOutOfStock ? (
              <Button
                variant="secondary"
                size="sm"
                disabled
                className="text-xs h-8 opacity-60 cursor-not-allowed"
              >
                Agotado
              </Button>
            ) : (
              <a
                href={product.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-1.5 text-xs font-bold h-8 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-sm"
              >
                Comprar <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}