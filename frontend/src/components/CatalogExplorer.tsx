import React, { useEffect, useState, useRef, useCallback } from "react";
import { ProductCard, ProductCardSkeleton, type Product } from "./ProductCard";
import { PriceHistoryModal } from "./PriceHistoryModal";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { Select } from "./ui/select";
import {
  Search,
  MessageSquare,
  RefreshCw,
  Layers,
  CheckCircle2,
  SlidersHorizontal,
  TriangleAlert,
  Sun,
  Eye,
  Glasses,
  X,
} from "lucide-react";
import { cn, focusRing } from "@/lib/utils";

interface Props {
  apiBaseUrl: string;
  apiKey: string;
}

const STORES = [
  { id: "all", label: "Todas las tiendas" },
  { id: "gmo", label: "GMO" },
  { id: "place_vendome", label: "Place Vendôme" },
  { id: "ryk", label: "Rotter & Krauss" },
  { id: "schilling", label: "Schilling" },
  { id: "econopticas", label: "Econópticas" },
  { id: "karun", label: "Karün" },
  { id: "lentesplus", label: "Lentesplus" },
];

const CATEGORIES = [
  { id: "all", label: "Todo el catálogo", icon: Layers },
  { id: "sol", label: "Lentes de sol", icon: Sun },
  { id: "opticos", label: "Lentes ópticos", icon: Glasses },
  { id: "contacto", label: "Lentes de contacto", icon: Eye },
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
  { id: "disc-40", label: "-40%" },
  { id: "disc-20", label: "-20%" },
  { id: "under-50k", label: "Menos de $50.000" },
  { id: "under-100k", label: "Menos de $100.000" },
];

type SortBy = "price-asc" | "price-desc" | "discount" | "recent";

const SORT_OPTIONS: { value: SortBy; label: string }[] = [
  { value: "price-asc", label: "Menor precio" },
  { value: "price-desc", label: "Mayor precio" },
  { value: "discount", label: "Mayor descuento" },
  { value: "recent", label: "Recién agregados" },
];

const PAGE_SIZE = 36;

/** 44px on every pointer type — the search row is the one-hand case. */
const CONTROL_HEIGHT = "h-11 min-h-11 pointer-fine:h-11 pointer-fine:min-h-11";

/**
 * One chip shape for every toggle in the product: category, deal preset,
 * store and brand. Selected state is the petrol tint, unselected is the plain
 * surface. No scale, no blur, no colour coding.
 *
 * The label typography lives on the chip's inner <span>, not on the button:
 * the span inherits the button's colour and keeps the type token.
 */
const chipClass = (selected: boolean) =>
  cn(
    "inline-flex min-h-11 items-center gap-2 rounded-sm border px-3 py-2",
    "transition-colors duration-fast ease-out",
    focusRing,
    selected
      ? "border-primary/40 bg-accent text-accent-foreground"
      : "border-border bg-card text-muted-foreground hover:border-border-strong hover:text-foreground"
  );

interface FilterPanelProps {
  selectedStore: string;
  onStoreChange: (storeId: string) => void;
  selectedBrand: string | null;
  onBrandChange: (brand: string | null) => void;
  dealFilter: string;
  onDealChange: (dealId: string) => void;
  onReset: () => void;
  hasActiveFilters: boolean;
}

/**
 * The advanced filters. Rendered inline beside the grid from 1024px up, and
 * inside a bottom sheet below that — same markup, one implementation.
 */
