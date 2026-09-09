import React, { useEffect, useState } from "react";
import { Button } from "./ui/button";
import { Dialog, DialogContent, DialogTitle } from "./ui/dialog";
import { formatCLP } from "@/lib/utils";
import { X, TrendingDown, TrendingUp, History, ExternalLink } from "lucide-react";

interface Snapshot {
  id: number;
  price_normal: number;
  price_discount: number | null;
  discount_percentage: number | null;
  is_in_stock: boolean;
  scraped_at: string;
}

interface ProductDetail {
  id: string;
  store: string;
  brand: string;
  model_name: string;
  category: string;
  url: string;
  image_url?: string;
  current_price_normal?: number;
  price_snapshots: Snapshot[];
}

interface Props {
  productId: string | null;
  onClose: () => void;
  apiBaseUrl: string;
  apiKey: string;
}

export function PriceHistoryModal({ productId, onClose, apiBaseUrl, apiKey }: Props) {
  const [loading, setLoading] = useState(true);
  const [product, setProduct] = useState<ProductDetail | null>(null);

  useEffect(() => {
    if (!productId) return;
    setLoading(true);

    fetch(`${apiBaseUrl}/api/products/${productId}`, {
      headers: { "X-API-Key": apiKey },
    })
      .then((res) => res.json())
      .then((data) => {
        setProduct(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching product detail:", err);
        setLoading(false);
      });
  }, [productId, apiBaseUrl, apiKey]);

  if (!productId) return null;

  return (
    <Dialog open={!!productId} onOpenChange={(open) => !open && onClose()}>
      <DialogContent onClose={onClose} className="p-0 overflow-hidden max-w-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-muted/20">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-primary" />
            <DialogTitle className="text-lg">Historial de Precios</DialogTitle>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 max-h-[75vh] overflow-y-auto">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground gap-3">
              <div className="w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin" />
              <p className="text-sm">Cargando serie temporal de precios...</p>
            </div>
          ) : product ? (
            <div className="space-y-6">
              {/* Product summary */}
              <div className="flex items-center gap-4 bg-muted/20 p-4 rounded-xl border border-border">
                {product.image_url ? (
                  <img
                    src={product.image_url}
                    alt={product.model_name}
                    className="w-16 h-16 object-contain bg-white rounded-lg p-1 border"
                  />
                ) : (
                  <div className="w-16 h-16 bg-muted rounded-lg flex items-center justify-center text-xs font-bold text-muted-foreground">
                    {product.brand}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <span className="text-xs uppercase tracking-wider font-semibold text-primary">{product.brand}</span>
                  <h4 className="font-semibold text-sm truncate">{product.model_name}</h4>
                  <p className="text-xs text-muted-foreground capitalize mt-0.5">Tienda: {product.store}</p>
                </div>
                <a
                  href={product.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                >
                  Ver Tienda <ExternalLink className="w-3 h-3" />
                </a>
              </div>

              {/* Price Snapshots Timeline */}
              <div>
                <h5 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3">
                  Registros Capturados ({product.price_snapshots?.length || 0})
                </h5>
                <div className="space-y-2">
                  {product.price_snapshots && product.price_snapshots.length > 0 ? (
                    product.price_snapshots.map((snap, idx) => {
                      const isDiscount = snap.price_discount && snap.price_discount < snap.price_normal;
                      const dateFormatted = new Date(snap.scraped_at).toLocaleString("es-CL", {
                        dateStyle: "medium",
                        timeStyle: "short",
                      });

                      return (
                        <div
                          key={snap.id || idx}
                          className="flex items-center justify-between p-3.5 rounded-xl border border-border bg-card/60 hover:bg-muted/30 transition-colors text-sm"
                        >
                          <div className="flex items-center gap-3">
                            {isDiscount ? (
                              <div className="w-8 h-8 rounded-full bg-emerald-500/15 text-emerald-600 flex items-center justify-center">
                                <TrendingDown className="w-4 h-4" />
                              </div>
                            ) : (
                              <div className="w-8 h-8 rounded-full bg-slate-500/15 text-slate-600 flex items-center justify-center">
                                <TrendingUp className="w-4 h-4" />
                              </div>
                            )}
                            <div>
                              <p className="font-medium text-xs text-muted-foreground">{dateFormatted}</p>
                              <span
                                className={`inline-block text-xs font-medium ${
                                  snap.is_in_stock ? "text-emerald-600" : "text-rose-600"
                                }`}
                              >
                                {snap.is_in_stock ? "● En Stock" : "○ Agotado"}
                              </span>
                            </div>
                          </div>

                          <div className="text-right">
                            {isDiscount ? (
                              <div>
                                <span className="font-bold text-emerald-600">{formatCLP(snap.price_discount)}</span>
                                <div className="flex items-center justify-end gap-1.5 mt-0.5">
                                  <span className="text-xs line-through text-muted-foreground">
                                    {formatCLP(snap.price_normal)}
                                  </span>
                                  <span className="text-[10px] bg-emerald-500/20 text-emerald-700 px-1.5 py-0.2 rounded font-bold">
                                    -{snap.discount_percentage}%
                                  </span>
                                </div>
                              </div>
                            ) : (
                              <span className="font-bold text-foreground">{formatCLP(snap.price_normal)}</span>
                            )}
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <p className="text-sm text-muted-foreground py-4 text-center">No hay variaciones previas registradas.</p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-rose-500 text-center py-6">No se pudo cargar la información del producto.</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}