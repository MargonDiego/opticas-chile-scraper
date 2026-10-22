import React, { useEffect, useRef, useState } from "react";
import { Dialog } from "./ui/dialog";
import { buttonVariants } from "./ui/button";
import { StoreBadge } from "./StoreBadge";
import { cn, formatCLP } from "@/lib/utils";
import {
  Check,
  ExternalLink,
  Glasses,
  Store,
  Tag,
  TrendingDown,
  X,
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

/**
 * Chain display names. The API only carries the raw store key ("ryk",
 * "karun", …) but the prose needs the name a Chilean would recognise
 * ("Rotter & Krauss", "Karün"). `StoreBadge` carries the dot + name identity
 * for the rows; this map is only for the sentences.
 */
const STORE_LABELS: Record<string, string> = {
  gmo: "GMO",
  place_vendome: "Place Vendôme",
  ryk: "Rotter & Krauss",
  schilling: "Schilling",
  econopticas: "Econópticas",
  karun: "Karün",
  lentesplus: "Lentesplus",
};

function storeLabel(store?: string | null): string {
  if (!store) return "otra óptica";
  return STORE_LABELS[store.toLowerCase()] ?? store;
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

  const isInStock = product ? product.current_in_stock !== false : false;

  const hasDiscount = Boolean(
    product?.current_price_discount &&
      product?.current_price_normal &&
      product.current_price_discount < product.current_price_normal
  );

  // The row the reader is currently looking at, and the cheapest row next to it.
  const currentMatch = comparison?.matches?.find((m) => m.product_id === product?.id);
  const currentPrice = currentMatch?.effective_price ?? currentEffectivePrice;

  const cheapestMatch = (comparison?.matches || []).reduce<
    StorePriceMatch | undefined
  >((best, match) => {
    if (!best) return match;
    return (match.effective_price ?? Infinity) < (best.effective_price ?? Infinity)
      ? match
      : best;
  }, undefined);

  const savingsVsCurrent =
    cheapestMatch && currentPrice && cheapestMatch.effective_price
      ? currentPrice - cheapestMatch.effective_price
      : 0;

  const rangeLabel =
    chartPoints.length > 0
      ? `${chartPoints[0].dateStr.split(",")[0]} – ${
          chartPoints[chartPoints.length - 1].dateStr.split(",")[0]
        }`
      : "Sin mediciones";

  return (
    <Dialog
      open={!!productId}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      title={
        product ? `Precio de ${product.model_name}` : "Historial de precios"
      }
      description={
        <span className="text-body-sm">
          Historial de precios y comparación entre ópticas.
        </span>
      }
      footer={
        product ? (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="text-body-sm text-muted-foreground">Precio actual</p>
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="text-price-lg tabular-nums text-foreground">
                  {formatCLP(currentEffectivePrice)}
                </span>
                {hasDiscount && (
                  <span className="text-body-sm tabular-nums text-muted-foreground line-through">
                    {formatCLP(product.current_price_normal)}
                  </span>
                )}
              </div>
            </div>
            <a
              href={product.url}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                buttonVariants({ variant: "default", size: "default" }),
                "gap-1.5"
              )}
            >
              <span>Ver publicación</span>
              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
            </a>
          </div>
        ) : null
      }
    >
      {/* Tabs — sticky so they stay reachable while the ledger scrolls. */}
      <div className="sticky top-0 z-10 -mx-5 -mt-4 border-b border-border bg-card px-5 py-3">
        <div
          role="tablist"
          aria-label="Secciones del historial de precios"
          className="flex flex-wrap items-center gap-2"
        >
          <button
            type="button"
            role="tab"
            id="tab-historial"
            aria-selected={activeTab === "history"}
            aria-controls="panel-historial"
            onClick={() => setActiveTab("history")}
            className={`min-h-11 rounded-sm px-3 text-body-sm font-semibold transition-colors duration-fast ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
              activeTab === "history"
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Historial de precios
          </button>
          <button
            type="button"
            role="tab"
            id="tab-tiendas"
            aria-selected={activeTab === "compare"}
            aria-controls="panel-tiendas"
            onClick={() => setActiveTab("compare")}
            className={`inline-flex min-h-11 items-center gap-1.5 rounded-sm px-3 text-body-sm font-semibold transition-colors duration-fast ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
              activeTab === "compare"
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <span>Comparar tiendas</span>
            {comparison && comparison.total_stores > 0 && (
              <span className="rounded-sm bg-muted px-1.5 py-0.5 text-body-sm tabular-nums text-muted-foreground">
                {comparison.total_stores}
              </span>
            )}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground">
          <div
            className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent"
            aria-hidden="true"
          />
          <p className="text-body-sm">Cargando historial y comparación…</p>
        </div>
      ) : product ? (
        <div className="space-y-6 pt-4">
          {/* What the reader is looking at. */}
          <div className="flex items-center gap-4">
            {product.image_url ? (
              <img
                src={product.image_url}
                alt={product.model_name}
                loading="lazy"
                className="h-16 w-16 shrink-0 rounded-md bg-white p-1 object-contain well-ring"
              />
            ) : (
              <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-md bg-white well-ring">
                <Glasses
                  className="h-5 w-5 text-muted-foreground opacity-40"
                  aria-hidden="true"
                />
              </div>
            )}
            <div className="min-w-0">
              <StoreBadge store={product.store} />
              <p className="mt-0.5 text-body-sm text-muted-foreground">{product.brand}</p>
            </div>
          </div>

          <div
            id="panel-historial"
            role="tabpanel"
            aria-labelledby="tab-historial"
            hidden={activeTab !== "history"}
            className="space-y-6"
          >
            {/* One data readout, three figures, hairline separated. */}
            <div className="grid grid-cols-1 gap-y-3 sm:grid-cols-3">
              <div className="min-w-0 sm:pr-4">
                <p className="text-body-sm text-muted-foreground">Mínimo histórico</p>
                <p className="text-price tabular-nums text-foreground">
                  {minHistoricalPrice > 0 ? formatCLP(minHistoricalPrice) : "Sin datos"}
                </p>
                {isCurrentAtAllTimeLow && (
                  <span className="mt-1 inline-flex items-center gap-1 rounded-sm bg-success-tint px-2 py-1 text-body-sm font-semibold text-success-foreground">
                    <TrendingDown className="h-3.5 w-3.5" aria-hidden="true" />
                    Mejor precio hoy
                  </span>
                )}
              </div>

              <div className="min-w-0 sm:border-l sm:border-border sm:px-4">
                <p className="text-body-sm text-muted-foreground">Máximo registrado</p>
                <p className="text-price tabular-nums text-foreground">
                  {maxHistoricalPrice > 0 ? formatCLP(maxHistoricalPrice) : "Sin datos"}
                </p>
                <p className="text-body-sm tabular-nums text-muted-foreground">
                  {chartPoints.length} mediciones
                </p>
              </div>

              <div className="min-w-0 sm:border-l sm:border-border sm:pl-4">
                <p className="text-body-sm text-muted-foreground">Disponibilidad</p>
                <p
                  className={`inline-flex items-center gap-1.5 text-price tabular-nums ${
                    isInStock ? "text-success-foreground" : "text-destructive"
                  }`}
                >
                  {isInStock ? (
                    <Check className="h-4 w-4" aria-hidden="true" />
                  ) : (
                    <X className="h-4 w-4" aria-hidden="true" />
                  )}
                  {isInStock ? "En stock" : "Agotado"}
                </p>
                <p className="text-body-sm text-muted-foreground">
                  {storeLabel(product.store)}
                </p>
              </div>
            </div>

            {/* The series. Graphical only — every label lives in HTML. */}
            <div className="rounded-lg border border-border bg-surface-sunken p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-label text-muted-foreground">Serie de precios</h3>
                {hoveredPoint ? (
                  <p className="text-body-sm">
                    <span className="text-muted-foreground">{hoveredPoint.dateStr}</span>
                    <span className="ml-2 font-semibold tabular-nums text-foreground">
                      {formatCLP(hoveredPoint.effectivePrice)}
                    </span>
                    {hoveredPoint.discountPct ? (
                      <span className="ml-1.5 tabular-nums text-success-foreground">
                        -{hoveredPoint.discountPct}%
                      </span>
                    ) : null}
                  </p>
                ) : (
                  <p className="text-body-sm text-muted-foreground">
                    Toca la gráfica para ver cada medición
                  </p>
                )}
              </div>

              {chartPoints.length > 0 ? (
                <div className="mt-3">
                  <PriceSvgChart
                    points={chartPoints}
                    activePoint={hoveredPoint}
                    onPointChange={setHoveredPoint}
                    modelName={product.model_name}
                  />
                </div>
              ) : (
                <p className="py-12 text-center text-body-sm text-muted-foreground">
                  No hay suficientes registros temporales aún.
                </p>
              )}

              <div className="mt-3 flex flex-wrap items-baseline justify-between gap-2 text-body-sm text-muted-foreground">
                <span className="tabular-nums">
                  Mínimo{" "}
                  {minHistoricalPrice > 0 ? formatCLP(minHistoricalPrice) : "Sin datos"}
                </span>
                <span className="tabular-nums">
                  Máximo{" "}
                  {maxHistoricalPrice > 0 ? formatCLP(maxHistoricalPrice) : "Sin datos"}
                </span>
                <span>{rangeLabel}</span>
              </div>
            </div>

            {/* The same series, readable without a pointer. */}
            <table className="sr-only">
              <caption>Serie de precios de {product.model_name}</caption>
              <thead>
                <tr>
                  <th scope="col">Fecha</th>
                  <th scope="col">Precio normal</th>
                  <th scope="col">Precio con descuento</th>
                  <th scope="col">Precio final</th>
                  <th scope="col">Disponible</th>
                </tr>
              </thead>
              <tbody>
                {chartPoints.map((point, index) => (
                  <tr key={index}>
                    <td>
                      {point.date.toLocaleString("es-CL", {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })}
                    </td>
                    <td>{formatCLP(point.priceNormal)}</td>
                    <td>{point.priceDiscount ? formatCLP(point.priceDiscount) : "—"}</td>
                    <td>{formatCLP(point.effectivePrice)}</td>
                    <td>{point.isInStock ? "Sí" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* The raw ledger. */}
            <section>
              <h3 className="text-label text-muted-foreground">
                Capturas registradas ({snapshots.length})
              </h3>
              <ul className="mt-2 divide-y divide-border">
                {snapshots.map((snap, idx) => {
                  const isDiscount = Boolean(
                    snap.price_discount && snap.price_discount < snap.price_normal
                  );
                  const dateFormatted = new Date(snap.scraped_at).toLocaleString("es-CL", {
                    dateStyle: "medium",
                    timeStyle: "short",
                  });

                  return (
                    <li
                      key={snap.id || idx}
                      className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1 py-3"
                    >
                      <div className="min-w-0">
                        <p className="text-body-sm tabular-nums text-muted-foreground">
                          {dateFormatted}
                        </p>
                        <p
                          className={`inline-flex items-center gap-1.5 text-body-sm ${
                            snap.is_in_stock
                              ? "text-success-foreground"
                              : "text-destructive"
                          }`}
                        >
                          {snap.is_in_stock ? (
                            <Check className="h-3.5 w-3.5" aria-hidden="true" />
                          ) : (
                            <X className="h-3.5 w-3.5" aria-hidden="true" />
                          )}
                          {snap.is_in_stock ? "En stock" : "Agotado"}
                        </p>
                      </div>

                      <div className="text-right">
                        {isDiscount ? (
                          <div className="flex flex-col items-end">
                            <span className="inline-flex items-center gap-1.5 text-price tabular-nums text-success-foreground">
                              <Tag className="h-3.5 w-3.5" aria-hidden="true" />
                              {formatCLP(snap.price_discount)}
                            </span>
                            <div className="mt-0.5 flex items-center justify-end gap-1.5">
                              <span className="text-body-sm tabular-nums text-muted-foreground line-through">
                                {formatCLP(snap.price_normal)}
                              </span>
                              <span className="rounded-sm bg-success-tint px-1.5 py-0.5 text-body-sm font-semibold tabular-nums text-success-foreground">
                                -{snap.discount_percentage}%
                              </span>
                            </div>
                          </div>
                        ) : (
                          <span className="text-price tabular-nums text-foreground">
                            {formatCLP(snap.price_normal)}
                          </span>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </section>
          </div>

          <div
            id="panel-tiendas"
            role="tabpanel"
            aria-labelledby="tab-tiendas"
            hidden={activeTab !== "compare"}
            className="space-y-5"
          >
            {/* The spread, stated as a fact. */}
            {cheapestMatch && savingsVsCurrent > 0 ? (
              <div className="flex items-start gap-3 rounded-lg bg-success-tint p-4">
                <TrendingDown
                  className="mt-0.5 h-5 w-5 shrink-0 text-success-foreground"
                  aria-hidden="true"
                />
                <p className="text-body text-success-foreground">
                  En {storeLabel(cheapestMatch.store)} este modelo está{" "}
                  {formatCLP(savingsVsCurrent)} más barato.
                </p>
              </div>
            ) : (
              <div className="flex items-center gap-3 rounded-lg border border-border p-4">
                <Store className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                <p className="text-body-sm text-muted-foreground">
                  Este modelo aparece en {comparison?.total_stores || 1}{" "}
                  {comparison?.total_stores === 1 ? "óptica" : "ópticas"} con{" "}
                  {comparison?.total_listings || 1} publicaciones en el catálogo.
                </p>
              </div>
            )}

            <section>
              <h3 className="text-label text-muted-foreground">
                Comparativa por óptica ({comparison?.matches.length || 0})
              </h3>

              {comparison?.matches && comparison.matches.length > 0 ? (
                <ul className="mt-2 divide-y divide-border">
                  {comparison.matches.map((item, idx) => {
                    const isCheapest =
                      comparison.lowest_price !== undefined &&
                      item.effective_price === comparison.lowest_price;
                    const isCurrentBase = item.product_id === product.id;
                    const savings =
                      currentPrice && item.effective_price
                        ? currentPrice - item.effective_price
                        : 0;
                    const itemHasDiscount = Boolean(
                      item.price_discount &&
                        item.price_normal &&
                        item.price_discount < item.price_normal
                    );

                    return (
                      <li
                        key={item.product_id || idx}
                        className={cn(
                          "flex flex-wrap items-start justify-between gap-x-4 gap-y-2 py-3",
                          isCurrentBase && "-mx-3 rounded-md bg-accent px-3"
                        )}
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <StoreBadge store={item.store} />
                            {isCurrentBase && (
                              <span className="text-body-sm font-semibold text-accent-foreground">
                                Estás viendo este
                              </span>
                            )}
                            {isCheapest && (
                              <span className="inline-flex items-center gap-1 rounded-sm bg-success-tint px-2 py-1 text-body-sm font-semibold text-success-foreground">
                                <TrendingDown className="h-3.5 w-3.5" aria-hidden="true" />
                                Mejor precio
                                {savings > 0 ? ` · ${formatCLP(savings)}` : ""}
                              </span>
                            )}
                          </div>

                          <p className="mt-1 text-title text-foreground">{item.model_name}</p>

                          <p
                            className={`mt-0.5 inline-flex items-center gap-1.5 text-body-sm ${
                              item.is_in_stock
                                ? "text-success-foreground"
                                : "text-destructive"
                            }`}
                          >
                            {item.is_in_stock ? (
                              <Check className="h-3.5 w-3.5" aria-hidden="true" />
                            ) : (
                              <X className="h-3.5 w-3.5" aria-hidden="true" />
                            )}
                            {item.is_in_stock ? "En stock" : "Sin stock"}
                          </p>
                        </div>

                        <div className="flex shrink-0 flex-col items-end gap-1">
                          <span className="text-price tabular-nums text-foreground">
                            {item.effective_price
                              ? formatCLP(item.effective_price)
                              : "A consultar"}
                          </span>
                          {itemHasDiscount && (
                            <span className="text-body-sm tabular-nums text-muted-foreground line-through">
                              {formatCLP(item.price_normal)}
                            </span>
                          )}
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={cn(
                              buttonVariants({ variant: "secondary", size: "sm" }),
                              "min-h-11 gap-1.5"
                            )}
                          >
                            <span>Ver publicación</span>
                            <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                          </a>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="mt-3 text-body-sm text-muted-foreground">
                  No se encontraron otras publicaciones de este modelo en otras ópticas.
                </p>
              )}
            </section>
          </div>
        </div>
      ) : (
        <p className="py-8 text-center text-body-sm text-destructive">
          No se pudo cargar la información del producto.
        </p>
      )}
    </Dialog>
  );
}

interface PriceSvgChartProps {
  points: ChartPoint[];
  activePoint: ChartPoint | null;
  onPointChange: (point: ChartPoint | null) => void;
  modelName: string;
}

/**
 * The price series. The SVG carries nothing but geometry — grid, line, area
 * and the current point — so it can scale to any width without shrinking text
 * into illegibility. Every label lives in the HTML around it, and the values
 * are repeated in a visually hidden table for screen readers.
 *
 * The viewport is measured so the drawing is 1:1 with CSS pixels: the stroke
 * keeps its weight, the markers stay round, and a pointer maps exactly onto
 * the series.
 */
function PriceSvgChart({
  points,
  activePoint,
  onPointChange,
  modelName,
}: PriceSvgChartProps) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const pointerDownRef = useRef(false);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;

    const measure = () => {
      const rect = el.getBoundingClientRect();
      const width = Math.round(rect.width);
      const height = Math.round(rect.height);
      setSize((prev) =>
        prev.width === width && prev.height === height
          ? prev
          : { width, height }
      );
    };

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  if (points.length === 0) return null;

  const width = size.width;
  const height = size.height;

  const padTop = 12;
  const padBottom = 10;
  const padLeft = 8;
  const padRight = 8;

  const chartW = Math.max(1, width - padLeft - padRight);
  const chartH = Math.max(1, height - padTop - padBottom);

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

  const coordinates = points.map((p, idx) => ({
    x: getX(idx),
    y: getY(p.effectivePrice),
    point: p,
  }));

  const pathD = coordinates.reduce((acc, curr, idx) => {
    if (idx === 0) return `M ${curr.x} ${curr.y}`;
    return `${acc} L ${curr.x} ${curr.y}`;
  }, "");

  const baselineY = padTop + chartH;
  const areaD = `${pathD} L ${coordinates[coordinates.length - 1].x} ${baselineY} L ${
    coordinates[0].x
  } ${baselineY} Z`;

  const midP = (maxP + minP) / 2;
  const gridLevels = [maxP, midP, minP].map((price) => getY(price));

  const current = coordinates[coordinates.length - 1];
  const activeCoordinate = activePoint
    ? coordinates.find((coord) => coord.point === activePoint)
    : undefined;

  const updateFromPointer = (event: React.PointerEvent<SVGSVGElement>) => {
    const svg = svgRef.current;
    if (!svg || width === 0) return;

    const rect = svg.getBoundingClientRect();
    if (rect.width === 0) return;

    // "meet" fit: the drawing may be letterboxed inside the element.
    const scale = Math.min(rect.width / width, rect.height / height);
    const offsetX = (rect.width - width * scale) / 2;
    const pointerX = (event.clientX - rect.left - offsetX) / scale;

    let nearest = coordinates[0];
    let bestDistance = Infinity;
    for (const coord of coordinates) {
      const distance = Math.abs(coord.x - pointerX);
      if (distance < bestDistance) {
        bestDistance = distance;
        nearest = coord;
      }
    }

    onPointChange(nearest.point);
  };

  const handlePointerMove = (event: React.PointerEvent<SVGSVGElement>) => {
    if (event.pointerType === "mouse" || pointerDownRef.current) {
      updateFromPointer(event);
    }
  };

  const handlePointerDown = (event: React.PointerEvent<SVGSVGElement>) => {
    pointerDownRef.current = true;
    updateFromPointer(event);
  };

  const handlePointerUp = () => {
    pointerDownRef.current = false;
  };

  const handlePointerLeave = (event: React.PointerEvent<SVGSVGElement>) => {
    if (event.pointerType === "mouse" && !pointerDownRef.current) {
      onPointChange(null);
    }
  };

  const ariaLabel = `Serie de precios de ${modelName} entre ${
    points[0].dateStr
  } y ${points[points.length - 1].dateStr}, de ${formatCLP(minP)} a ${formatCLP(maxP)}.`;

  return (
    <div
      ref={wrapRef}
      className="aspect-[4/3] w-full sm:aspect-[21/9]"
    >
      {width > 0 && height > 0 && (
        <svg
          ref={svgRef}
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={ariaLabel}
          tabIndex={0}
          className="h-full w-full touch-pan-y select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          onPointerMove={handlePointerMove}
          onPointerDown={handlePointerDown}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
          onPointerLeave={handlePointerLeave}
        >
          {/* Grid lines — no labels, they live in the HTML readout. */}
          {gridLevels.map((y, index) => (
            <line
              key={index}
              x1={padLeft}
              y1={y}
              x2={width - padRight}
              y2={y}
              stroke="currentColor"
              strokeDasharray="3 3"
              strokeWidth="1"
              className="text-border"
            />
          ))}

          {/* Area under the series — flat, never a gradient. */}
          <path d={areaD} className="fill-primary/10" />

          {/* The series itself. */}
          <path
            d={pathD}
            fill="none"
            className="stroke-primary"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* The current point. */}
          <circle
            cx={current.x}
            cy={current.y}
            r="4.5"
            strokeWidth="2"
            className="fill-primary stroke-surface-sunken"
          />

          {/* The probed point, when there is one. */}
          {activeCoordinate && (
            <circle
              cx={activeCoordinate.x}
              cy={activeCoordinate.y}
              r="6"
              strokeWidth="2"
              className="fill-card stroke-primary"
            />
          )}
        </svg>
      )}
    </div>
  );
}
