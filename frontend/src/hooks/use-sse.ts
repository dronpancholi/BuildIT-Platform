"use client";

import { useState, useEffect, useRef } from "react";
import { API_BASE_URL, MOCK_TENANT_ID } from "@/lib/api";

export function useSSE<T = any>(tenantId: string = MOCK_TENANT_ID, channel?: string) {
  const [lastEvent, setLastEvent] = useState<T | null>(null);
  const [eventHistory, setEventHistory] = useState<T[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const retryRef = useRef(0);

  useEffect(() => {
    const url = channel
      ? `${API_BASE_URL}/stream/${tenantId}?channels=${channel}`
      : `${API_BASE_URL}/stream/${tenantId}`;

    const connect = () => {
      if (esRef.current) esRef.current.close();
      const es = new EventSource(url);
      esRef.current = es;

      es.onopen = () => {
        retryRef.current = 0;
        setIsConnected(true);
      };

      es.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as T;
          setLastEvent(parsed);
          setEventHistory((prev) => [parsed, ...prev].slice(0, 500));
        } catch {
        }
      };

      es.onerror = () => {
        es.close();
        setIsConnected(false);
        const delay = Math.min(1000 * 2 ** retryRef.current, 30000);
        retryRef.current += 1;
        setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
    };
  }, [tenantId, channel]);

  return { lastEvent, eventHistory, isConnected };
}
