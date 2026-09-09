import React, { useEffect, useState, useMemo } from "react";
import { ProductCard, type Product } from "./ProductCard";
import { PriceHistoryModal } from "./PriceHistoryModal";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { Search, Sparkles, SlidersHorizontal, RefreshCw, Layers } from "lucide-react";

interface Props {
  apiBaseUrl: string;
  apiKey: string;
}

const STORES = [
  { id: "all", label: "Todas las Tiendas" },
  { id: "gmo", label: "GMO Chile" },
  { id: "place_vendome", label: "Place Vendôme" },
  { id: "ryk", label: "Rotter & Krauss" },
  { id: "schilling", label: "Ópticas Schilling" },
  { id: "econopticas", label: "Econópticas" },
  { id: "karun", label: "Karün Chile" },
  { id: "lentesplus", label: "Lentesplus" },
];

const CATEGORIES = [
  { id: "all", label: "Todas las Categorías" },
  { id: "sol", label: "Lentes de Sol" },
  { id: "opticos", label: "Lentes Ópticos" },
  { id: "contacto", label: "Lentes de Contacto" },
];

export function CatalogExplorer({ apiBaseUrl, apiKey }: Props) {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [semanticMode, setSemanticMode] = useState(false);
  const [selectedStore, setSelectedStore] = useState("all");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [sortBy, setSortBy] = useState<"price-asc" | "price-desc" | "discount">("price-asc");
  const [activeHistoryId, setActiveHistoryId] = useState<string | null>(null);

  // Fetch Catalog
  const fetchProducts = async () => {
    setLoading(true);
    try {
      if (semanticMode && search.trim()) {
        // Vector Search via pgvector
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
        }
      } else {
        // Traditional Filter
        const params = new URLSearchParams({ limit: "100" });
        if (selectedStore !== "all") params.append("store", selectedStore);
        if (selectedCategory !== "all") params.append("category", selectedCategory);
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
  }, [selectedStore, selectedCategory, semanticMode]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchProducts();
  };

  // Client-side sorting
  const sortedProducts = useMemo(() => {
    return [...products].sort((a, b) => {
      const pA = a.current_price_discount || a.current_price_normal || 0;
      const pB = b.current_price_discount || b.current_price_normal || 0;

      if (sortBy === "price-asc") return pA - pB;
      if (sortBy === "price-desc") return pB - pA;
      if (sortBy === "discount") {
        const discA = a.current_price_normal && a.current_price_discount ? a.current_price_normal - a.current_price_discount : 0;
        const discB = b.current_price_normal && b.current_price_discount ? b.current_price_normal - b.current_price_discount : 0;
        return discB - discA;
      }
      return 0;
    });
  }, [products, sortBy]);

  return (
    <div className="space-y-8">
      {/* Search & Hero Bar */}
      <div className="bg-card border border-border p-6 rounded-3xl shadow-sm space-y-6">
        <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={
                semanticMode
                  ? "Búsqueda semántica con IA: ej. 'armazón metálico dorado estilo aviador'..."
                  : "Buscar por modelo, marca o descripción (ej. Ray-Ban, Aviator, Acuvue)..."
              }
              className="w-full pl-12 pr-4 py-3 rounded-2xl bg-muted/30 border border-input text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary transition-all"
            />
          </div>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setSemanticMode(!semanticMode)}
              className={`flex items-center gap-2 px-4 py-3 rounded-2xl text-xs font-bold border transition-all ${
                semanticMode
                  ? "bg-gradient-to-r from-primary to-indigo-600 text-white border-transparent shadow-md shadow-primary/20"
                  : "bg-muted/40 border-border text-muted-foreground hover:text-foreground"
              }`}
            >
              <Sparkles className="w-4 h-4" />
              <span>Búsqueda IA ({semanticMode ? "Activa" : "Desactivada"})</span>
            </button>

            <Button type="submit" className="rounded-2xl px-6 py-3 font-semibold h-auto">
              Buscar
            </Button>
          </div>
        </form>

        {/* Store Filter Pills */}
        <div className="space-y-2.5">
          <div className="flex items-center gap-2 font-mono text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
            <span>FILTER // TIENDAS:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {STORES.map((s) => (
              <button
                key={s.id}
                onClick={() => setSelectedStore(s.id)}
                className={`px-3 py-1.5 rounded-xl font-mono text-xs font-semibold transition-all ${
                  selectedStore === s.id
                    ? "bg-primary text-primary-foreground shadow-md shadow-primary/20 scale-[1.02]"
                    : "bg-muted/40 hover:bg-muted text-muted-foreground hover:text-foreground border border-border/60"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Category Filter Pills & Sort */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pt-4 border-t border-border">
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map((c) => (
              <button
                key={c.id}
                onClick={() => setSelectedCategory(c.id)}
                className={`px-3 py-1.5 rounded-lg font-mono text-xs font-semibold transition-all ${
                  selectedCategory === c.id
                    ? "bg-secondary text-secondary-foreground font-bold border border-primary/40 shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/30"
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 font-mono text-xs">
            <span className="text-muted-foreground font-bold text-[11px]">SORT // ORDENAR:</span>
            <select
              value={sortBy}
              onChange={(e: any) => setSortBy(e.target.value)}
              className="bg-muted/50 border border-input rounded-xl px-3 py-1.5 text-xs font-mono font-medium focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="price-asc">Menor Precio (CLP)</option>
              <option value="price-desc">Mayor Precio (CLP)</option>
              <option value="discount">Mayor Descuento ($)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Catalog Grid */}
      <div>
        <div className="flex items-center justify-between mb-4 font-mono">
          <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            CATALOG // RESULTADOS ({sortedProducts.length} PRODUCTOS)
          </p>
          <button
            onClick={fetchProducts}
            className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-primary transition-colors font-semibold"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} /> ACTUALIZAR
          </button>
        </div>

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
        ) : sortedProducts.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {sortedProducts.map((p) => (
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
              Prueba cambiando los filtros de tienda, ajustando la búsqueda o ejecutando un nuevo scrape desde la API.
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