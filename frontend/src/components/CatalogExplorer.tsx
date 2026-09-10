import React, { useEffect, useState, useRef, useCallback } from "react";
import { ProductCard, type Product } from "./ProductCard";
import { PriceHistoryModal } from "./PriceHistoryModal";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { Select } from "./ui/select";
import { Card } from "./ui/card";
import {
  Search,
  Sparkles,
  RefreshCw,
  Layers,
  CheckCircle2,
  Tag,
  Percent,
  Store,
  Glasses,
  TrendingDown,
  Sun,
  Eye,
  X,
  SlidersHorizontal,
} from "lucide-react";
import { formatCLP } from "@/lib/utils";

interface Props {
  apiBaseUrl: string;
  apiKey: string;
}

interface CatalogStats {
  total_products: number;
  total_deals: number;
  avg_discount_percentage: number;
  total_stores: number;
  total_in_stock: number;
  by_store: Record<string, number>;
  by_category: Record<string, number>;
}

const STORES = [
  { id: "all", label: "Todas las Tiendas" },
  { id: "gmo", label: "GMO" },
  { id: "place_vendome", label: "Place Vendôme" },
  { id: "ryk", label: "Rotter & Krauss" },
  { id: "schilling", label: "Schilling" },
  { id: "econopticas", label: "Econópticas" },
  { id: "karun", label: "Karün" },
  { id: "lentesplus", label: "Lentesplus" },
];

const CATEGORIES = [
  { id: "all", label: "Todo el Catálogo", icon: Layers },
  { id: "sol", label: "Lentes de Sol", icon: Sun },
  { id: "opticos", label: "Lentes Ópticos", icon: Glasses },
  { id: "contacto", label: "Lentes de Contacto", icon: Eye },
];

const TOP_BRANDS = [
  "Ray-Ban",
  "Oakley",
  "Vogue",
  "Karün",
  "Acuvue",
  "Armani Exchange",
  "Michael Kors",
  "Alcon",
  "Arnette",
  "Burberry",
  "Montini",
  "Biofinity",
];

const DEAL_FILTERS = [
  { id: "all", label: "Todos los precios" },
  { id: "disc-40", label: "+40% OFF" },
  { id: "disc-20", label: "+20% OFF" },
  { id: "under-50k", label: "< $50.000" },
  { id: "under-100k", label: "< $100.000" },
];

const PAGE_SIZE = 36;

