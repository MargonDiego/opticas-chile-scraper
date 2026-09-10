import React, { useState, useEffect, useRef } from "react";
import {
  Send,
  X,
  Bot,
  ExternalLink,
  Sparkles,
  RotateCcw,
  Database,
  Scale,
  BrainCircuit,
  Tag,
  Glasses,
  Sun,
  Eye,
} from "lucide-react";
import { formatCLP } from "@/lib/utils";

interface Props {
  apiBaseUrl: string;
  apiKey: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  products?: any[];
}

const SEARCH_STAGES = [
  { text: "Analizando intención y rango de precio...", icon: BrainCircuit, color: "text-emerald-500" },
  { text: "Consultando catálogo en vivo (9.980+ productos)...", icon: Database, color: "text-cyan-500" },
  { text: "Comparando precios y descuentos entre ópticas...", icon: Scale, color: "text-amber-500" },
  { text: "Sintetizando la mejor recomendación...", icon: Sparkles, color: "text-indigo-500" },
];

const PROMPT_SUGGESTIONS = [
  { label: "Ray-Ban en oferta", query: "Quiero lentes de sol Ray-Ban en oferta bajo $80.000", icon: Sun },
  { label: "Filtro azul oficina", query: "Busco armazones ópticos con filtro azul para computador", icon: Glasses },
  { label: "Mayor descuento", query: "Muéstrame las mejores ofertas con más de 40% de descuento", icon: Tag },
  { label: "Lentes de contacto", query: "Busco lentes de contacto Biofinity o Acuvue al mejor precio", icon: Eye },
];

