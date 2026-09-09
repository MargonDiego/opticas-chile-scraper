import React from "react";
import { StoreBadge } from "./StoreBadge";
import { formatCLP } from "@/lib/utils";
import { ExternalLink, History, Sparkles } from "lucide-react";
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

export function ProductCard({ product, onViewHistory }: Props) {
  const hasDiscount =
    product.current_price_discount &&
    product.current_price_normal &&
    product.current_price_discount < product.current_price_normal;

  const discountPct = hasDiscount
    ? Math.round(
        ((product.current_price_normal! - product.current_price_discount!) /
          product.current_price_normal!) *
          100
      )
    : null;

  return (
    <div className="group relative flex flex-col bg-card text-card-foreground rounded-2xl border border-border overflow-hidden hover:border-primary/50 hover:shadow-xl hover:shadow-primary/5 transition-all duration-300">
      {/* Top badges */}
      <div className="flex items-center justify-between p-3.5 pb-0 z-10">
        <StoreBadge store={product.store} />
        {hasDiscount && (
          <span className="inline-flex items-center gap-1 bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 text-xs font-bold px-2 py-0.5 rounded-full">
            <Sparkles className="w-3 h-3" /> -{discountPct}%
          </span>
        )}
      </div>

      {/* Image Container */}
      <div className="relative aspect-square w-full p-6 flex items-center justify-center bg-white dark:bg-muted/10 overflow-hidden my-2">
        {product.image_url ? (
          <img
            src={product.image_url}
            alt={product.model_name}
            className="w-full h-full object-contain transform group-hover:scale-105 transition-transform duration-300"
            loading="lazy"
          />
        ) : (
          <div className="flex flex-col items-center justify-center text-muted-foreground gap-1">
            <span className="text-3xl font-extrabold opacity-20">{product.brand}</span>
            <span className="text-xs">Sin imagen</span>
          </div>
        )}
      </div>

      {/* Details */}
      <div className="flex flex-col flex-1 p-4 pt-2">
        <div className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
          {product.brand}
        </div>
        <h3 className="font-semibold text-sm line-clamp-2 mt-0.5 group-hover:text-primary transition-colors">
          {product.model_name}
        </h3>

        {/* Pricing */}
        <div className="mt-auto pt-4">
          <div className="flex items-baseline gap-2">
            {hasDiscount ? (
              <>
                <span className="text-lg font-extrabold text-emerald-600 dark:text-emerald-400">
                  {formatCLP(product.current_price_discount)}
                </span>
                <span className="text-xs text-muted-foreground line-through">
                  {formatCLP(product.current_price_normal)}
                </span>
              </>
            ) : (
              <span className="text-lg font-extrabold text-foreground">
                {formatCLP(product.current_price_normal)}
              </span>
            )}
          </div>

          {/* Action buttons */}
          <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-border/60">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onViewHistory(product.id)}
              className="text-xs gap-1.5 h-8 font-medium"
            >
              <History className="w-3.5 h-3.5" /> Historial
            </Button>
            <a
              href={product.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-1.5 text-xs font-medium h-8 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow-sm"
            >
              Comprar <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}