import { writable, derived, get } from 'svelte/store';
import { WebSocketManager } from '$lib/websocket/manager';
import type { ConnectionState } from '$types/websocket';
import { browser } from '$app/environment';
import { api } from '$api/client';
import { env } from '$env/dynamic/public';
import type { CommentEvent } from '$api/types';

/** Represents a user connected to a document */
export interface ConnectedUser {
	user_id: number;
	username: string;
	connection_id: string;
	connected_at: string;
}

/** Represents a user's cursor position */
export interface UserCursor {
	user_id: number;
	username: string;
	x: number; // Normalized 0-1
	y: number; // Normalized 0-1
	page: number;
	visible: boolean;
	lastUpdate: number; // Timestamp for cleanup
}

/** Handshake response from server */
interface HandshakeEvent {
	type: 'handshake';
	payload: {
		connection_id: string;
		active_users: ConnectedUser[];
	};
}

/** User connected event */
interface UserConnectedEvent {
	type: 'user_connected';
	payload: ConnectedUser;
	originating_connection_id?: string;
}

/** User disconnected event */
interface UserDisconnectedEvent {
	type: 'user_disconnected';
	payload: {
		user_id: number;
	};
}

/** Mouse position event from other users */
interface MousePositionEvent {
	type: 'mouse_position';
	payload: {
		user_id: number;
		username: string;
		x: number;
		y: number;
		page: number;
		visible: boolean;
	};
	originating_connection_id?: string;
}

/** All possible WebSocket event types */
type WebSocketEvent =
	| CommentEvent
	| HandshakeEvent
	| UserConnectedEvent
	| UserDisconnectedEvent
	| MousePositionEvent;

/**
 * WebSocket connection for a specific document with active user tracking
 */
class DocumentWebSocketStore {
	private manager: WebSocketManager | null = null;
	private currentConnectionId: string | null = null;

	// Connection state
	private stateStore = writable<ConnectionState>('disconnected');

	// Active users in the document
	private activeUsersStore = writable<ConnectedUser[]>([]);

	// User cursor positions (keyed by user_id)
	private userCursorsStore = writable<Map<number, UserCursor>>(new Map());

	// Export as readonly
	public readonly state = derived(this.stateStore, ($state) => $state);
	public readonly activeUsers = derived(this.activeUsersStore, ($users) => $users);
	public readonly userCursors = derived(this.userCursorsStore, ($cursors) => $cursors);

	// Internal event handlers
	private commentEventHandlers: ((event: CommentEvent) => void)[] = [];

	// Throttle tracking for mouse position sending
	private lastMouseSendTime = 0;
	private mouseThrottleMs = 50; // Send at most every 50ms

	/**
	 * Initialize WebSocket connection for a document
	 * Uses httponly cookies for authentication (no token needed)
	 */
	async connect(documentId: string): Promise<void> {
		if (!browser) return;

		// Disconnect any existing connection
		this.disconnect();

		const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
		const host = env.PUBLIC_BACKEND_BASEURL.replace(/^https?:\/\//, '').replace(/\/$/, '');
		const wsUrl = `${protocol}//${host}/api/documents/${documentId}/events/comments?connection_id=${api.getConnectionId()}`;

		// Create manager
		this.manager = new WebSocketManager({
			url: wsUrl,
			reconnectDelay: 1000,
			maxReconnectDelay: 30000,
			maxReconnectAttempts: 10
		});

		// Subscribe to state changes
		this.manager.on<ConnectionState>('stateChange', (state) => {
			this.stateStore.set(state);
		});

		// Handle all incoming messages
		this.manager.on<WebSocketEvent>('message', (event) => {
			this.handleEvent(event);
		});

		// Connect
		this.manager.connect();
	}

	/**
	 * Handle incoming WebSocket events
	 */
	private handleEvent(event: WebSocketEvent): void {
		switch (event.type) {
			case 'handshake':
				// Initial handshake - set connection ID and active users
				this.currentConnectionId = event.payload.connection_id;
				this.activeUsersStore.set(event.payload.active_users);
				console.log('[WS] Handshake received, active users:', event.payload.active_users.length);
				break;

			case 'user_connected':
				// Skip our own connection event
				if (event.originating_connection_id === this.currentConnectionId) break;
				// Add new user to the list
				this.activeUsersStore.update((users) => {
					// Don't add if already exists
					if (users.some((u) => u.user_id === event.payload.user_id)) return users;
					return [...users, event.payload];
				});
				console.log('[WS] User connected:', event.payload.username);
				break;

			case 'user_disconnected':
				// Remove user from the list
				this.activeUsersStore.update((users) =>
					users.filter((u) => u.user_id !== event.payload.user_id)
				);
				// Also remove their cursor
				this.userCursorsStore.update((cursors) => {
					cursors.delete(event.payload.user_id);
					return new Map(cursors);
				});
				console.log('[WS] User disconnected:', event.payload.user_id);
				break;

			case 'mouse_position':
				// Update cursor position for this user
				this.userCursorsStore.update((cursors) => {
					cursors.set(event.payload.user_id, {
						user_id: event.payload.user_id,
						username: event.payload.username,
						x: event.payload.x,
						y: event.payload.y,
						page: event.payload.page,
						visible: event.payload.visible,
						lastUpdate: Date.now()
					});
					return new Map(cursors);
				});
				break;

			case 'create':
			case 'update':
			case 'delete':
			case 'custom':
				// Forward comment events to registered handlers
				this.commentEventHandlers.forEach((handler) => handler(event as CommentEvent));
				break;
		}
	}

	/**
	 * Disconnect from WebSocket
	 */
	disconnect(): void {
		if (this.manager) {
			this.manager.disconnect();
			this.manager = null;
		}
		this.stateStore.set('disconnected');
		this.activeUsersStore.set([]);
		this.userCursorsStore.set(new Map());
		this.currentConnectionId = null;
		this.commentEventHandlers = [];
	}

	/**
	 * Send mouse position update (throttled)
	 */
	sendMousePosition(x: number, y: number, page: number, visible: boolean = true): void {
		const now = Date.now();
		if (now - this.lastMouseSendTime < this.mouseThrottleMs) {
			return; // Throttle
		}
		this.lastMouseSendTime = now;

		this.send({
			type: 'mouse_position',
			payload: { x, y, page, visible }
		});
	}

	/**
	 * Subscribe to comment events
	 * Returns an unsubscribe function
	 */
	onCommentEvent(handler: (event: CommentEvent) => void): () => void {
		this.commentEventHandlers.push(handler);
		return () => {
			this.commentEventHandlers = this.commentEventHandlers.filter((h) => h !== handler);
		};
	}

	/**
	 * Get the current connection ID
	 */
	getConnectionId(): string | null {
		return this.currentConnectionId;
	}

	/**
	 * Get active users as a plain array (for non-store contexts)
	 */
	getActiveUsers(): ConnectedUser[] {
		return get(this.activeUsersStore);
	}

	/**
	 * Send a message to the server (for future bidirectional features)
	 */
	send(data: unknown): void {
		if (this.manager) {
			this.manager.send(data);
		} else {
			console.warn('Cannot send message: WebSocket not connected');
		}
	}

	/**
	 * Get current connection state
	 */
	getState(): ConnectionState {
		return this.manager?.getState() ?? 'disconnected';
	}
}

// Export singleton instance
export const documentWebSocket = new DocumentWebSocketStore();