export function CatalogExplorer({ apiBaseUrl, apiKey }: Props) {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [catalogStats, setCatalogStats] = useState<CatalogStats | null>(null);

  const [search, setSearch] = useState("");
  const [semanticMode, setSemanticMode] = useState(false);
  const [selectedStore, setSelectedStore] = useState("all");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedBrand, setSelectedBrand] = useState<string | null>(null);
  const [dealFilter, setDealFilter] = useState("all");
  const [onlyInStock, setOnlyInStock] = useState(false);
  const [sortBy, setSortBy] = useState<"price-asc" | "price-desc" | "discount" | "recent">("price-asc");
  const [activeHistoryId, setActiveHistoryId] = useState<string | null>(null);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);

  // In-memory query cache for instant tab/filter switching
  const cacheRef = useRef<Map<string, { products: Product[]; totalCount: number }>>(new Map());
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  // 1. Fetch Global Stats
  const fetchStats = async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/api/stats`, {
        headers: { "X-API-Key": apiKey },
      });
      if (res.ok) {
        const data = await res.json();
        setCatalogStats(data);
      }
    } catch (err) {
      console.error("Error fetching catalog stats:", err);
    }
  };

  // 2. Fetch Catalog Products (Reset or Append)
  const fetchProducts = useCallback(
    async (isAppend: boolean = false) => {
      const cacheKey = `${selectedStore}:${selectedCategory}:${selectedBrand || ""}:${dealFilter}:${onlyInStock}:${sortBy}:${semanticMode}:${search.trim()}`;

      if (!isAppend && cacheRef.current.has(cacheKey)) {
        const cached = cacheRef.current.get(cacheKey)!;
        setProducts(cached.products);
        setTotalCount(cached.totalCount);
        setLoading(false);
        return;
      }

      if (isAppend) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }

      try {
        if (semanticMode && search.trim()) {
          const res = await fetch(`${apiBaseUrl}/api/products/search/semantic`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-API-Key": apiKey,
            },
            body: JSON.stringify({
              query: search.trim(),
              store: selectedStore === "all" ? undefined : selectedStore,
              category: selectedCategory === "all" ? undefined : selectedCategory,
              brand: selectedBrand || undefined,
              deal: dealFilter === "all" ? undefined : dealFilter,
              in_stock: onlyInStock ? true : undefined,
              sort_by: sortBy,
              limit: 60,
            }),
          });
          if (res.ok) {
            const data = await res.json();
            setProducts(data);
            setTotalCount(data.length);
            cacheRef.current.set(cacheKey, { products: data, totalCount: data.length });
          }
        } else {
          const offset = isAppend ? products.length : 0;
          const params = new URLSearchParams({
            limit: String(PAGE_SIZE),
            offset: String(offset),
            sort_by: sortBy,
          });

          if (selectedStore !== "all") params.append("store", selectedStore);
          if (selectedCategory !== "all") params.append("category", selectedCategory);
          if (selectedBrand) params.append("brand", selectedBrand);
          if (search.trim()) params.append("search", search.trim());
          if (dealFilter !== "all") params.append("deal", dealFilter);
          if (onlyInStock) params.append("in_stock", "true");

          const res = await fetch(`${apiBaseUrl}/api/products?${params.toString()}`, {
            headers: { "X-API-Key": apiKey },
          });

          if (res.ok) {
            const countHeader = res.headers.get("X-Total-Count");
            const data: Product[] = await res.json();

            let newTotal = totalCount;
            if (countHeader) {
              newTotal = parseInt(countHeader, 10);
              setTotalCount(newTotal);
            } else if (!isAppend) {
              newTotal = data.length;
              setTotalCount(newTotal);
            }

            if (isAppend) {
              setProducts((prev) => {
                const combined = [...prev, ...data];
                cacheRef.current.set(cacheKey, { products: combined, totalCount: newTotal });
                return combined;
              });
            } else {
              setProducts(data);
              cacheRef.current.set(cacheKey, { products: data, totalCount: newTotal });
            }
          }
        }
      } catch (err) {
        console.error("Error fetching products:", err);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [
      apiBaseUrl,
      apiKey,
      selectedStore,
      selectedCategory,
      selectedBrand,
      dealFilter,
      onlyInStock,
      sortBy,
      semanticMode,
      search,
      products.length,
      totalCount,
    ]
  );

  // Initial load: Stats and Products
  useEffect(() => {
    fetchStats();
  }, []);

  // When filters change: reload products from offset 0
  useEffect(() => {
    fetchProducts(false);
  }, [selectedStore, selectedCategory, selectedBrand, dealFilter, onlyInStock, sortBy, semanticMode]);

  // Automatic Infinite Scroll with IntersectionObserver
  useEffect(() => {
    if (!sentinelRef.current) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const first = entries[0];
        if (first.isIntersecting && !loading && !loadingMore && products.length < totalCount && products.length > 0) {
          fetchProducts(true);
        }
      },
      { rootMargin: "400px" }
    );
    observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [loading, loadingMore, products.length, totalCount, fetchProducts]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchProducts(false);
  };

  const handleRefresh = () => {
    fetchStats();
    fetchProducts(false);
  };

  const handleLoadMore = () => {
    if (!loadingMore && products.length < totalCount) {
      fetchProducts(true);
    }
  };

  // Display metrics
  const displayTotal = catalogStats?.total_products ?? 9980;
  const displayDeals = catalogStats?.total_deals ?? 4323;
  const displayDiscount = catalogStats?.avg_discount_percentage ?? 46;
  const displayStores = catalogStats?.total_stores ?? 7;

  const hasActiveCustomFilters =
    selectedStore !== "all" || selectedBrand !== null || dealFilter !== "all" || onlyInStock;

  const clearAllFilters = () => {
    setSelectedStore("all");
    setSelectedBrand(null);
    setDealFilter("all");
    setOnlyInStock(false);
    setSearch("");
  };

  return (
    <div className="space-y-8">
      {/* 1. Market Live Ribbon (Integrated & Sleek) */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 px-5 rounded-2xl bg-card/60 backdrop-blur-md border border-border/80 text-xs shadow-sm">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="font-semibold text-foreground">
            {displayTotal.toLocaleString("es-CL")}
          </span>
          <span className="text-muted-foreground">productos en catálogo</span>
        </div>

        <div className="hidden sm:block h-3.5 w-px bg-border/80" />

        <div className="flex items-center gap-2">
          <Tag className="w-3.5 h-3.5 text-emerald-400" />
          <span className="font-semibold text-emerald-400">
            {displayDeals.toLocaleString("es-CL")} ofertas activas
          </span>
        </div>

        <div className="hidden sm:block h-3.5 w-px bg-border/80" />

        <div className="flex items-center gap-2">
          <Percent className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-muted-foreground">Ahorro promedio:</span>
          <span className="font-mono font-bold text-foreground">
            {displayDiscount > 0 ? `-${displayDiscount}%` : "-46%"}
          </span>
        </div>

        <div className="hidden sm:block h-3.5 w-px bg-border/80" />

        <div className="flex items-center gap-2">
          <Store className="w-3.5 h-3.5 text-muted-foreground" />
          <span className="text-muted-foreground font-medium">
            {displayStores} cadenas monitoreadas
          </span>
        </div>
      </div>

      {/* 2. Unified Search & Category Command Center */}
      <div className="space-y-4">
        {/* Category Segmented Tabs */}
        <div className="flex justify-center">
          <div className="inline-flex p-1.5 rounded-2xl bg-muted/40 border border-border/80 backdrop-blur-sm gap-1 max-w-full overflow-x-auto">
            {CATEGORIES.map((cat) => {
              const Icon = cat.icon;
              const isActive = selectedCategory === cat.id;
              return (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all whitespace-nowrap ${
                    isActive
                      ? "bg-background text-foreground shadow-sm scale-[1.02]"
                      : "text-muted-foreground hover:text-foreground hover:bg-background/40"
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? "text-primary" : "text-muted-foreground"}`} />
                  <span>{cat.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Primary Search Bar Container */}
        <Card className="p-4 md:p-5 rounded-3xl border-border/80 bg-card/80 backdrop-blur-md shadow-lg space-y-4">
          <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-2.5">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={
                  semanticMode
                    ? "Búsqueda con IA: ej. 'armazón metálico dorado estilo aviador'..."
                    : "Buscar por modelo, marca o código (ej. Ray-Ban, Aviator, Oakley)..."
                }
                className="h-12 pl-11 pr-10 rounded-2xl text-sm bg-background/90 border-border/80 focus:border-primary focus:ring-1 focus:ring-primary"
              />
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch("")}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 p-1 rounded-full text-muted-foreground hover:text-foreground hover:bg-muted/60"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            <div className="flex gap-2">
              <Button
                type="button"
                variant={semanticMode ? "default" : "outline"}
                onClick={() => setSemanticMode(!semanticMode)}
                className={`h-12 rounded-2xl text-xs font-semibold gap-2 px-4 transition-all ${
                  semanticMode
                    ? "bg-primary text-primary-foreground shadow-md shadow-primary/20"
                    : "border-border/80 bg-background/60 hover:bg-background"
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Búsqueda Inteligente</span>
                <span className="sm:hidden">IA</span>
              </Button>

              <Button
                type="button"
                variant="outline"
                onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
                className={`h-12 rounded-2xl text-xs font-semibold gap-2 px-4 transition-all ${
                  showAdvancedFilters || hasActiveCustomFilters
                    ? "border-primary/50 text-primary bg-primary/10"
                    : "border-border/80 bg-background/60 hover:bg-background"
                }`}
              >
                <SlidersHorizontal className="w-3.5 h-3.5" />
                <span>Filtros</span>
                {hasActiveCustomFilters && (
                  <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                )}
              </Button>

              <Button type="submit" className="h-12 rounded-2xl px-7 font-bold text-sm shadow-md">
                Buscar
              </Button>
            </div>
          </form>

          {/* Quick Deal Presets (Always accessible) */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-border/60">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mr-1">
                Ahorro:
              </span>
              {DEAL_FILTERS.map((df) => (
                <button
                  key={df.id}
                  onClick={() => setDealFilter(df.id)}
                  className={`px-3 py-1 rounded-xl text-xs font-medium transition-all ${
                    dealFilter === df.id
                      ? "bg-foreground text-background font-bold shadow-sm scale-[1.02]"
                      : "bg-muted/30 hover:bg-muted text-muted-foreground hover:text-foreground border border-border/50"
                  }`}
                >
                  {df.label}
                </button>
              ))}
            </div>

            {hasActiveCustomFilters && (
              <button
                onClick={clearAllFilters}
                className="text-[11px] text-primary hover:underline font-medium"
              >
                Restablecer filtros
              </button>
            )}
          </div>

          {/* Expandable Advanced Filters (Store & Brand Selectors) */}
          {showAdvancedFilters && (
            <div className="pt-3 border-t border-border/60 space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
              {/* Store Filter */}
              <div className="space-y-2">
                <p className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
                  Filtrar por Tienda:
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {STORES.map((s) => (
                    <button
                      key={s.id}
                      onClick={() => setSelectedStore(s.id)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                        selectedStore === s.id
                          ? "bg-primary text-primary-foreground font-bold shadow-sm scale-[1.02]"
                          : "bg-muted/30 hover:bg-muted text-muted-foreground hover:text-foreground border border-border/50"
                      }`}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Brand Filter */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
                    Marcas Populares:
                  </p>
                  {selectedBrand && (
                    <button
                      onClick={() => setSelectedBrand(null)}
                      className="text-[11px] text-primary hover:underline font-normal"
                    >
                      Quitar filtro ({selectedBrand})
                    </button>
                  )}
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {TOP_BRANDS.map((b) => (
                    <button
                      key={b}
                      onClick={() => setSelectedBrand(selectedBrand === b ? null : b)}
                      className={`px-2.5 py-1 rounded-lg text-xs transition-all ${
                        selectedBrand === b
                          ? "bg-primary text-primary-foreground font-bold shadow-sm scale-105"
                          : "bg-muted/20 hover:bg-muted text-muted-foreground hover:text-foreground border border-border/40"
                      }`}
                    >
                      {b}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>

      {/* 3. Catalog Controls & Results Header */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-1">
          <div className="flex items-center gap-2">
            <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              {loading ? (
                "Consultando catálogo en vivo..."
              ) : (
                `Mostrando ${products.length} de ${totalCount.toLocaleString("es-CL")} productos`
              )}
            </p>
            {totalCount > products.length && !loading && (
              <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-[10px] font-mono font-bold">
                {Math.round((products.length / totalCount) * 100)}%
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setOnlyInStock(!onlyInStock)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all flex items-center gap-1.5 ${
                onlyInStock
                  ? "bg-primary/15 text-primary border-primary font-bold shadow-sm"
                  : "bg-muted/30 text-muted-foreground border-border/60 hover:text-foreground"
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Solo en Stock</span>
            </button>

            <div className="flex items-center gap-1.5 text-xs">
              <Select
                value={sortBy}
                onChange={(e: any) => setSortBy(e.target.value)}
                className="w-40 text-xs h-9 rounded-xl"
              >
                <option value="price-asc">Menor Precio</option>
                <option value="price-desc">Mayor Precio</option>
                <option value="discount">Mayor Descuento</option>
                <option value="recent">Recién Agregados</option>
              </Select>
            </div>

            <button
              onClick={handleRefresh}
              title="Actualizar catálogo"
              className="p-2 rounded-xl text-muted-foreground hover:text-primary hover:bg-muted/50 border border-border/60 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Products Grid / Skeletons */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {[...Array(8)].map((_, i) => (
              <div
                key={i}
                className="bg-card border border-border/80 rounded-2xl p-4 flex flex-col justify-between space-y-4 animate-pulse"
              >
                <div className="flex justify-between items-center">
                  <div className="w-20 h-5 bg-muted rounded-full" />
                  <div className="w-12 h-5 bg-muted rounded-md" />
                </div>
                <div className="w-full aspect-[4/3] bg-zinc-100 dark:bg-zinc-900 rounded-xl" />
                <div className="space-y-2 pt-1">
                  <div className="w-16 h-3.5 bg-muted rounded" />
                  <div className="w-4/5 h-4 bg-muted rounded" />
                </div>
                <div className="pt-3 border-t border-border/50 flex items-baseline justify-between">
                  <div className="w-24 h-6 bg-muted rounded" />
                  <div className="w-16 h-4 bg-muted rounded" />
                </div>
                <div className="grid grid-cols-2 gap-2 pt-1">
                  <div className="h-9 bg-muted rounded-xl" />
                  <div className="h-9 bg-muted rounded-xl" />
                </div>
              </div>
            ))}
          </div>
        ) : products.length > 0 ? (
          <div className="space-y-8">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {products.map((p) => (
                <ProductCard
                  key={p.id}
                  product={p}
                  onViewHistory={(id) => setActiveHistoryId(id)}
                />
              ))}
            </div>

            {/* Infinite Scroll Sentinel & Load More Status */}
            <div ref={sentinelRef} className="flex flex-col items-center justify-center pt-4 pb-8 space-y-3">
              {products.length < totalCount ? (
                <Button
                  onClick={handleLoadMore}
                  disabled={loadingMore}
                  variant="outline"
                  className="h-11 px-6 rounded-xl font-mono text-xs gap-2 border-border/80 hover:bg-muted text-foreground transition-all"
                >
                  {loadingMore ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Cargando más modelos...</span>
                    </>
                  ) : (
                    <>
                      <span>Cargar más ({Math.min(PAGE_SIZE, totalCount - products.length)} modelos)</span>
                    </>
                  )}
                </Button>
              ) : (
                <p className="text-xs text-muted-foreground font-mono">
                  Has llegado al final del catálogo ({totalCount.toLocaleString("es-CL")} productos)
                </p>
              )}
              <p className="text-[11px] text-muted-foreground font-mono">
                Mostrando {products.length.toLocaleString("es-CL")} de {totalCount.toLocaleString("es-CL")} productos disponibles
              </p>
            </div>
          </div>
        ) : (
          <div className="bg-card border border-border/80 rounded-2xl p-12 text-center space-y-3">
            <Layers className="w-10 h-10 text-muted-foreground mx-auto opacity-30" />
            <h4 className="font-semibold text-base">No se encontraron productos coincidentes</h4>
            <p className="text-xs text-muted-foreground max-w-md mx-auto">
              Prueba ajustando los filtros de precio, tienda o quitando la marca seleccionada.
            </p>
          </div>
        )}
      </div>

      {/* Price History Modal */}
      <PriceHistoryModal
        productId={activeHistoryId}
        onClose={() => setActiveHistoryId(null)}
        apiBaseUrl={apiBaseUrl}
        apiKey={apiKey}
      />
    </div>
  );
}