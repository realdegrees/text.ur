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
