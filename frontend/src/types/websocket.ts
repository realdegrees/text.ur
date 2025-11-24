import type { ViewMode } from '$api/types';

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

/** Represents a user connected to a document (handshake / presence updates)
 */
export interface ConnectedUser {
	user_id: number;
	username: string;
	connection_id: string;
	connected_at: string;
}

/** Handshake response from the server when joining a comments channel. */
export interface HandshakeEvent {
	type: 'handshake';
	payload: {
		connection_id: string;
		active_users: ConnectedUser[];
	};
}

/** Event emitted when another user connects to the document comments channel. */
export interface UserConnectedEvent {
	type: 'user_connected';
	payload: ConnectedUser;
	originating_connection_id?: string | null;
}

/** Event emitted when a user disconnects from the comments channel. */
export interface UserDisconnectedEvent {
	type: 'user_disconnected';
	payload: { user_id: number };
}

/** Envelope emitted by the server for mouse cursor updates. */
export interface MousePositionEventEnvelope {
	type: 'mouse_position';
	payload: {
		user_id: number;
		username: string;
		x: number;
		y: number;
		page: number;
		visible?: boolean;
	};
	originating_connection_id?: string | null;
}

/** Envelope used for view-mode change events */
export interface ViewModeChangedEventEnvelope {
	type: 'view_mode_changed';
	payload: {
		document_id: string;
		view_mode: ViewMode;
	};
	originating_connection_id?: string | null;
}
