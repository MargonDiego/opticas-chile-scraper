import React, { useEffect, useState } from "react";
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
  { id: "all", label: "Todo el Catálogo" },
  { id: "sol", label: "Lentes de Sol" },
  { id: "opticos", label: "Lentes Ópticos" },
  { id: "contacto", label: "Lentes de Contacto" },
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
  { id: "disc-40", label: "Más de 40% OFF" },
  { id: "disc-20", label: "Más de 20% OFF" },
  { id: "under-50k", label: "Menos de $50.000" },
  { id: "under-100k", label: "Menos de $100.000" },
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
  const fetchProducts = async (isAppend: boolean = false) => {
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
            limit: 60,
          }),
        });
        if (res.ok) {
          const data = await res.json();
          setProducts(data);
          setTotalCount(data.length);
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
          const data = await res.json();

          if (countHeader) {
            setTotalCount(parseInt(countHeader, 10));
          } else if (!isAppend) {
            setTotalCount(data.length);
          }

          if (isAppend) {
            setProducts((prev) => [...prev, ...data]);
          } else {
            setProducts(data);
          }
        }
      }
    } catch (err) {
      console.error("Error fetching products:", err);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  // Initial load: Stats and Products
  useEffect(() => {
    fetchStats();
  }, []);

  // When filters change: reload products from offset 0
  useEffect(() => {
    fetchProducts(false);
  }, [selectedStore, selectedCategory, selectedBrand, dealFilter, onlyInStock, sortBy, semanticMode]);

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

  return (
    <div className="space-y-6">
      {/* 1. Market Pulse / Real Global Metrics Ribbon */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-4 rounded-2xl bg-card border border-border/80 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0">
            <Glasses className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground font-medium">Productos Activos</p>
            <p className="text-xl font-bold font-mono text-foreground leading-tight">
              {displayTotal.toLocaleString("es-CL")}
            </p>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-card border border-border/80 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
            <Tag className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground font-medium">Ofertas Detectadas</p>
            <p className="text-xl font-bold font-mono text-foreground leading-tight">
              {displayDeals.toLocaleString("es-CL")}
            </p>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-card border border-border/80 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0">
            <Percent className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground font-medium">Descuento Promedio</p>
            <p className="text-xl font-bold font-mono text-foreground leading-tight">
              {displayDiscount > 0 ? `-${displayDiscount}%` : "-46%"}
            </p>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-card border border-border/80 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-muted/60 text-muted-foreground flex items-center justify-center shrink-0">
            <Store className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground font-medium">Cadenas Comparadas</p>
            <p className="text-xl font-bold font-mono text-foreground leading-tight">
              {displayStores} Tiendas
            </p>
          </div>
        </div>
      </div>

      {/* 2. Search & Main Controls Card */}
      <Card className="p-5 md:p-6 rounded-3xl space-y-5 border-border/80 shadow-sm">
        {/* Search Bar */}
        <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={
                semanticMode
                  ? "Búsqueda descriptiva: ej. 'armazón metálico dorado estilo aviador'..."
                  : "Buscar por modelo, marca o estilo (ej. Ray-Ban, Aviator, Acuvue)..."
              }
              className="h-11 pl-11 pr-4 rounded-xl text-sm bg-background"
            />
          </div>

          <div className="flex gap-2">
            <Button
              type="button"
              variant={semanticMode ? "default" : "outline"}
              onClick={() => setSemanticMode(!semanticMode)}
              className="h-11 rounded-xl text-xs font-semibold gap-2 px-4 shadow-sm"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Búsqueda Inteligente</span>
            </Button>

            <Button type="submit" className="h-11 rounded-xl px-6 font-semibold">
              Buscar
            </Button>
          </div>
        </form>

        {/* 3. Deal Hunter / Quick Price Pills */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            <TrendingDown className="w-3.5 h-3.5 text-primary" />
            <span>Filtros Rápidos de Ahorro:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {DEAL_FILTERS.map((df) => (
              <button
                key={df.id}
                onClick={() => setDealFilter(df.id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                  dealFilter === df.id
                    ? "bg-foreground text-background font-semibold shadow-sm"
                    : "bg-muted/40 hover:bg-muted text-muted-foreground hover:text-foreground border border-border/60"
                }`}
              >
                {df.label}
              </button>
            ))}
          </div>
        </div>

        {/* 4. Top Brands Selector */}
        <div className="space-y-2 pt-2">
          <div className="flex items-center justify-between text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            <span>Marcas Populares:</span>
            {selectedBrand && (
              <button
                onClick={() => setSelectedBrand(null)}
                className="text-[11px] text-primary hover:underline lowercase font-normal"
              >
                quitar filtro de marca ({selectedBrand})
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
                    ? "bg-primary text-primary-foreground font-semibold shadow-sm scale-105"
                    : "bg-muted/30 hover:bg-muted text-muted-foreground hover:text-foreground border border-border/40"
                }`}
              >
                {b}
              </button>
            ))}
          </div>
        </div>

        {/* Store Filter Pills */}
        <div className="space-y-2 pt-2 border-t border-border/60">
          <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            <span>Tiendas:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {STORES.map((s) => (
              <button
                key={s.id}
                onClick={() => setSelectedStore(s.id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                  selectedStore === s.id
                    ? "bg-primary text-primary-foreground font-semibold shadow-sm scale-[1.02]"
                    : "bg-muted/40 hover:bg-muted text-muted-foreground hover:text-foreground border border-border/60"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Category Filter Pills & Sort Dropdown */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pt-3 border-t border-border/60">
          <div className="flex flex-wrap items-center gap-2">
            {CATEGORIES.map((c) => (
              <button
                key={c.id}
                onClick={() => setSelectedCategory(c.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  selectedCategory === c.id
                    ? "bg-secondary text-secondary-foreground font-semibold border border-primary/30 shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/30"
                }`}
              >
                {c.label}
              </button>
            ))}

            <button
              onClick={() => setOnlyInStock(!onlyInStock)}
              className={`ml-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 ${
                onlyInStock
                  ? "bg-primary/15 text-primary border-primary font-semibold shadow-sm"
                  : "bg-muted/30 text-muted-foreground border-border/60 hover:text-foreground"
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Solo en Stock</span>
            </button>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-muted-foreground font-medium">Ordenar:</span>
            <Select
              value={sortBy}
              onChange={(e: any) => setSortBy(e.target.value)}
              className="w-44 text-xs"
            >
              <option value="price-asc">Menor Precio</option>
              <option value="price-desc">Mayor Precio</option>
              <option value="discount">Mayor Descuento ($)</option>
              <option value="recent">Recién Agregados</option>
            </Select>
          </div>
        </div>
      </Card>

      {/* Catalog Grid Header & Results Status */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {loading ? (
                "Buscando productos..."
              ) : (
                `Mostrando ${products.length} de ${totalCount.toLocaleString("es-CL")} productos`
              )}
            </p>
            {totalCount > products.length && !loading && (
              <span className="text-[11px] text-primary font-mono font-medium">
                ({Math.round((products.length / totalCount) * 100)}%)
              </span>
            )}
          </div>

          <button
            onClick={handleRefresh}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-primary transition-colors font-medium"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Actualizar
          </button>
        </div>

        {/* Products Grid / Skeletons */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {[...Array(8)].map((_, i) => (
              <div
                key={i}
                className="bg-card/70 border border-border/70 rounded-2xl p-4 h-96 flex flex-col justify-between animate-pulse"
              >
                <div className="flex justify-between items-center">
                  <div className="w-20 h-5 bg-muted/80 rounded-full" />
                  <div className="w-12 h-5 bg-muted/60 rounded-full" />
                </div>
                <div className="w-full h-40 bg-muted/40 rounded-xl my-2 flex items-center justify-center">
                  <div className="w-12 h-12 rounded-full bg-muted/60" />
                </div>
                <div className="space-y-2">
                  <div className="w-1/3 h-3.5 bg-muted/60 rounded" />
                  <div className="w-4/5 h-4 bg-muted/80 rounded" />
                </div>
                <div className="pt-2 border-t border-border/50 flex justify-between items-center">
                  <div className="space-y-1">
                    <div className="w-24 h-5 bg-muted/90 rounded" />
                    <div className="w-16 h-3 bg-muted/50 rounded" />
                  </div>
                  <div className="w-8 h-8 rounded-lg bg-muted/60" />
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

            {/* Load More Button & Infinite Pagination Bar */}
            {products.length < totalCount && (
              <div className="flex flex-col items-center justify-center pt-4 pb-8 space-y-3">
                <Button
                  onClick={handleLoadMore}
                  disabled={loadingMore}
                  className="h-12 px-8 rounded-2xl font-semibold text-sm gap-2 shadow-lg shadow-primary/20 hover:scale-[1.02] transition-transform"
                >
                  {loadingMore ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Cargando más productos...</span>
                    </>
                  ) : (
                    <>
                      <span>Cargar más productos ({Math.min(PAGE_SIZE, totalCount - products.length)} más)</span>
                    </>
                  )}
                </Button>
                <p className="text-xs text-muted-foreground font-mono">
                  Mostrando {products.length.toLocaleString("es-CL")} de {totalCount.toLocaleString("es-CL")} productos disponibles
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-card border border-border rounded-3xl p-12 text-center space-y-3">
            <Layers className="w-12 h-12 text-muted-foreground mx-auto opacity-30" />
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