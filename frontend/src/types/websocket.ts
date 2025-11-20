import type { CommentRead } from '$api/types';

/**
 * WebSocket event types matching backend Event model
 */
export type EventType = 'create' | 'update' | 'delete' | 'custom';

/**
 * Base WebSocket event structure
 */
export interface WebSocketEvent<T = unknown> {
	event_id: string;
	published_at: string;
	payload: T | null;
	resource_id: number | null;
	resource: string | null;
	type: EventType;
}

/**
 * Comment-specific WebSocket events
 */
export type CommentEvent = WebSocketEvent<CommentRead>;

/**
 * WebSocket connection states
 */
export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error';

/**
 * WebSocket connection configuration
 */
export interface WebSocketConfig {
	/** WebSocket URL */
	url: string;
	/** Reconnection delay in ms */
	reconnectDelay?: number;
	/** Maximum reconnection delay in ms */
	maxReconnectDelay?: number;
	/** Maximum number of reconnection attempts */
	maxReconnectAttempts?: number;
}

/**
 * WebSocket manager interface
 */
export interface IWebSocketManager {
	connect(): void;
	disconnect(): void;
	send(data: unknown): void;
	on<T = unknown>(event: string, handler: (data: T) => void): () => void;
	getState(): ConnectionState;
}
