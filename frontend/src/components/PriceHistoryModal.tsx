import React, { useEffect, useState, useId } from "react";
import { Dialog, DialogContent, DialogTitle } from "./ui/dialog";
import { StoreBadge } from "./StoreBadge";
import { formatCLP } from "@/lib/utils";
import {
  TrendingDown,
  TrendingUp,
  History,
  ExternalLink,
  Store,
  Sparkles,
} from "lucide-react";

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
  current_price_discount?: number;
  current_in_stock?: boolean;
  price_snapshots: Snapshot[];
}

interface StorePriceMatch {
  product_id: string;
  store: string;
  brand: string;
  model_name: string;
  url: string;
  image_url?: string;
  price_normal?: number;
  price_discount?: number;
  effective_price?: number;
  discount_percentage?: number;
  is_in_stock: boolean;
  savings_vs_base: number;
  is_base_product: boolean;
}

interface ProductComparisonResponse {
  canonical_key: string;
  base_product_id: string;
  brand: string;
  canonical_model: string;
  category: string;
  total_stores: number;
  total_listings: number;
  cheapest_store?: string;
  lowest_price?: number;
  highest_price?: number;
  max_arbitrage_amount: number;
  max_arbitrage_percentage: number;
  matches: StorePriceMatch[];
}

interface Props {
  productId: string | null;
  onClose: () => void;
  apiBaseUrl: string;
  apiKey: string;
}

interface ChartPoint {
  date: Date;
  dateStr: string;
  priceNormal: number;
  priceDiscount: number | null;
  effectivePrice: number;
  discountPct: number | null;
  isInStock: boolean;
}