function FilterPanel({
  selectedStore,
  onStoreChange,
  selectedBrand,
  onBrandChange,
  dealFilter,
  onDealChange,
  onReset,
  hasActiveFilters,
}: FilterPanelProps) {
  return (
    <div className="space-y-5">
      <fieldset className="min-w-0 space-y-2">
        <legend className="text-label text-muted-foreground">Ahorro</legend>
        <div className="flex flex-wrap gap-2">
          {DEAL_FILTERS.map((deal) => (
            <button
              key={deal.id}
              type="button"
              aria-pressed={dealFilter === deal.id}
              onClick={() => onDealChange(deal.id)}
              className={chipClass(dealFilter === deal.id)}
            >
              <span className="text-label">{deal.label}</span>
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="min-w-0 space-y-2">
        <legend className="text-label text-muted-foreground">Tienda</legend>
        <div className="flex flex-wrap gap-2">
          {STORES.map((store) => (
            <button
              key={store.id}
              type="button"
              aria-pressed={selectedStore === store.id}
              onClick={() => onStoreChange(store.id)}
              className={chipClass(selectedStore === store.id)}
            >
              <span className="text-label">{store.label}</span>
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="min-w-0 space-y-2">
        <legend className="text-label text-muted-foreground">Marcas populares</legend>
        <div className="flex flex-wrap gap-2">
          {TOP_BRANDS.map((brand) => (
            <button
              key={brand}
              type="button"
              aria-pressed={selectedBrand === brand}
              onClick={() => onBrandChange(selectedBrand === brand ? null : brand)}
              className={chipClass(selectedBrand === brand)}
            >
              <span className="text-label">{brand}</span>
            </button>
          ))}
        </div>
        {selectedBrand && (
          <Button
            type="button"
            variant="ghost"
            size="default"
            onClick={() => onBrandChange(null)}
            aria-label={`Quitar filtro de marca ${selectedBrand}`}
            className="min-h-11 justify-start gap-1.5 px-2 pointer-fine:min-h-11"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Quitar filtro</span>
          </Button>
        )}
      </fieldset>

      {hasActiveFilters && (
        <Button
          type="button"
          variant="ghost"
          size="default"
          onClick={onReset}
          className="min-h-11 justify-start px-2 pointer-fine:min-h-11"
        >
          Restablecer filtros
        </Button>
      )}
    </div>
  );
}

export function CatalogExplorer({ apiBaseUrl, apiKey }: Props) {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [fetchFailed, setFetchFailed] = useState(false);

  const [search, setSearch] = useState("");
  const [semanticMode, setSemanticMode] = useState(false);
  const [selectedStore, setSelectedStore] = useState("all");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedBrand, setSelectedBrand] = useState<string | null>(null);
  const [dealFilter, setDealFilter] = useState("all");
  const [onlyInStock, setOnlyInStock] = useState(false);
  const [sortBy, setSortBy] = useState<SortBy>("price-asc");
  const [activeHistoryId, setActiveHistoryId] = useState<string | null>(null);
  const [filterSheetOpen, setFilterSheetOpen] = useState(false);

  // In-memory query cache for instant tab/filter switching
  const cacheRef = useRef<Map<string, { products: Product[]; totalCount: number }>>(new Map());
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  // A slow earlier response must never overwrite a newer one.
  const abortRef = useRef<AbortController | null>(null);
  const sheetRef = useRef<HTMLDialogElement | null>(null);
  const sheetContentRef = useRef<HTMLDivElement | null>(null);

  // Fetch catalog products (reset or append)
  const fetchProducts = useCallback(
    async (isAppend: boolean = false, force: boolean = false) => {
      const cacheKey = `${selectedStore}:${selectedCategory}:${selectedBrand || ""}:${dealFilter}:${onlyInStock}:${sortBy}:${semanticMode}:${search.trim()}`;

      // `force` (manual refresh) bypasses the cache read but still writes the
      // fresh result back, so filter/search-driven fetches keep hitting it.
      if (!isAppend && !force && cacheRef.current.has(cacheKey)) {
        const cached = cacheRef.current.get(cacheKey)!;
        setProducts(cached.products);
        setTotalCount(cached.totalCount);
        setFetchFailed(false);
        setLoading(false);
        return;
      }

      if (force) {
        // Refresh must invalidate every filter combination: keeping the other
        // keys would still serve stale data after a filter change.
        cacheRef.current.clear();
      }

      if (isAppend) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }

      // Supersede whatever is in flight: the newest request always wins.
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

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
            signal: controller.signal,
          });

          if (!res.ok) {
            throw new Error(`Semantic search failed with status ${res.status}`);
          }

          const data: Product[] = await res.json();
          setProducts(data);
          setTotalCount(data.length);
          cacheRef.current.set(cacheKey, { products: data, totalCount: data.length });
          setFetchFailed(false);
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
            signal: controller.signal,
          });

          if (!res.ok) {
            throw new Error(`Catalog request failed with status ${res.status}`);
          }

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
          setFetchFailed(false);
        }
      } catch (err) {
        // An aborted request was superseded on purpose — it is not a failure.
        if (controller.signal.aborted) return;
        console.error("Error fetching products:", err);
        setFetchFailed(true);
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
          setLoading(false);
          setLoadingMore(false);
        }
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

  // When filters change: reload products from offset 0
  useEffect(() => {
    fetchProducts(false);
  }, [selectedStore, selectedCategory, selectedBrand, dealFilter, onlyInStock, sortBy, semanticMode]);

  // Stop the in-flight request when the component goes away.
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

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

  // Bottom sheet: native <dialog> + showModal() gives the focus trap, the
  // inert background, Escape-to-close and focus restore for free.
  useEffect(() => {
    const el = sheetRef.current;
    if (!el) return;
    if (filterSheetOpen && !el.open) {
      el.showModal();
    } else if (!filterSheetOpen && el.open) {
      el.close();
    }
  }, [filterSheetOpen]);

  useEffect(() => {
    const el = sheetRef.current;
    if (!el) return;
    const handleCancel = (event: Event) => {
      event.preventDefault();
      setFilterSheetOpen(false);
    };
    el.addEventListener("cancel", handleCancel);
    return () => el.removeEventListener("cancel", handleCancel);
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchProducts(false);
  };

  const handleRefresh = () => {
    // Force a network fetch: the refresh button must never be a cache no-op.
    fetchProducts(false, true);
  };

  const handleRetry = () => {
    fetchProducts(false, true);
  };

  const handleLoadMore = () => {
    if (!loadingMore && products.length < totalCount) {
      fetchProducts(true);
    }
  };

  const handleSortChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const next = SORT_OPTIONS.find((option) => option.value === event.target.value);
    if (next) setSortBy(next.value);
  };

  const handleSheetBackdropClick = (event: React.MouseEvent<HTMLDialogElement>) => {
    const el = sheetRef.current;
    if (!el) return;
    const clickedOutside = !sheetContentRef.current?.contains(event.target as Node);
    if (event.target === el && clickedOutside) {
      setFilterSheetOpen(false);
    }
  };

  const activeFilterCount =
    (selectedStore !== "all" ? 1 : 0) +
    (selectedBrand !== null ? 1 : 0) +
    (dealFilter !== "all" ? 1 : 0) +
    (onlyInStock ? 1 : 0);

  const hasActiveFilters = activeFilterCount > 0;

  const clearAllFilters = () => {
    setSelectedStore("all");
    setSelectedBrand(null);
    setDealFilter("all");
    setOnlyInStock(false);
    setSearch("");
  };

  const filterPanelProps: FilterPanelProps = {
    selectedStore,
    onStoreChange: setSelectedStore,
    selectedBrand,
    onBrandChange: setSelectedBrand,
    dealFilter,
    onDealChange: setDealFilter,
    onReset: clearAllFilters,
    hasActiveFilters,
  };

  return (
    <div className="space-y-8 sm:space-y-10">
      {/* 1. Search surface — the hero. It sits directly on the canvas and
          reads as a continuation of the heading above it. */}
      <section aria-label="Buscar en el catálogo" className="space-y-4">
        <form
          onSubmit={handleSearchSubmit}
          className="flex flex-col gap-2.5 sm:flex-row sm:items-center"
        >
          <div className="relative min-w-0 flex-1">
            <Search
              className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por modelo, marca o código (ej. Ray-Ban, Aviator, Oakley)..."
              aria-label="Buscar en el catálogo"
              className={cn(CONTROL_HEIGHT, "pl-11 pr-11")}
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch("")}
                aria-label="Limpiar campo de búsqueda"
                className={cn(
                  "absolute right-0 top-1/2 flex h-11 w-11 -translate-y-1/2 items-center justify-center",
                  "rounded-md text-muted-foreground transition-colors duration-fast ease-out",
                  "hover:bg-muted hover:text-foreground",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                )}
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant={semanticMode ? "subtle" : "secondary"}
              aria-pressed={semanticMode}
              aria-label="Buscar por descripción"
              onClick={() => setSemanticMode((value) => !value)}
              className={cn(CONTROL_HEIGHT, "w-11 shrink-0 px-0 sm:w-auto sm:px-[18px]")}
            >
              <MessageSquare className="h-4 w-4" aria-hidden="true" />
              <span className="hidden sm:inline">Por descripción</span>
            </Button>

            {/* Below 1024px the filters live in a bottom sheet; from 1024px up
                the panel is inline beside the grid, so the button steps aside. */}
            <Button
              type="button"
              variant="secondary"
              onClick={() => setFilterSheetOpen(true)}
              aria-haspopup="dialog"
              aria-expanded={filterSheetOpen}
              aria-controls="panel-filtros"
              className={cn(CONTROL_HEIGHT, "shrink-0 px-3 lg:hidden")}
            >
              <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
              <span>Filtros</span>
              {activeFilterCount > 0 && (
                <span className="inline-flex h-[22px] min-w-[22px] items-center justify-center rounded-sm bg-accent px-1 text-label tabular-nums text-accent-foreground">
                  <span className="sr-only">{activeFilterCount} filtros activos</span>
                  <span aria-hidden="true">{activeFilterCount}</span>
                </span>
              )}
            </Button>

            <Button
              type="submit"
              variant="default"
              className={cn(CONTROL_HEIGHT, "flex-1 sm:flex-none")}
            >
              Buscar
            </Button>
          </div>
        </form>

        <div
          role="group"
          aria-label="Categorías de productos"
          className="flex flex-wrap gap-2"
        >
          {CATEGORIES.map((category) => {
            const Icon = category.icon;
            const isActive = selectedCategory === category.id;
            return (
              <button
                key={category.id}
                type="button"
                aria-pressed={isActive}
                onClick={() => setSelectedCategory(category.id)}
                className={chipClass(isActive)}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                <span className="text-label">{category.label}</span>
              </button>
            );
          })}
        </div>
      </section>

      {/* 2. Results toolbar + results */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          {/* Row A — the real count, as plain text. */}
          <div className="flex w-full items-center justify-between gap-2 sm:w-auto sm:flex-1">
            <p className="text-body-sm text-muted-foreground">
              {loading ? (
                "Consultando catálogo en vivo..."
              ) : (
                <>
                  Mostrando{" "}
                  <span className="tabular-nums">{products.length}</span> de{" "}
                  <span className="tabular-nums">
                    {totalCount.toLocaleString("es-CL")}
                  </span>{" "}
                  productos
                </>
              )}
            </p>
            <Button
              type="button"
              variant="ghost"
              onClick={handleRefresh}
              aria-label="Actualizar catálogo"
              className={cn(CONTROL_HEIGHT, "w-11 shrink-0 px-0")}
            >
              <RefreshCw
                className={cn("h-4 w-4", loading && "animate-spin")}
                aria-hidden="true"
              />
            </Button>
          </div>

          {/* Row B — in-stock toggle + sort. */}
          <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
            <button
              type="button"
              aria-pressed={onlyInStock}
              onClick={() => setOnlyInStock((value) => !value)}
              className={cn(
                CONTROL_HEIGHT,
                "inline-flex items-center gap-2 rounded-md border px-3",
                "transition-colors duration-fast ease-out",
                focusRing,
                onlyInStock
                  ? "border-primary/40 bg-accent text-accent-foreground"
                  : "border-border bg-card text-muted-foreground hover:border-border-strong hover:text-foreground"
              )}
            >
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              <span className="text-label">Solo en stock</span>
            </button>

            <Select
              value={sortBy}
              onChange={handleSortChange}
              aria-label="Ordenar resultados"
              className={cn(
                CONTROL_HEIGHT,
                "w-auto min-w-0 flex-1 sm:flex-none sm:min-w-[12rem]"
              )}
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </div>
        </div>

        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:gap-8">
          {/* Inline filter panel from 1024px up. */}
          <aside className="hidden w-64 shrink-0 lg:block" aria-label="Filtros del catálogo">
            <FilterPanel {...filterPanelProps} />
          </aside>

          <div className="min-w-0 flex-1">
            {loading ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3 xl:grid-cols-4">
                {[...Array(8)].map((_, i) => (
                  <ProductCardSkeleton key={i} />
                ))}
              </div>
            ) : fetchFailed ? (
              <div className="rounded-lg border border-destructive/30 bg-danger-tint p-8 text-center sm:p-12">
                <div className="mx-auto flex max-w-md flex-col items-center gap-3">
                  <TriangleAlert
                    className="h-8 w-8 text-destructive"
                    aria-hidden="true"
                  />
                  <h3 className="text-title text-destructive">
                    No pudimos cargar el catálogo
                  </h3>
                  <p className="text-body-sm text-destructive">
                    Falló la conexión con el catálogo. Revisa tu conexión e
                    inténtalo de nuevo.
                  </p>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={handleRetry}
                    disabled={loading}
                    className={cn(CONTROL_HEIGHT, "px-4")}
                  >
                    Reintentar
                  </Button>
                </div>
              </div>
            ) : products.length > 0 ? (
              <div className="space-y-8">
                {/* The results grid keeps the page outline intact: h1 → h2 → h3. */}
                <h2 className="sr-only">Resultados</h2>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3 xl:grid-cols-4">
                  {products.map((p) => (
                    <ProductCard
                      key={p.id}
                      product={p}
                      onViewHistory={(id) => setActiveHistoryId(id)}
                    />
                  ))}
                </div>

                {/* Infinite Scroll Sentinel & Load More Status */}
                <div
                  ref={sentinelRef}
                  className="flex flex-col items-center justify-center gap-3 pt-2 pb-8"
                >
                  {products.length < totalCount ? (
                    <Button
                      type="button"
                      onClick={handleLoadMore}
                      disabled={loadingMore}
                      variant="secondary"
                      className={cn(CONTROL_HEIGHT, "rounded-md px-4")}
                    >
                      {loadingMore ? (
                        <>
                          <RefreshCw
                            className="h-4 w-4 animate-spin"
                            aria-hidden="true"
                          />
                          <span>Cargando más modelos...</span>
                        </>
                      ) : (
                        <span>
                          Cargar más (
                          {Math.min(PAGE_SIZE, totalCount - products.length)}{" "}
                          modelos)
                        </span>
                      )}
                    </Button>
                  ) : (
                    <p className="text-body-sm text-muted-foreground">
                      Has llegado al final del catálogo (
                      {totalCount.toLocaleString("es-CL")} productos)
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <div className="rounded-lg border border-border bg-card p-8 text-center sm:p-12">
                <Layers
                  className="mx-auto h-8 w-8 text-muted-foreground opacity-40"
                  aria-hidden="true"
                />
                <h3 className="text-title text-foreground">
                  No se encontraron productos coincidentes
                </h3>
                <p className="mx-auto mt-2 max-w-md text-body-sm text-muted-foreground">
                  Prueba ajustando los filtros de precio, tienda o quitando la
                  marca seleccionada.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Filter bottom sheet — below 1024px. */}
      <dialog
        ref={sheetRef}
        id="panel-filtros"
        aria-modal="true"
        aria-labelledby="titulo-filtros"
        onClick={handleSheetBackdropClick}
        className="fixed inset-x-0 bottom-0 m-0 max-h-[85dvh] w-full max-w-none overflow-hidden rounded-t-xl rounded-b-none border-0 border-t border-border bg-card p-0 text-card-foreground shadow-overlay"
      >
        <div
          ref={sheetContentRef}
          className="flex max-h-[85dvh] flex-col overflow-hidden"
        >
          <div className="shrink-0 px-4 pt-3 pb-2">
            <div
              aria-hidden="true"
              className="mx-auto h-1 w-10 rounded-full bg-border-strong"
            />
            <div className="mt-3 flex items-center justify-between gap-3">
              <h2 id="titulo-filtros" className="text-title text-foreground">
                Filtros
              </h2>
              <button
                type="button"
                onClick={() => setFilterSheetOpen(false)}
                aria-label="Cerrar filtros"
                className={cn(
                  "flex h-11 w-11 shrink-0 items-center justify-center rounded-md",
                  "text-muted-foreground transition-colors duration-fast ease-out",
                  "hover:bg-muted hover:text-foreground",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                )}
              >
                <X className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>
          </div>
          <div className="safe-bottom min-h-0 flex-1 overflow-y-auto px-4 pb-4">
            {filterSheetOpen ? <FilterPanel {...filterPanelProps} /> : null}
          </div>
        </div>
      </dialog>

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
