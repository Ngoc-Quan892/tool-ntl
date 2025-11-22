import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { WS_URL } from "../lib/constants";
import { usePredictionStore, useGameStore } from "../stores";
import { Prediction } from "../types";

export const useWebSocket = () => {
  const queryClient = useQueryClient();
  const { setPrediction } = usePredictionStore();
  const { addToHistory } = useGameStore();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);

  const connect = () => {
    try {
      const ws = new WebSocket(WS_URL);
      
      ws.onopen = () => {
        console.log("WebSocket connected");
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          
          // Handle different message types
          switch (payload.type) {
            case "prediction_update":
              if (payload.data) {
                const prediction = payload.data as Prediction;
                setPrediction(prediction);
                queryClient.setQueryData(["prediction"], prediction);
              }
              break;
            
            case "result_added":
              if (payload.data?.result) {
                addToHistory(payload.data.result);
                queryClient.invalidateQueries({ queryKey: ["history"] });
                queryClient.invalidateQueries({ queryKey: ["stats"] });
              }
              break;
            
            case "reset":
              queryClient.invalidateQueries();
              break;
            
            case "heartbeat":
              // Respond to heartbeat
              if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "pong" }));
              }
              break;
            
            default:
              console.log("Unknown WebSocket message type:", payload.type);
          }
        } catch (error) {
          console.error("WebSocket message parse failed", error);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };

      ws.onclose = () => {
        console.log("WebSocket disconnected");
        wsRef.current = null;
        
        // Reconnect with exponential backoff
        if (reconnectAttempts.current < 5) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          reconnectAttempts.current++;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error("Failed to create WebSocket:", error);
    }
  };

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [queryClient, setPrediction, addToHistory]);
};
