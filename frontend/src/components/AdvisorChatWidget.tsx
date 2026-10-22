import React, { useEffect, useRef, useState } from "react";
import {
  Send,
  X,
  Bot,
  ExternalLink,
  RotateCcw,
  MessageCircle,
  Tag,
  Glasses,
  Sun,
  Eye,
} from "lucide-react";
import { formatCLP, focusRing } from "@/lib/utils";
import { StoreBadge } from "./StoreBadge";
import { Button } from "./ui/button";
import { Input } from "./ui/input";

interface Props {
  apiBaseUrl: string;
  apiKey: string;
}

/**
 * The product payload the advisor returns. The API contract is
 * `AdvisorChatResponse { response, relevant_products }` where each product is
 * a `ProductRead`; only the fields this widget actually reads are declared
 * here.
 */
interface AdvisorProduct {
  id: string;
  store: string;
  brand: string;
  model_name: string;
  category: string;
  url: string;
  image_url?: string | null;
  current_price_normal?: number | null;
  current_price_discount?: number | null;
  current_in_stock?: boolean | null;
}

interface AdvisorChatResponse {
  response?: string;
  relevant_products?: AdvisorProduct[];
}

interface Message {
  role: "user" | "assistant";
  content: string;
  products?: AdvisorProduct[];
}

function isAdvisorChatResponse(value: unknown): value is AdvisorChatResponse {
  return typeof value === "object" && value !== null && "response" in value;
}

function isAdvisorProduct(value: unknown): value is AdvisorProduct {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Partial<AdvisorProduct>;
  return (
    typeof candidate.url === "string" &&
    typeof candidate.store === "string" &&
    typeof candidate.model_name === "string"
  );
}

interface ParsedSseBlock {
  event: string;
  data: unknown;
}

/**
 * Parse one SSE block ("event: x\ndata: {...}") into its event name and the
 * JSON-decoded data. Returns null for frames we cannot understand.
 */
