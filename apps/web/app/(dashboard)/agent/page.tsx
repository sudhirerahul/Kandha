// Repatriation Agent — real SSE streaming from FastAPI → GMI / Kimi K2
"use client";

import { useEffect, useRef, useState } from "react";
import { useUser } from "@clerk/nextjs";
import { createAgentSession, sendAgentMessage } from "@/lib/api";

type Role = "user" | "agent";

interface Message {
  id: string;
  role: Role;
  content: string;
  streaming?: boolean;
}

export default function AgentPage() {
  const { user } = useUser();
  const userId = user?.id ?? "anonymous";

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Create session on mount
  useEffect(() => {
    createAgentSession(userId)
      .then((s) => {
        setSessionId(s.session_id);
        setMessages([
          {
            id: "welcome",
            role: "agent",
            content:
              "Hello. I'm Kimi K2 running on the Kandha Repatriation Agent.\n\nI can audit your cloud architecture and build a sequenced migration plan to bare-metal infrastructure.\n\n**What's your primary application stack?** (e.g. microservices on ECS, monolith on EC2, Kubernetes on EKS)",
          },
        ]);
      })
      .catch((e: unknown) => {
        setSessionError(e instanceof Error ? e.message : "Failed to connect to agent API.");
      });
  }, [userId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  async function handleSend() {
    const text = input.trim();
    if (!text || isThinking || !sessionId) return;

    const userMsgId = Date.now().toString();
    const agentMsgId = (Date.now() + 1).toString();

    setMessages((prev) => [...prev, { id: userMsgId, role: "user", content: text }]);
    setInput("");
    setIsThinking(true);

    try {
      const stream = await sendAgentMessage(sessionId, text, userId);
      const reader = stream.getReader();

      setIsThinking(false);
      setMessages((prev) => [
        ...prev,
        { id: agentMsgId, role: "agent", content: "", streaming: true },
      ]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        if (value.type === "chunk" && value.content) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === agentMsgId
                ? { ...m, content: m.content + value.content }
                : m,
            ),
          );
        }

        if (value.type === "done" || value.type === "error") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === agentMsgId
                ? {
                    ...m,
                    streaming: false,
                    content:
                      value.type === "error"
                        ? `Error: ${value.message ?? "Unknown error"}`
                        : m.content,
                  }
                : m,
            ),
          );
          break;
        }
      }
    } catch (e) {
      setIsThinking(false);
      const errMsg = e instanceof Error ? e.message : "Connection error";
      setMessages((prev) => [
        ...prev,
        { id: agentMsgId, role: "agent", content: `Error: ${errMsg}`, streaming: false },
      ]);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-8 py-5 border-b border-border/40 shrink-0">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono mb-0.5">
            <span className="text-cyan-400">02</span>
            <span>/</span>
            <span>repatriation-agent</span>
            {sessionId && (
              <>
                <span className="text-muted-foreground/40">·</span>
                <span className="text-muted-foreground/50">{sessionId.slice(0, 8)}</span>
              </>
            )}
          </div>
          <h1 className="text-lg font-bold tracking-tight text-foreground">Repatriation Agent</h1>
        </div>
        <div className="flex items-center gap-2">
          <div
            className={`flex items-center gap-1.5 text-xs border rounded-lg px-2.5 py-1 ${
              sessionError
                ? "text-red-400 border-red-400/20 bg-red-400/5"
                : sessionId
                  ? "text-emerald-400 border-emerald-400/20 bg-emerald-400/5"
                  : "text-muted-foreground border-border/40"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                sessionError ? "bg-red-400" : sessionId ? "bg-emerald-400 animate-pulse" : "bg-muted-foreground"
              }`}
            />
            {sessionError ? "disconnected" : sessionId ? "kimi-k2-5" : "connecting…"}
          </div>
          <button className="text-xs text-muted-foreground border border-border/50 rounded-lg px-2.5 py-1 hover:border-border hover:text-foreground transition-colors cursor-pointer">
            Export plan
          </button>
        </div>
      </div>

      {/* Error banner */}
      {sessionError && (
        <div className="mx-8 mt-4 rounded-xl border border-red-400/20 bg-red-400/5 px-4 py-3 text-sm text-red-400">
          <strong>Could not connect to the agent API.</strong> Make sure the FastAPI server is running on{" "}
          <code className="font-mono text-xs">localhost:8000</code>.
          <div className="text-xs mt-1 text-red-400/70">{sessionError}</div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-8 py-6 space-y-6">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
            <div
              className={`w-7 h-7 rounded-lg shrink-0 flex items-center justify-center mt-0.5 ${
                msg.role === "agent"
                  ? "bg-cyan-500/15 border border-cyan-500/20 text-cyan-400"
                  : "bg-muted/50 border border-border/50 text-muted-foreground"
              }`}
            >
              {msg.role === "agent" ? <AgentIcon /> : <UserIcon />}
            </div>
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === "agent"
                  ? "glass border border-border/50"
                  : "bg-cyan-500/10 border border-cyan-500/15"
              }`}
            >
              <FormattedContent content={msg.content} />
              {msg.streaming && msg.content.length > 0 && (
                <span className="inline-block w-2 h-3.5 bg-cyan-400 ml-0.5 animate-[blink_1s_step-end_infinite] align-text-bottom" />
              )}
            </div>
          </div>
        ))}

        {isThinking && (
          <div className="flex gap-4">
            <div className="w-7 h-7 rounded-lg shrink-0 flex items-center justify-center bg-cyan-500/15 border border-cyan-500/20 mt-0.5">
              <AgentIcon />
            </div>
            <div className="glass border border-border/50 rounded-2xl px-4 py-3">
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400/70 animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400/70 animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400/70 animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Suggested prompts — show only at start */}
      {messages.length === 1 && sessionId && (
        <div className="px-8 pb-3 flex flex-wrap gap-2">
          {SUGGESTED.map((s) => (
            <button
              key={s}
              onClick={() => setInput(s)}
              className="text-xs text-muted-foreground border border-border/40 rounded-xl px-3 py-1.5 hover:border-cyan-400/30 hover:text-foreground hover:bg-cyan-500/5 transition-all cursor-pointer"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="px-8 pb-8 pt-3 shrink-0">
        <div className="glass-bright rounded-2xl border border-border/50 focus-within:border-cyan-400/30 transition-colors">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!sessionId || !!sessionError}
            placeholder={
              sessionError
                ? "Agent offline — check API server"
                : sessionId
                  ? "Describe your stack or ask about the migration plan…"
                  : "Connecting to agent…"
            }
            rows={3}
            className="w-full bg-transparent text-sm text-foreground placeholder:text-muted-foreground/50 resize-none p-4 focus:outline-none font-sans leading-relaxed disabled:opacity-40"
          />
          <div className="flex items-center justify-between px-4 pb-3">
            <div className="text-xs text-muted-foreground/50 font-mono">
              Enter to send · Shift+Enter for new line
            </div>
            <button
              onClick={() => void handleSend()}
              disabled={!input.trim() || isThinking || !sessionId || !!sessionError}
              className="flex items-center gap-1.5 bg-cyan-500 disabled:bg-muted disabled:text-muted-foreground/40 text-background rounded-xl px-4 py-2 text-xs font-semibold hover:bg-cyan-400 disabled:cursor-not-allowed transition-all cursor-pointer"
            >
              Send
              <SendIcon />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function FormattedContent({ content }: { content: string }) {
  const parts = content.split(/(\*\*.*?\*\*)/g);
  return (
    <>
      {parts.map((part, i) =>
        part.startsWith("**") && part.endsWith("**") ? (
          <strong key={i} className="text-foreground font-semibold">
            {part.slice(2, -2)}
          </strong>
        ) : (
          <span key={i} className="text-foreground/80 whitespace-pre-wrap">
            {part}
          </span>
        ),
      )}
    </>
  );
}

const SUGGESTED = [
  "We run microservices on ECS",
  "Monolith on EC2 + RDS",
  "Kubernetes on EKS",
  "Serverless on Lambda + S3",
];

// ─── Icons ────────────────────────────────────────────────────────────────────

function AgentIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 2a4 4 0 0 1 4 4v2a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z" />
      <path d="M6 21v-1a6 6 0 0 1 12 0v1" />
    </svg>
  );
}

function UserIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 20v-1a8 8 0 0 1 16 0v1" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}
