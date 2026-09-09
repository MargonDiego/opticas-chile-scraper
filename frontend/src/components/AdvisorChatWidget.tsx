import React, { useState } from "react";
import { MessageSquare, Send, Sparkles, X, Bot, User, ExternalLink } from "lucide-react";
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

export function AdvisorChatWidget({ apiBaseUrl, apiKey }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "¡Hola! Soy tu Asesor Experto en Ópticas en Chile. ¿Buscas lentes de sol, armazones ópticos o lentes de contacto con el mejor precio?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);

    try {
      const res = await fetch(`${apiBaseUrl}/api/advisor/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey,
        },
        body: JSON.stringify({ message: userMsg }),
      });

      if (res.ok) {
        const data = await res.json();
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: data.response || "No se pudo generar respuesta.",
            products: data.relevant_products || [],
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "Hubo un problema al consultar al Asesor IA. Verifica tu API Key.",
          },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Error de conexión con el servidor Ollama.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating trigger button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 bg-gradient-to-r from-primary to-indigo-600 text-white px-5 py-3 rounded-full shadow-2xl hover:scale-105 active:scale-95 transition-all duration-200"
      >
        <Sparkles className="w-5 h-5 animate-pulse" />
        <span className="font-semibold text-sm">Asesor IA</span>
      </button>

      {/* Chat Drawer / Modal */}
      {isOpen && (
        <div className="fixed bottom-20 right-6 z-50 w-full max-w-md bg-card text-card-foreground border border-border rounded-2xl shadow-2xl overflow-hidden flex flex-col h-[560px] animate-in slide-in-from-bottom-5 duration-200">
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-3.5 bg-gradient-to-r from-primary to-indigo-600 text-white">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <h4 className="font-semibold text-sm leading-tight">Asesor Inteligente</h4>
                <p className="text-[11px] text-white/80">Ollama Qwen2.5 + pgvector</p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 rounded-lg hover:bg-white/20 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Messages Feed */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex gap-2.5 ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {m.role === "assistant" && (
                  <div className="w-7 h-7 rounded-full bg-primary/15 text-primary flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="w-4 h-4" />
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                    m.role === "user"
                      ? "bg-primary text-primary-foreground rounded-br-none"
                      : "bg-muted/60 text-foreground border border-border/80 rounded-bl-none"
                  }`}
                >
                  <p className="whitespace-pre-line">{m.content}</p>

                  {/* Recommended Products Cards */}
                  {m.products && m.products.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-border space-y-2">
                      <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                        Recomendaciones encontradas:
                      </p>
                      {m.products.map((p, pIdx) => (
                        <a
                          key={pIdx}
                          href={p.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center justify-between p-2 rounded-lg bg-card border border-border hover:border-primary text-xs transition-colors"
                        >
                          <div className="truncate mr-2">
                            <span className="font-bold uppercase text-[10px] text-primary">
                              [{p.store}]
                            </span>{" "}
                            <span className="font-medium text-foreground">{p.model_name}</span>
                          </div>
                          <span className="font-extrabold text-emerald-600 shrink-0">
                            {formatCLP(p.current_price_normal)}
                          </span>
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex gap-2.5 items-center text-muted-foreground text-xs">
                <div className="w-7 h-7 rounded-full bg-primary/15 text-primary flex items-center justify-center shrink-0 animate-pulse">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="flex items-center gap-1.5 bg-muted/40 px-3 py-2 rounded-xl">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" />
                  <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:0.2s]" />
                  <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:0.4s]" />
                  <span className="ml-1 text-xs">Analizando catálogo con IA...</span>
                </div>
              </div>
            )}
          </div>

          {/* Form */}
          <form onSubmit={sendMessage} className="p-3 border-t border-border bg-card flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Pregunta por un modelo, marca o presupuesto..."
              className="flex-1 bg-muted/40 border border-input rounded-xl px-3.5 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-3.5 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors shrink-0"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      )}
    </>
  );
}