export function PriceHistoryModal({ productId, onClose, apiBaseUrl, apiKey }: Props) {
  const [loading, setLoading] = useState(true);
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [comparison, setComparison] = useState<ProductComparisonResponse | null>(null);
  const [hoveredPoint, setHoveredPoint] = useState<ChartPoint | null>(null);
  const [activeTab, setActiveTab] = useState<"history" | "compare">("history");

  useEffect(() => {
    if (!productId) return;
    setLoading(true);
    setHoveredPoint(null);

    const headers = { "X-API-Key": apiKey };

    Promise.all([
      fetch(`${apiBaseUrl}/api/products/${productId}`, { headers }).then((r) =>
        r.ok ? r.json() : null
      ),
      fetch(`${apiBaseUrl}/api/products/${productId}/compare`, { headers }).then((r) =>
        r.ok ? r.json() : null
      ),
    ])
      .then(([prodData, compData]) => {
        setProduct(prodData);
        setComparison(compData);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error fetching product history & comparison:", err);
        setLoading(false);
      });
  }, [productId, apiBaseUrl, apiKey]);

  if (!productId) return null;

  // Process timeline data for the SVG chart
  const snapshots = (product?.price_snapshots || []).slice().sort(
    (a, b) => new Date(a.scraped_at).getTime() - new Date(b.scraped_at).getTime()
  );

  const chartPoints: ChartPoint[] = snapshots.map((s) => ({
    date: new Date(s.scraped_at),
    dateStr: new Date(s.scraped_at).toLocaleDateString("es-CL", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }),
    priceNormal: s.price_normal,
    priceDiscount: s.price_discount,
    effectivePrice: s.price_discount || s.price_normal,
    discountPct: s.discount_percentage,
    isInStock: s.is_in_stock,
  }));

  const allEffectivePrices = chartPoints.map((p) => p.effectivePrice);
  const minHistoricalPrice = allEffectivePrices.length > 0 ? Math.min(...allEffectivePrices) : 0;
  const maxHistoricalPrice = allEffectivePrices.length > 0 ? Math.max(...allEffectivePrices) : 0;
  const currentEffectivePrice =
    chartPoints.length > 0
      ? chartPoints[chartPoints.length - 1].effectivePrice
      : product?.current_price_discount || product?.current_price_normal || 0;

  const isCurrentAtAllTimeLow =
    minHistoricalPrice > 0 && currentEffectivePrice <= minHistoricalPrice;

  // Other store matches excluding the current product
  const otherStoreMatches = (comparison?.matches || []).filter(
    (m) => m.product_id !== product?.id
  );

  return (
    <Dialog open={!!productId} onOpenChange={(open) => !open && onClose()}>
      <DialogContent onClose={onClose} className="p-0 overflow-hidden max-w-3xl border-border bg-card">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-muted/30">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
              <History className="w-4 h-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-bold text-foreground">
                Análisis de Precios & Comparador Multi-Tienda
              </DialogTitle>
              <p className="text-xs text-muted-foreground">
                Monitoreo histórico y arbitraje en ópticas chilenas
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center bg-muted/60 p-1 rounded-xl border border-border/80 text-xs font-semibold">
            <button
              onClick={() => setActiveTab("history")}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                activeTab === "history"
                  ? "bg-background text-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Historial de Precios
            </button>
            <button
              onClick={() => setActiveTab("compare")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                activeTab === "compare"
                  ? "bg-background text-foreground shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <span>Comparar Tiendas</span>
              {otherStoreMatches.length > 0 && (
                <span className="bg-primary/20 text-primary font-mono text-[10px] px-1.5 py-0.2 rounded-full font-bold">
                  {comparison?.total_stores}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 max-h-[80vh] overflow-y-auto space-y-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground gap-3">
              <div className="w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin" />
              <p className="text-sm font-medium">Analizando historial y tiendas cruzadas...</p>
            </div>
          ) : product ? (
            <>
              {/* Product Specimen Summary Banner */}
              <div className="flex items-center gap-4 bg-muted/20 p-4 rounded-2xl border border-border">
                {product.image_url ? (
                  <img
                    src={product.image_url}
                    alt={product.model_name}
                    className="w-16 h-16 object-contain bg-white rounded-xl p-1.5 border border-border/60 shadow-xs"
                  />
                ) : (
                  <div className="w-16 h-16 bg-muted rounded-xl flex items-center justify-center text-xs font-bold text-muted-foreground">
                    {product.brand}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <StoreBadge store={product.store} />
                    <span className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
                      {product.brand}
                    </span>
                  </div>
                  <h4 className="font-semibold text-sm text-foreground truncate">
                    {product.model_name}
                  </h4>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className="text-lg font-black font-mono text-foreground">
                      {formatCLP(currentEffectivePrice)}
                    </span>
                    {product.current_price_discount &&
                      product.current_price_normal &&
                      product.current_price_discount < product.current_price_normal && (
                        <span className="text-xs font-mono line-through text-muted-foreground">
                          {formatCLP(product.current_price_normal)}
                        </span>
                      )}
                  </div>
                </div>
                <a
                  href={product.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-bold px-3.5 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-xs shrink-0"
                >
                  <span>Ver Tienda</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>

              {/* TAB 1: HISTORICAL PRICE FLUCTUATIONS (KEEPA/KNASTA STYLE) */}
              {activeTab === "history" && (
                <div className="space-y-6">
                  {/* Historical Key Metrics Cards */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-3.5 rounded-xl border border-border bg-card/60 space-y-1">
                      <p className="text-[11px] font-mono font-semibold uppercase tracking-wider text-muted-foreground">
                        Mínimo Histórico
                      </p>
                      <p className="text-base font-black font-mono text-emerald-600 dark:text-emerald-400">
                        {minHistoricalPrice > 0 ? formatCLP(minHistoricalPrice) : "N/D"}
                      </p>
                      {isCurrentAtAllTimeLow && (
                        <span className="inline-block text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-600">
                          ★ Mejor Precio Hoy
                        </span>
                      )}
                    </div>

                    <div className="p-3.5 rounded-xl border border-border bg-card/60 space-y-1">
                      <p className="text-[11px] font-mono font-semibold uppercase tracking-wider text-muted-foreground">
                        Máximo Registrado
                      </p>
                      <p className="text-base font-black font-mono text-foreground">
                        {maxHistoricalPrice > 0 ? formatCLP(maxHistoricalPrice) : "N/D"}
                      </p>
                      <span className="inline-block text-[10px] font-mono text-muted-foreground">
                        {chartPoints.length} mediciones
                      </span>
                    </div>

                    <div className="p-3.5 rounded-xl border border-border bg-card/60 space-y-1">
                      <p className="text-[11px] font-mono font-semibold uppercase tracking-wider text-muted-foreground">
                        Disponibilidad
                      </p>
                      <p
                        className={`text-base font-black font-mono ${
                          product.current_in_stock !== false
                            ? "text-emerald-600 dark:text-emerald-400"
                            : "text-rose-600 dark:text-rose-400"
                        }`}
                      >
                        {product.current_in_stock !== false ? "En Stock" : "Agotado"}
                      </p>
                      <span className="inline-block text-[10px] font-mono text-muted-foreground capitalize">
                        {product.store}
                      </span>
                    </div>
                  </div>

                  {/* Interactive SVG Price Chart */}
                  <div className="p-4 rounded-2xl border border-border bg-zinc-50 dark:bg-zinc-950/60 space-y-3">
                    <div className="flex items-center justify-between">
                      <h5 className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                        <TrendingDown className="w-4 h-4 text-primary" />
                        Serie Temporal de Fluctuaciones
                      </h5>
                      {hoveredPoint ? (
                        <div className="text-right font-mono text-xs">
                          <span className="text-muted-foreground mr-2">{hoveredPoint.dateStr}:</span>
                          <span className="font-bold text-foreground">
                            {formatCLP(hoveredPoint.effectivePrice)}
                          </span>
                          {hoveredPoint.discountPct && (
                            <span className="text-emerald-600 ml-1.5 font-bold">
                              (-{hoveredPoint.discountPct}%)
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-[11px] font-mono text-muted-foreground">
                          Pasa el cursor sobre la gráfica
                        </span>
                      )}
                    </div>

                    {chartPoints.length > 0 ? (
                      <div className="relative w-full aspect-[21/9] sm:aspect-[24/8] select-none">
                        <PriceSvgChart
                          points={chartPoints}
                          onHoverPoint={setHoveredPoint}
                          hoveredPoint={hoveredPoint}
                        />
                      </div>
                    ) : (
                      <div className="py-12 text-center text-xs text-muted-foreground">
                        No hay suficientes registros temporales aún.
                      </div>
                    )}
                  </div>

                  {/* Historical Snapshots Raw Ledger */}
                  <div>
                    <h5 className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground mb-3">
                      Capturas Registradas ({snapshots.length})
                    </h5>
                    <div className="space-y-2">
                      {snapshots.map((snap, idx) => {
                        const isDiscount =
                          snap.price_discount && snap.price_discount < snap.price_normal;
                        const dateFormatted = new Date(snap.scraped_at).toLocaleString("es-CL", {
                          dateStyle: "medium",
                          timeStyle: "short",
                        });

                        return (
                          <div
                            key={snap.id || idx}
                            className="flex items-center justify-between p-3 rounded-xl border border-border bg-card/60 hover:bg-muted/30 transition-colors text-sm"
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
                                <p className="font-mono text-xs text-muted-foreground">
                                  {dateFormatted}
                                </p>
                                <span
                                  className={`inline-block text-xs font-medium ${
                                    snap.is_in_stock ? "text-emerald-600" : "text-rose-600"
                                  }`}
                                >
                                  {snap.is_in_stock ? "● En Stock" : "○ Agotado"}
                                </span>
                              </div>
                            </div>

                            <div className="text-right font-mono">
                              {isDiscount ? (
                                <div>
                                  <span className="font-bold text-emerald-600">
                                    {formatCLP(snap.price_discount)}
                                  </span>
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
                                <span className="font-bold text-foreground">
                                  {formatCLP(snap.price_normal)}
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: MULTI-STORE CROSS-STORE COMPARISON & ARBITRAGE (FEATURE 1) */}
              {activeTab === "compare" && (
                <div className="space-y-6">
                  {/* Arbitrage Summary Banner */}
                  {comparison && comparison.max_arbitrage_amount > 0 ? (
                    <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/25 flex items-start gap-3">
                      <div className="w-8 h-8 rounded-xl bg-emerald-500/20 text-emerald-600 flex items-center justify-center shrink-0 mt-0.5">
                        <Sparkles className="w-4 h-4" />
                      </div>
                      <div className="space-y-1">
                        <h5 className="text-sm font-bold text-emerald-700 dark:text-emerald-300">
                          Oportunidad de Arbitraje Detectada
                        </h5>
                        <p className="text-xs text-emerald-800 dark:text-emerald-200 leading-relaxed">
                          Puedes ahorrar hasta{" "}
                          <strong className="font-mono">
                            {formatCLP(comparison.max_arbitrage_amount)}
                          </strong>{" "}
                          ({comparison.max_arbitrage_percentage}% de diferencia) comprando este
                          mismo modelo en{" "}
                          <strong className="capitalize">{comparison.cheapest_store}</strong> en
                          lugar de la tienda con mayor precio.
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="p-4 rounded-2xl bg-muted/30 border border-border flex items-center gap-3 text-xs text-muted-foreground">
                      <Store className="w-5 h-5 text-primary shrink-0" />
                      <span>
                        Este modelo fue identificado en {comparison?.total_stores || 1}{" "}
                        {comparison?.total_stores === 1 ? "tienda" : "tiendas"} con{" "}
                        {comparison?.total_listings || 1} opciones en catálogo.
                      </span>
                    </div>
                  )}

                  {/* Multi-Store Comparison Listings */}
                  <div className="space-y-3">
                    <h5 className="text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground">
                      Comparativa por Óptica en Chile ({comparison?.matches.length || 0})
                    </h5>

                    {comparison?.matches && comparison.matches.length > 0 ? (
                      comparison.matches.map((item, idx) => {
                        const isCheapest =
                          comparison.lowest_price && item.effective_price === comparison.lowest_price;
                        const isCurrentBase = item.product_id === product.id;

                        return (
                          <div
                            key={item.product_id || idx}
                            className={`p-4 rounded-2xl border transition-all flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 ${
                              isCurrentBase
                                ? "bg-primary/5 border-primary/30 ring-1 ring-primary/20"
                                : "bg-card border-border/80 hover:border-foreground/20 shadow-xs"
                            }`}
                          >
                            <div className="flex items-center gap-3 min-w-0 flex-1">
                              <StoreBadge store={item.store} />
                              <div className="min-w-0">
                                <div className="flex items-center gap-2">
                                  <h6 className="font-semibold text-sm text-foreground truncate">
                                    {item.model_name}
                                  </h6>
                                  {isCurrentBase && (
                                    <span className="text-[10px] font-mono bg-primary/20 text-primary px-2 py-0.2 rounded-md font-bold shrink-0">
                                      Estás viendo este
                                    </span>
                                  )}
                                  {isCheapest && (
                                    <span className="text-[10px] font-mono bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 px-2 py-0.2 rounded-md font-bold shrink-0 flex items-center gap-1">
                                      ★ Mejor Precio
                                    </span>
                                  )}
                                </div>
                                <div className="flex items-center gap-2 mt-0.5 text-xs text-muted-foreground font-mono">
                                  <span
                                    className={
                                      item.is_in_stock ? "text-emerald-600" : "text-rose-600"
                                    }
                                  >
                                    {item.is_in_stock ? "● En Stock" : "○ Sin Stock"}
                                  </span>
                                  {item.savings_vs_base > 0 && (
                                    <span className="text-emerald-600 font-bold">
                                      · Ahorras {formatCLP(item.savings_vs_base)}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Price and Action Button */}
                            <div className="flex items-center justify-between sm:justify-end gap-4 w-full sm:w-auto pt-2 sm:pt-0 border-t sm:border-t-0 border-border/60">
                              <div className="text-left sm:text-right font-mono">
                                <p className="text-base font-black text-foreground">
                                  {item.effective_price
                                    ? formatCLP(item.effective_price)
                                    : "A consultar"}
                                </p>
                                {item.price_discount &&
                                  item.price_normal &&
                                  item.price_discount < item.price_normal && (
                                    <p className="text-xs line-through text-muted-foreground">
                                      {formatCLP(item.price_normal)}
                                    </p>
                                  )}
                              </div>

                              <a
                                href={item.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className={`inline-flex items-center gap-1.5 text-xs font-bold px-4 py-2 rounded-xl transition-all shadow-xs shrink-0 ${
                                  isCheapest
                                    ? "bg-emerald-600 text-white hover:bg-emerald-700"
                                    : "bg-primary text-primary-foreground hover:bg-primary/90"
                                }`}
                              >
                                <span>Ver en {item.store.toUpperCase()}</span>
                                <ExternalLink className="w-3.5 h-3.5" />
                              </a>
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <p className="text-xs text-muted-foreground text-center py-6">
                        No se encontraron otras publicaciones para este modelo en otras ópticas.
                      </p>
                    )}
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-rose-500 text-center py-8">
              No se pudo cargar la información del producto.
            </p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Interactive SVG Price Graph Component
interface PriceSvgChartProps {
  points: ChartPoint[];
  onHoverPoint: (pt: ChartPoint | null) => void;
  hoveredPoint: ChartPoint | null;
}

function PriceSvgChart({ points, onHoverPoint, hoveredPoint }: PriceSvgChartProps) {
  const gradientId = useId();
  if (!points || points.length === 0) return null;

  const width = 600;
  const height = 180;
  const padTop = 20;
  const padBottom = 30;
  const padLeft = 65;
  const padRight = 20;

  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  const prices = points.map((p) => p.effectivePrice);
  const minP = Math.min(...prices);
  const maxP = Math.max(...prices);
  const priceRange = maxP === minP ? 1000 : maxP - minP;

  // Add 10% breathing room top and bottom
  const yMin = Math.max(0, minP - priceRange * 0.1);
  const yMax = maxP + priceRange * 0.1;
  const ySpan = yMax - yMin;

  const getX = (index: number) => {
    if (points.length <= 1) return padLeft + chartW / 2;
    return padLeft + (index / (points.length - 1)) * chartW;
  };

  const getY = (price: number) => {
    return padTop + chartH - ((price - yMin) / ySpan) * chartH;
  };

  // Build SVG Path
  const coordinates = points.map((p, idx) => ({
    x: getX(idx),
    y: getY(p.effectivePrice),
    point: p,
  }));

  const pathD = coordinates.reduce((acc, curr, idx) => {
    if (idx === 0) return `M ${curr.x} ${curr.y}`;
    return `${acc} L ${curr.x} ${curr.y}`;
  }, "");

  const areaD = `${pathD} L ${coordinates[coordinates.length - 1].x} ${
    padTop + chartH
  } L ${coordinates[0].x} ${padTop + chartH} Z`;

  // Grid levels
  const midP = Math.round((maxP + minP) / 2);
  const gridLevels = [
    { label: formatCLP(maxP), y: getY(maxP) },
    { label: formatCLP(midP), y: getY(midP) },
    { label: formatCLP(minP), y: getY(minP) },
  ];

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-full overflow-visible"
      onMouseLeave={() => onHoverPoint(null)}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#10b981" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
        </linearGradient>
      </defs>

      {/* Background Grid Lines */}
      {gridLevels.map((lvl, idx) => (
        <g key={idx} className="opacity-40">
          <line
            x1={padLeft}
            y1={lvl.y}
            x2={width - padRight}
            y2={lvl.y}
            stroke="currentColor"
            strokeDasharray="3 3"
            strokeWidth="0.8"
            className="text-border"
          />
          <text
            x={padLeft - 8}
            y={lvl.y + 3}
            textAnchor="end"
            fontSize="9"
            fontFamily="monospace"
            className="fill-muted-foreground"
          >
            {lvl.label}
          </text>
        </g>
      ))}

      {/* Filled Area Gradient */}
      <path d={areaD} fill={`url(#${gradientId})`} />

      {/* Main Curve Line */}
      <path
        d={pathD}
        fill="none"
        stroke="#10b981"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Data Points and Hover Target Hitboxes */}
      {coordinates.map((coord, idx) => {
        const isHovered = hoveredPoint === coord.point;
        const isMin = coord.point.effectivePrice === minP;

        return (
          <g
            key={idx}
            className="cursor-pointer"
            onMouseEnter={() => onHoverPoint(coord.point)}
          >
            {/* Expanded invisible hover hitbox */}
            <circle cx={coord.x} cy={coord.y} r="14" fill="transparent" />

            {/* Visual Dot */}
            <circle
              cx={coord.x}
              cy={coord.y}
              r={isHovered ? 6 : isMin ? 4.5 : 3.5}
              fill={isMin ? "#10b981" : "#ffffff"}
              stroke={isMin ? "#ffffff" : "#10b981"}
              strokeWidth={isHovered ? 3 : 2}
              className="transition-all duration-150"
            />

            {/* X-axis Date Label (First, Middle, Last) */}
            {(idx === 0 || idx === coordinates.length - 1 || idx === Math.floor(coordinates.length / 2)) && (
              <text
                x={coord.x}
                y={padTop + chartH + 18}
                textAnchor={idx === 0 ? "start" : idx === coordinates.length - 1 ? "end" : "middle"}
                fontSize="9"
                fontFamily="monospace"
                className="fill-muted-foreground"
              >
                {coord.point.dateStr.split(",")[0]}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}