function parseSseBlock(block: string): ParsedSseBlock | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }
  if (dataLines.length === 0) return null;
  try {
    return { event, data: JSON.parse(dataLines.join("\n")) };
  } catch {
    return null;
  }
}

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
  // In-progress phase text ("Buscando…", "Redactando…") shown in the visible
  // status line. Cleared the moment the answer (or error) arrives.
  const [status, setStatus] = useState("");
  // One-shot completion announcement for the sr-only live region: the finished
  // answer or the error — announced once, never rendered a second time.
  const [announcement, setAnnouncement] = useState("");

  const dialogRef = useRef<HTMLDialogElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // A slow earlier response must never overwrite a newer one.
  const abortRef = useRef<AbortController | null>(null);

  const scrollToBottom = () => {
    const reduceMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    messagesEndRef.current?.scrollIntoView({
      behavior: reduceMotion ? "auto" : "smooth",
    });
  };

  // The native <dialog> owns the top layer: focus trap, inert background,
  // scroll lock and focus restoration all come from the platform.
  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    if (isOpen && !el.open) {
      el.showModal();
    } else if (!isOpen && el.open) {
      el.close();
    }
  }, [isOpen]);

  // Escape is native: the browser fires `cancel`, we mirror it to the state.
  useEffect(() => {
    const el = dialogRef.current;
    if (!el) return;
    const handleCancel = (event: Event) => {
      event.preventDefault();
      setIsOpen(false);
    };
    el.addEventListener("cancel", handleCancel);
    return () => el.removeEventListener("cancel", handleCancel);
  }, []);

  // Stop the in-flight stream when the widget goes away.
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    scrollToBottom();
    const timer = setTimeout(() => inputRef.current?.focus(), 150);
    return () => clearTimeout(timer);
  }, [isOpen, messages, loading]);

  const handleSend = async (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || loading) return;

    setInput("");
    setMessages((prev) => [
      ...prev,
      { role: "user", content: query },
      // Placeholder for the streaming answer: filled in as SSE events land.
      { role: "assistant", content: "" },
    ]);
    setLoading(true);
    setStatus("Buscando productos en el catálogo…");
    setAnnouncement("");

    // Supersede whatever is in flight: the newest request always wins.
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    let assembled = "";
    let finished = false;

    const updateLastAssistant = (updater: (m: Message) => Message) => {
      setMessages((prev) => {
        const next = [...prev];
        for (let i = next.length - 1; i >= 0; i--) {
          if (next[i].role === "assistant") {
            next[i] = updater(next[i]);
            break;
          }
        }
        return next;
      });
    };

    const handleStreamEvent = (event: string, data: unknown) => {
      switch (event) {
        case "products": {
          // Product cards land here first — before any prose exists.
          const rawProducts = (data as { products?: unknown })?.products;
          const products = Array.isArray(rawProducts)
            ? rawProducts.filter(isAdvisorProduct)
            : [];
          updateLastAssistant((m) => ({ ...m, products }));
          break;
        }
        case "status": {
          const phase = (data as { phase?: unknown })?.phase;
          setStatus(
            phase === "generating"
              ? "Redactando la respuesta…"
              : "Buscando productos en el catálogo…"
          );
          break;
        }
        case "delta": {
          const text = (data as { text?: unknown })?.text;
          if (typeof text === "string" && text.length > 0) {
            assembled += text;
            updateLastAssistant((m) => ({ ...m, content: m.content + text }));
          }
          break;
        }
        case "done": {
          finished = true;
          const message = (data as { message?: unknown })?.message;
          const finalText =
            typeof message === "string" && message.length > 0 ? message : assembled;
          // Reconcile to the EXACT message from the done payload: the server
          // applies one end-of-stream correction (trailing-sentence trim), so
          // the bubble must not keep the uncorrected streamed text.
          updateLastAssistant((m) => ({ ...m, content: finalText }));
          // Clear the visible status (the bubble already shows the answer)
          // and announce the completed text once via the sr-only region.
          setStatus("");
          setAnnouncement(finalText);
          break;
        }
        case "error": {
          finished = true;
          const detail = (data as { detail?: unknown })?.detail;
          const errorText =
            typeof detail === "string" && detail.length > 0
              ? detail
              : "No pudimos generar la respuesta. Por favor intenta de nuevo.";
          updateLastAssistant((m) => ({ ...m, content: errorText }));
          // The error text lives in the bubble — no visible status duplication;
          // the sr-only region announces it once.
          setStatus("");
          setAnnouncement(errorText);
          break;
        }
      }
    };

    try {
      const res = await fetch(`${apiBaseUrl}/api/advisor/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey,
        },
        body: JSON.stringify({ message: query }),
        signal: controller.signal,
      });

      if (!res.ok) {
        throw new Error(`Advisor stream failed with status ${res.status}`);
      }

      const contentType = res.headers.get("content-type") || "";

      // Fallback: an older/non-streaming backend answers the classic JSON
      // AdvisorChatResponse — render it in one shot.
      if (!res.body || !contentType.includes("text/event-stream")) {
        const raw: unknown = await res.json();
        const data: AdvisorChatResponse = isAdvisorChatResponse(raw) ? raw : {};
        const products = Array.isArray(data.relevant_products)
          ? data.relevant_products.filter(isAdvisorProduct)
          : [];
        const content = data.response || "Encontré estas opciones en el catálogo:";
        updateLastAssistant((m) => ({ ...m, content, products }));
        setStatus("");
        setAnnouncement(content);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      // Drain every complete "\n\n"-delimited frame currently in the buffer.
      const drainBuffer = () => {
        let boundary = buffer.indexOf("\n\n");
        while (boundary !== -1) {
          const block = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          const parsed = parseSseBlock(block);
          if (parsed) handleStreamEvent(parsed.event, parsed.data);
          if (finished) break;
          boundary = buffer.indexOf("\n\n");
        }
      };

      while (!finished) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        drainBuffer();
      }

      // Flush any multi-byte character the decoder held back, drain whatever
      // that last flush completed, then release the stream's underlying lock
      // whether we finished cleanly or the server hung up early.
      buffer += decoder.decode();
      if (!finished) drainBuffer();
      await reader.cancel();

      if (!finished) {
        throw new Error("The stream ended before the answer was complete.");
      }
    } catch (err) {
      // An aborted request was superseded or torn down on purpose — not a failure.
      if (controller.signal.aborted) return;
      console.error("Error streaming advisor answer:", err);
      const errorText =
        "No pudimos conectar con el catálogo en este momento. Por favor intenta de nuevo.";
      updateLastAssistant((m) => ({ ...m, content: errorText }));
      setStatus("");
      setAnnouncement(errorText);
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
        setLoading(false);
      }
    }
  };

  const handleReset = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setMessages([
      {
        role: "assistant",
        content:
          "¡Hola de nuevo! ¿Qué modelo o rango de presupuesto te gustaría consultar?",
      },
    ]);
    setLoading(false);
    setStatus("");
    setAnnouncement("");
  };

  const handleBackdropClick = (event: React.MouseEvent<HTMLDialogElement>) => {
    if (event.target === dialogRef.current) {
      setIsOpen(false);
    }
  };

  // Skeleton only while the placeholder assistant message is still empty —
  // as soon as cards or text land, the real content replaces it.
  const lastMessage = messages[messages.length - 1];
  const showSkeleton =
    loading &&
    (!lastMessage ||
      lastMessage.role !== "assistant" ||
      (!lastMessage.content &&
        !(lastMessage.products && lastMessage.products.length > 0)));

  return (
    <>
      {/* The trigger: a plain circle, floating by its position and nothing else. */}
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        aria-label="Abrir el asesor óptico"
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        className={[
          "fixed bottom-[max(1rem,env(safe-area-inset-bottom))] right-[max(1rem,env(safe-area-inset-right))]",
          "z-40 flex h-[52px] w-[52px] items-center justify-center rounded-full",
          "border border-border bg-card text-foreground",
          "transition-colors duration-fast ease-out hover:bg-muted",
          focusRing,
        ].join(" ")}
      >
        <MessageCircle className="h-5 w-5" aria-hidden="true" />
      </button>

      {/* The panel: full-height sheet on mobile, side panel on desktop. */}
      <dialog
        ref={dialogRef}
        aria-modal="true"
        aria-labelledby="titulo-asesor"
        onClick={handleBackdropClick}
        className={[
          "fixed inset-0 z-50 m-0 h-dvh max-h-dvh w-full max-w-full overflow-hidden",
          "border-0 bg-transparent p-0 text-foreground",
          "sm:inset-auto sm:bottom-0 sm:left-auto sm:right-0 sm:top-0",
          "sm:h-dvh sm:max-h-dvh sm:w-[min(420px,100vw)] sm:max-w-full",
          "sm:rounded-none sm:border-l sm:border-border sm:bg-card sm:text-card-foreground sm:shadow-overlay",
        ].join(" ")}
      >
        <div className="flex h-full w-full flex-col overflow-hidden bg-card text-card-foreground">
          {/* Header */}
          <div className="flex shrink-0 items-center justify-between gap-2 border-b border-border px-4 py-3">
            <h2 id="titulo-asesor" className="text-title text-foreground">
              Asesor óptico
            </h2>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={handleReset}
                title="Reiniciar conversación"
                aria-label="Reiniciar conversación del asesor"
                className={[
                  "flex h-11 w-11 shrink-0 items-center justify-center rounded-md",
                  "text-muted-foreground transition-colors duration-fast ease-out hover:bg-muted hover:text-foreground",
                  focusRing,
                ].join(" ")}
              >
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
              </button>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                title="Cerrar asesor óptico"
                aria-label="Cerrar el asesor óptico"
                className={[
                  "flex h-11 w-11 shrink-0 items-center justify-center rounded-md",
                  "text-muted-foreground transition-colors duration-fast ease-out hover:bg-muted hover:text-foreground",
                  focusRing,
                ].join(" ")}
              >
                <X className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>
          </div>

          {/* Messages feed. Deliberately NOT a live region: announcing every
              streaming delta would flood a screen reader. Phase changes and
              the one-shot completion announcement go through the live
              regions below instead. */}
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4">
            {messages.map((m, idx) => {
              const hasProducts = Boolean(m.products && m.products.length > 0);
              // The streaming placeholder (no text, no cards yet) renders
              // nothing — the neutral skeleton covers that phase.
              if (m.role === "assistant" && !m.content && !hasProducts) {
                return null;
              }
              return (
              <div
                key={idx}
                className={`flex gap-2.5 ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {m.role === "assistant" && (
                  <span
                    aria-hidden="true"
                    className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border bg-muted text-muted-foreground"
                  >
                    <Bot className="h-3.5 w-3.5" />
                  </span>
                )}
                <div
                  className={`max-w-[85%] rounded-lg px-3.5 py-2.5 text-body ${
                    m.role === "user"
                      ? "rounded-br-sm bg-accent text-accent-foreground"
                      : "rounded-bl-sm border border-border bg-card text-card-foreground"
                  }`}
                >
                  {/* The assistant bubble grows with streaming deltas; it is
                      explicitly aria-live="off" so fragments are never
                      announced mid-sentence. */}
                  <p className="whitespace-pre-line" aria-live={m.role === "assistant" ? "off" : undefined}>
                    {m.content}
                  </p>

                  {/* The products the assistant found. */}
                  {m.products && m.products.length > 0 && (
                    <div className="mt-3 border-t border-border pt-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-body-sm font-semibold text-muted-foreground">
                          Opciones recomendadas
                        </span>
                        <span className="text-body-sm tabular-nums text-muted-foreground">
                          {m.products.length} productos
                        </span>
                      </div>
                      <ul className="mt-2 space-y-1.5">
                        {m.products.map((p, pIdx) => {
                          const price = p.current_price_discount || p.current_price_normal;
                          const hasDisc = Boolean(
                            p.current_price_discount &&
                              p.current_price_normal &&
                              p.current_price_discount < p.current_price_normal
                          );
                          return (
                            <li key={p.id || pIdx}>
                              <a
                                href={p.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-start justify-between gap-3 rounded-md border border-border bg-card p-2.5 transition-colors duration-fast ease-out hover:border-border-strong"
                              >
                                <div className="min-w-0">
                                  <StoreBadge store={p.store} />
                                  <p className="mt-0.5 text-body-sm text-muted-foreground">
                                    {p.brand}
                                  </p>
                                  <p className="text-body-sm font-medium text-foreground">
                                    {p.model_name}
                                  </p>
                                </div>
                                <div className="shrink-0 text-right">
                                  <span className="block text-price tabular-nums text-foreground">
                                    {formatCLP(price)}
                                  </span>
                                  {hasDisc && (
                                    <span className="block text-body-sm tabular-nums text-muted-foreground line-through">
                                      {formatCLP(p.current_price_normal)}
                                    </span>
                                  )}
                                  <ExternalLink
                                    className="mt-0.5 inline h-3.5 w-3.5 text-muted-foreground"
                                    aria-hidden="true"
                                  />
                                </div>
                              </a>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
              );
            })}

            {/* A neutral skeleton. The work is happening; the shape of the
                answer is not known yet, so nothing pretends to be one. The
                phase text itself lives in the status region below. */}
            {showSkeleton && (
              <div className="flex gap-2.5">
                <span
                  aria-hidden="true"
                  className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border bg-muted text-muted-foreground"
                >
                  <Bot className="h-3.5 w-3.5" />
                </span>
                <div className="max-w-[85%] rounded-lg rounded-bl-sm border border-border bg-card px-3.5 py-2.5">
                  <div className="space-y-2" aria-hidden="true">
                    <div className="h-3 w-40 animate-pulse rounded-md bg-muted" />
                    <div className="h-3 w-32 animate-pulse rounded-md bg-muted" />
                    <div className="h-3 w-24 animate-pulse rounded-md bg-muted" />
                  </div>
                </div>
              </div>
            )}

            {/* Prompt suggestions (when idle or only 1 message) */}
            {!loading && messages.length <= 2 && (
              <div className="pt-2">
                <p className="text-body-sm text-muted-foreground">Prueba con:</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {PROMPT_SUGGESTIONS.map((sug, sIdx) => {
                    const Icon = sug.icon;
                    return (
                      <button
                        key={sIdx}
                        type="button"
                        onClick={() => handleSend(sug.query)}
                        className={[
                          "inline-flex min-h-11 items-center gap-1.5 rounded-md",
                          "border border-border bg-card px-3 py-2 text-left text-body-sm text-foreground",
                          "transition-colors duration-fast ease-out hover:border-border-strong",
                          focusRing,
                        ].join(" ")}
                      >
                        <Icon
                          className="h-3.5 w-3.5 shrink-0 text-muted-foreground"
                          aria-hidden="true"
                        />
                        <span>{sug.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* In-progress phase line ("Buscando…", "Redactando…"). Visible
              only while the work runs; cleared the moment done/error lands so
              it can never linger on screen as a stuck phrase. */}
          <div
            role="status"
            aria-live="polite"
            className={
              status
                ? "shrink-0 px-4 pb-2 text-body-sm text-muted-foreground"
                : "sr-only"
            }
          >
            {status}
          </div>

          {/* One-shot completion announcement: the finished answer or the
              error is announced to screen readers exactly once — but never
              rendered here, because the bubble already shows it. Duplicating
              it visibly would print the whole answer twice under the feed. */}
          <div aria-live="polite" className="sr-only">
            {announcement}
          </div>

          {/* Composer */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="safe-bottom flex shrink-0 items-center gap-2 border-t border-border bg-card px-4 py-3"
          >
            <label htmlFor="asesor-mensaje" className="sr-only">
              Mensaje para el asesor óptico
            </label>
            <Input
              id="asesor-mensaje"
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ej: Ray-Ban aviator en oferta bajo $90.000"
              disabled={loading}
              autoComplete="off"
              className="min-w-0 flex-1"
            />
            <Button
              type="submit"
              size="icon"
              disabled={loading || !input.trim()}
              aria-label="Enviar mensaje"
            >
              <Send className="h-4 w-4" aria-hidden="true" />
            </Button>
          </form>
        </div>
      </dialog>
    </>
  );
}
