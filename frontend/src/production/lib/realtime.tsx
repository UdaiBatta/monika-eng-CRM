import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";

export type RealtimeStatus = "connecting" | "live" | "reconnecting" | "offline";

export type PresenceUser = {
  user_id: string;
  display_name: string;
  seen_at: number;
};

type RealtimeContextValue = {
  status: RealtimeStatus;
  presence: Record<string, PresenceUser[]>;
  subscribe: (entityType: string, entityId: string) => () => void;
};

const RealtimeContext = createContext<RealtimeContextValue | null>(null);

const queryRoots: Record<string, string[]> = {
  customer: ["customers", "customer"],
  enquiry: ["enquiries", "enquiry"],
  engineering_feasibility_review: ["engineering-reviews", "engineering-review"],
  commercial_estimate: ["commercial-estimates", "commercial-estimate"],
  external_enquiry_submission: ["incoming-enquiries", "incoming-enquiry"],
  quotation: ["quotations", "quotation"],
  quotation_revision: ["quotations", "quotation"],
  approval_request: ["approvals", "approval"],
  document: ["documents", "document"],
  notification: ["notifications"],
};

function entityKey(entityType: string, entityId: string) {
  return `${entityType}:${entityId}`;
}

export function RealtimeProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<RealtimeStatus>("connecting");
  const [presence, setPresence] = useState<Record<string, PresenceUser[]>>({});
  const socket = useRef<WebSocket | null>(null);
  const subscriptions = useRef(new Map<string, { entityType: string; entityId: string; count: number }>());
  const seenEvents = useRef(new Set<string>());

  useEffect(() => {
    let closed = false;
    let attempt = 0;
    let reconnectTimer: number | undefined;
    let heartbeatTimer: number | undefined;

    const sendSubscriptions = () => {
      for (const item of subscriptions.current.values()) {
        socket.current?.send(JSON.stringify({
          type: "subscribe",
          entity_type: item.entityType,
          entity_id: item.entityId,
        }));
      }
    };

    const connect = () => {
      if (closed) return;
      setStatus(attempt ? "reconnecting" : "connecting");
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const next = new WebSocket(`${protocol}//${window.location.host}/ws/workspace/`);
      socket.current = next;
      next.addEventListener("open", () => {
        attempt = 0;
        setStatus("live");
        sendSubscriptions();
      });
      next.addEventListener("message", (event) => {
        let message: Record<string, unknown>;
        try {
          message = JSON.parse(event.data) as Record<string, unknown>;
        } catch {
          return;
        }
        if (message.type === "domain.event") {
          const eventId = String(message.event_id ?? "");
          if (eventId && seenEvents.current.has(eventId)) return;
          if (eventId) {
            seenEvents.current.add(eventId);
            if (seenEvents.current.size > 500) seenEvents.current.clear();
          }
          for (const root of queryRoots[String(message.entity_type)] ?? []) {
            void queryClient.invalidateQueries({ queryKey: [root] });
          }
        }
        if (message.type === "presence.changed") {
          const key = entityKey(String(message.entity_type), String(message.entity_id));
          setPresence((current) => ({ ...current, [key]: message.users as PresenceUser[] }));
        }
      });
      next.addEventListener("close", () => {
        if (closed) return;
        socket.current = null;
        setStatus(navigator.onLine ? "reconnecting" : "offline");
        const delay = Math.min(30_000, 1_000 * 2 ** attempt++);
        reconnectTimer = window.setTimeout(connect, delay);
      });
      next.addEventListener("error", () => next.close());
    };

    connect();
    heartbeatTimer = window.setInterval(() => {
      if (socket.current?.readyState !== WebSocket.OPEN) return;
      for (const item of subscriptions.current.values()) {
        socket.current.send(JSON.stringify({
          type: "presence.heartbeat",
          entity_type: item.entityType,
          entity_id: item.entityId,
        }));
      }
    }, 25_000);
    return () => {
      closed = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      if (heartbeatTimer) window.clearInterval(heartbeatTimer);
      socket.current?.close();
    };
  }, [queryClient]);

  const subscribe = useCallback((entityType: string, entityId: string) => {
    if (!entityId) return () => undefined;
    const key = entityKey(entityType, entityId);
    const existing = subscriptions.current.get(key);
    if (existing) existing.count += 1;
    else subscriptions.current.set(key, { entityType, entityId, count: 1 });
    if (!existing && socket.current?.readyState === WebSocket.OPEN) {
      socket.current.send(JSON.stringify({ type: "subscribe", entity_type: entityType, entity_id: entityId }));
    }
    return () => {
      const item = subscriptions.current.get(key);
      if (!item) return;
      item.count -= 1;
      if (item.count > 0) return;
      subscriptions.current.delete(key);
      if (socket.current?.readyState === WebSocket.OPEN) {
        socket.current.send(JSON.stringify({ type: "unsubscribe", entity_type: entityType, entity_id: entityId }));
      }
      setPresence((current) => {
        const next = { ...current };
        delete next[key];
        return next;
      });
    };
  }, []);

  const value = useMemo(() => ({ status, presence, subscribe }), [presence, status, subscribe]);
  return <RealtimeContext.Provider value={value}>{children}</RealtimeContext.Provider>;
}

export function useRealtime() {
  const value = useContext(RealtimeContext);
  if (!value) throw new Error("useRealtime must be used within RealtimeProvider");
  return value;
}

export function useRealtimeEntity(entityType: string, entityId?: string) {
  const { presence, subscribe } = useRealtime();
  useEffect(() => {
    if (!entityId) return;
    return subscribe(entityType, entityId);
  }, [entityId, entityType, subscribe]);
  return entityId ? presence[entityKey(entityType, entityId)] ?? [] : [];
}