export function AdvisorChatWidget({ apiBaseUrl, apiKey }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "¡Hola! Soy tu asesor inteligente de ópticas en Chile. ¿Buscas algún modelo específico, lentes de sol, armazones o lentes de contacto al mejor precio?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [searchStageIndex, setSearchStageIndex] = useState(0);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen, messages, loading, searchStageIndex]);

  // Search stage progression timer (synced with ~7-8s real inference latency)
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (loading) {
      setSearchStageIndex(0);
      interval = setInterval(() => {
        setSearchStageIndex((prev) => (prev < SEARCH_STAGES.length - 1 ? prev + 1 : prev));
      }, 1900);
    }
    return () => clearInterval(interval);
  }, [loading]);

  const handleSend = async (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setLoading(true);

    try {
      const res = await fetch(`${apiBaseUrl}/api/advisor/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey,
        },
        body: JSON.stringify({ message: query }),
      });

      if (res.ok) {
        const data = await res.json();
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: data.response || "Encontré estas opciones destacadas en el catálogo:",
            products: data.relevant_products || [],
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "No pudimos conectar con el catálogo en este momento. Por favor intenta de nuevo.",
          },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Hubo un error de conexión al consultar los productos en vivo.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setMessages([
      {
        role: "assistant",
        content:
          "¡Hola de nuevo! ¿Qué modelo o rango de presupuesto te gustaría consultar?",
      },
    ]);
  };

  const CurrentStage = SEARCH_STAGES[searchStageIndex];
  const StageIcon = CurrentStage.icon;

  return (
    <>
      {/* Floating Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2.5 bg-foreground text-background hover:bg-foreground/90 px-4.5 py-3 rounded-2xl shadow-lg hover:shadow-xl hover:scale-[1.02] active:scale-95 transition-all duration-200 border border-border/60 font-mono text-xs font-bold"
      >
        <Sparkles className="w-4 h-4 text-emerald-400" />
        <span>Asesor Óptico</span>
        <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
      </button>

      {/* Chat Drawer / Modal */}
      {isOpen && (
        <div className="fixed bottom-20 right-4 sm:right-6 z-50 w-[calc(100vw-2rem)] sm:w-[440px] bg-card text-card-foreground border border-border/90 rounded-2xl shadow-2xl overflow-hidden flex flex-col h-[580px] max-h-[85vh] animate-in slide-in-from-bottom-5 duration-200">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3.5 bg-card border-b border-border/80 text-foreground">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-muted text-foreground border border-border/80 flex items-center justify-center">
                <Bot className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="font-bold text-sm tracking-tight">Asesor Óptico</h4>
                  <span className="flex items-center gap-1 text-[10px] font-mono text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20 font-bold">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                    En vivo
                  </span>
                </div>
                <p className="text-[11px] text-muted-foreground font-mono">Búsqueda semántica & asesoría</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={handleReset}
                title="Reiniciar conversación"
                className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Messages Feed */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex gap-2.5 ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {m.role === "assistant" && (
                  <div className="w-7 h-7 rounded-xl bg-muted text-foreground border border-border/80 flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="w-3.5 h-3.5" />
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                    m.role === "user"
                      ? "bg-primary text-primary-foreground font-medium rounded-br-sm shadow-xs"
                      : "bg-muted/70 text-foreground border border-border/80 rounded-bl-sm"
                  }`}
                >
                  <p className="whitespace-pre-line">{m.content}</p>

                  {/* Recommended Products Cards */}
                  {m.products && m.products.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-border/80 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                          Opciones recomendadas:
                        </span>
                        <span className="font-mono text-[9.5px] text-emerald-500 font-bold bg-emerald-500/10 px-1.5 py-0.5 rounded">
                          {m.products.length} productos
                        </span>
                      </div>
                      <div className="space-y-1.5">
                        {m.products.map((p, pIdx) => {
                          const price = p.current_price_discount || p.current_price_normal;
                          const hasDisc =
                            p.current_price_discount &&
                            p.current_price_normal &&
                            p.current_price_discount < p.current_price_normal;
                          return (
                            <a
                              key={pIdx}
                              href={p.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="group/item flex items-center justify-between p-2.5 rounded-xl bg-card border border-border/90 hover:border-emerald-500/80 hover:shadow-md transition-all text-xs"
                            >
                              <div className="truncate mr-2 space-y-0.5">
                                <div className="flex items-center gap-1.5">
                                  <span className="font-mono text-[9px] font-extrabold uppercase px-1.5 py-0.5 bg-emerald-500/10 text-emerald-500 rounded border border-emerald-500/20">
                                    {p.store}
                                  </span>
                                  <span className="font-mono text-[10px] font-bold text-muted-foreground uppercase">
                                    {p.brand}
                                  </span>
                                </div>
                                <p className="font-medium text-foreground truncate group-hover/item:text-emerald-500 transition-colors text-[11.5px]">
                                  {p.model_name}
                                </p>
                              </div>
                              <div className="flex items-center gap-1.5 shrink-0 font-mono">
                                <div className="text-right">
                                  <span className="font-black text-emerald-600 dark:text-emerald-400 text-xs block">
                                    {formatCLP(price)}
                                  </span>
                                  {hasDisc && (
                                    <span className="text-[9.5px] text-muted-foreground line-through block leading-none">
                                      {formatCLP(p.current_price_normal)}
                                    </span>
                                  )}
                                </div>
                                <ExternalLink className="w-3 h-3 text-muted-foreground group-hover/item:text-emerald-500 transition-colors" />
                              </div>
                            </a>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Dynamic Interactive Loading State */}
            {loading && (
              <div className="space-y-3 animate-in fade-in duration-300">
                <div className="flex gap-2.5 items-start">
                  <div className="w-7 h-7 rounded-xl bg-emerald-500/20 text-emerald-500 border border-emerald-500/40 flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="w-3.5 h-3.5 animate-spin" />
                  </div>
                  <div className="flex-1 rounded-2xl rounded-bl-sm p-3 bg-muted/60 border border-border/80 space-y-2.5">
                    {/* Live Stage Progress Indicator */}
                    <div className="flex items-center gap-2 text-xs font-medium">
                      <StageIcon className={`w-4 h-4 animate-bounce ${CurrentStage.color}`} />
                      <span className="text-foreground font-medium animate-pulse">
                        {CurrentStage.text}
                      </span>
                    </div>

                    {/* Shimmer Skeleton Cards */}
                    <div className="space-y-1.5 pt-1">
                      <div className="p-2 rounded-xl bg-card/60 border border-border/60 animate-pulse space-y-1.5">
                        <div className="flex items-center justify-between">
                          <div className="h-3 w-16 bg-muted-foreground/20 rounded" />
                          <div className="h-3 w-12 bg-emerald-500/20 rounded" />
                        </div>
                        <div className="h-3 w-3/4 bg-muted-foreground/15 rounded" />
                      </div>
                      <div className="p-2 rounded-xl bg-card/60 border border-border/60 animate-pulse space-y-1.5 opacity-70">
                        <div className="flex items-center justify-between">
                          <div className="h-3 w-14 bg-muted-foreground/20 rounded" />
                          <div className="h-3 w-10 bg-emerald-500/20 rounded" />
                        </div>
                        <div className="h-3 w-2/3 bg-muted-foreground/15 rounded" />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Prompt Suggestion Chips (when idle or only 1 message) */}
            {!loading && messages.length <= 2 && (
              <div className="pt-2 space-y-1.5 animate-in fade-in duration-300">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold text-muted-foreground px-1">
                  <Sparkles className="w-3 h-3 text-emerald-500" />
                  <span>Sugerencias rápidas:</span>
                </div>
                <div className="grid grid-cols-2 gap-1.5">
                  {PROMPT_SUGGESTIONS.map((sug, sIdx) => {
                    const Icon = sug.icon;
                    return (
                      <button
                        key={sIdx}
                        onClick={() => handleSend(sug.query)}
                        className="flex items-center gap-1.5 p-2 text-left rounded-xl bg-muted/40 hover:bg-muted border border-border/80 hover:border-emerald-500/40 text-[11px] font-medium text-foreground transition-all group"
                      >
                        <Icon className="w-3.5 h-3.5 text-emerald-500 group-hover:scale-110 transition-transform shrink-0" />
                        <span className="truncate">{sug.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Form */}
          <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="p-3 border-t border-border bg-card/95 backdrop-blur flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ej: Ray-Ban aviator en oferta bajo $90k..."
              disabled={loading}
              className="flex-1 bg-muted/50 border border-input rounded-xl px-3.5 py-2 text-xs sm:text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-3.5 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40 transition-all shrink-0 shadow-xs font-bold"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      )}
    </>
  );
}