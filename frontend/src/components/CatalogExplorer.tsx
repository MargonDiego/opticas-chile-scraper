import React, { useEffect, useState, useMemo } from "react";
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

export function CatalogExplorer({ apiBaseUrl, apiKey }: Props) {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [semanticMode, setSemanticMode] = useState(false);
  const [selectedStore, setSelectedStore] = useState("all");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedBrand, setSelectedBrand] = useState<string | null>(null);
  const [dealFilter, setDealFilter] = useState("all");
  const [onlyInStock, setOnlyInStock] = useState(false);
  const [sortBy, setSortBy] = useState<"price-asc" | "price-desc" | "discount">("price-asc");
  const [activeHistoryId, setActiveHistoryId] = useState<string | null>(null);

  // Fetch Catalog
  const fetchProducts = async () => {
    setLoading(true);
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
            limit: 120,
          }),
        });
        if (res.ok) {
          const data = await res.json();
          setProducts(data);
        }
      } else {
        const params = new URLSearchParams({ limit: "150" });
        if (selectedStore !== "all") params.append("store", selectedStore);
        if (selectedCategory !== "all") params.append("category", selectedCategory);
        if (selectedBrand) params.append("brand", selectedBrand);
        if (search.trim()) params.append("search", search.trim());

        const res = await fetch(`${apiBaseUrl}/api/products?${params.toString()}`, {
          headers: { "X-API-Key": apiKey },
        });
        if (res.ok) {
          const data = await res.json();
          setProducts(data);
        }
      }
    } catch (err) {
      console.error("Error fetching products:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, [selectedStore, selectedCategory, selectedBrand, semanticMode]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchProducts();
  };

  // Client-side statistics for Market Pulse
  const stats = useMemo(() => {
    const total = products.length;
    let dealsCount = 0;
    let totalDiscountPct = 0;

    for (const p of products) {
      if (
        p.current_price_discount &&
        p.current_price_normal &&
        p.current_price_discount < p.current_price_normal
      ) {
        dealsCount++;
        const pct =
          ((p.current_price_normal - p.current_price_discount) / p.current_price_normal) * 100;
        totalDiscountPct += pct;
      }
    }

    const avgDiscount = dealsCount > 0 ? Math.round(totalDiscountPct / dealsCount) : 0;
    return { total, dealsCount, avgDiscount };
  }, [products]);

  // Client-side filtering & sorting
  const filteredAndSortedProducts = useMemo(() => {
    let list = [...products];

    // Filter by Brand if set in client
    if (selectedBrand) {
      const bLower = selectedBrand.toLowerCase();
      list = list.filter(
        (p) =>
          p.brand?.toLowerCase().includes(bLower) ||
          p.model_name?.toLowerCase().includes(bLower)
      );
    }

    // Filter by Stock
    if (onlyInStock) {
      list = list.filter((p) => p.current_in_stock !== false);
    }

    // Deal Hunter filter
    if (dealFilter === "disc-40") {
      list = list.filter((p) => {
        if (!p.current_price_discount || !p.current_price_normal) return false;
        const pct =
          ((p.current_price_normal - p.current_price_discount) / p.current_price_normal) * 100;
        return pct >= 40;
      });
    } else if (dealFilter === "disc-20") {
      list = list.filter((p) => {
        if (!p.current_price_discount || !p.current_price_normal) return false;
        const pct =
          ((p.current_price_normal - p.current_price_discount) / p.current_price_normal) * 100;
        return pct >= 20;
      });
    } else if (dealFilter === "under-50k") {
      list = list.filter((p) => {
        const price = p.current_price_discount || p.current_price_normal || 0;
        return price > 0 && price <= 50000;
      });
    } else if (dealFilter === "under-100k") {
      list = list.filter((p) => {
        const price = p.current_price_discount || p.current_price_normal || 0;
        return price > 0 && price <= 100000;
      });
    }

    // Sort
    return list.sort((a, b) => {
      const pA = a.current_price_discount || a.current_price_normal || 0;
      const pB = b.current_price_discount || b.current_price_normal || 0;

      if (sortBy === "price-asc") return pA - pB;
      if (sortBy === "price-desc") return pB - pA;
      if (sortBy === "discount") {
        const discA =
          a.current_price_normal && a.current_price_discount
            ? a.current_price_normal - a.current_price_discount
            : 0;
        const discB =
          b.current_price_normal && b.current_price_discount
            ? b.current_price_normal - b.current_price_discount
            : 0;
        return discB - discA;
      }
      return 0;
    });
  }, [products, sortBy, onlyInStock, selectedBrand, dealFilter]);

  return (
    <div className="space-y-6">
      {/* 1. Market Pulse / Metrics Ribbon */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-4 rounded-2xl bg-card border border-border/80 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0">
            <Glasses className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground font-medium">Productos Activos</p>
            <p className="text-xl font-bold font-mono text-foreground leading-tight">
              {stats.total > 0 ? stats.total.toLocaleString("es-CL") : "7.600+"}
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
              {stats.dealsCount.toLocaleString("es-CL")}
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
              {stats.avgDiscount > 0 ? `-${stats.avgDiscount}%` : "-30%"}
            </p>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-card border border-border/80 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-muted/60 text-muted-foreground flex items-center justify-center shrink-0">
            <Store className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground font-medium">Cadenas Comparadas</p>
            <p className="text-xl font-bold font-mono text-foreground leading-tight">7 Tiendas</p>
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
            <span>Marcar Populares:</span>
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
            </Select>
          </div>
        </div>
      </Card>

      {/* Catalog Grid Header */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Resultados ({filteredAndSortedProducts.length} productos)
          </p>
          <button
            onClick={fetchProducts}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-primary transition-colors font-medium"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> Actualizar
          </button>
        </div>

        {/* Products Grid */}
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {[...Array(8)].map((_, i) => (
              <div
                key={i}
                className="bg-card border border-border rounded-2xl p-4 h-80 animate-pulse flex flex-col justify-between"
              >
                <div className="w-20 h-4 bg-muted rounded-full" />
                <div className="w-full h-36 bg-muted rounded-xl" />
                <div className="space-y-2">
                  <div className="w-3/4 h-4 bg-muted rounded" />
                  <div className="w-1/2 h-5 bg-muted rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : filteredAndSortedProducts.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {filteredAndSortedProducts.map((p) => (
              <ProductCard
                key={p.id}
                product={p}
                onViewHistory={(id) => setActiveHistoryId(id)}
              />
            ))}
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