import { z } from 'zod';
import { WebSocketManager } from '$lib/websocket/manager';
import type { ConnectionState } from '$types/websocket';
import { browser } from '$app/environment';
import { api } from '$api/client';
import { env } from '$env/dynamic/public';
import { invalidateAll } from '$app/navigation';
import { documentStore } from '$lib/runes/document.svelte';
import { mousePositionEventSchema } from '$api/schemas';
import type { CommentEvent } from '$api/types';

import type {
	ConnectedUser,
	HandshakeEvent,
	UserConnectedEvent,
	UserDisconnectedEvent,
	MousePositionEventEnvelope,
	ViewModeChangedEventEnvelope
} from '$types/websocket';
import { SvelteMap } from 'svelte/reactivity';
import { sessionStore } from '$lib/runes/session.svelte';

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

/** All possible WebSocket event types */
type WebSocketEvent =
	| CommentEvent
	| HandshakeEvent
	| UserConnectedEvent
	| UserDisconnectedEvent
	| MousePositionEventEnvelope
	| ViewModeChangedEventEnvelope;

// Zod schemas for WebSocket payload validation
const connectedUserSchema = z.object({
	user_id: z.number(),
	username: z.string(),
	connection_id: z.string(),
	connected_at: z.string()
});

const handshakePayloadSchema = z.object({
	connection_id: z.string(),
	active_users: z.array(connectedUserSchema)
});

const disconnectPayloadSchema = z.object({
	user_id: z.number()
});

/**
 * WebSocket connection for a specific document with active user tracking
 */
class DocumentWebSocketStore {
	private manager: WebSocketManager | null = null;
	// Unsubscribe functions for manager event subscriptions so we can clean them up
	private managerStateUnsubscribe: (() => void) | null = null;
	private managerMessageUnsubscribe: (() => void) | null = null;
	private currentConnectionId: string | null = null;

	// Connection state
	private _state = $state<ConnectionState>('disconnected');
	public readonly state = $derived(this._state);

	// Active users in the document
	private _activeUsers = $state<ConnectedUser[]>([]);
	public readonly activeUsers = $derived(this._activeUsers);

	// User cursor positions (keyed by user_id)
	private _userCursors = new SvelteMap<number, UserCursor>();
	public readonly userCursors = $derived(this._userCursors);

	// Internal event handlers
	private commentEventHandlers: ((event: CommentEvent) => void)[] = [];
	private viewModeEventHandlers: ((event: ViewModeChangedEventEnvelope) => void)[] = [];

	// Throttle tracking for mouse position sending
	private lastMouseSendTime = 0;
	private mouseThrottleMs = 50; // Send at most every 50ms

	// Buffer messages that are emitted before the WebSocket manager is created
	// so we don't lose mouse events that happen early in the page lifecycle.
	private pendingMessageQueue: unknown[] = [];

	constructor() {
		// Start interval to clean up stale user cursors
		const CURSOR_TTL_MS = 2000;
		const CLEANUP_INTERVAL_MS = 1000;

		setInterval(() => {
			const now = Date.now();
			this._userCursors.forEach((cursor, userId) => {
				if (now - cursor.lastUpdate > CURSOR_TTL_MS) {
					this._userCursors.delete(userId);
				}
			});
		}, CLEANUP_INTERVAL_MS);
	}

	/**
	 * Create and connect the WebSocket manager for a given document.
	 * Uses httponly cookies for authentication (no token needed).
	 * Resolves once the manager reports a connected state.
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

		// Subscribe to state changes and message events, and keep unsubscribes
		this.managerStateUnsubscribe = this.manager.on<ConnectionState>('stateChange', (state) => {
			this._state = state;
		});

		this.managerMessageUnsubscribe = this.manager.on<WebSocketEvent>('message', (event) => {
			this.handleEvent(event);
		});

		// Flush any queued messages that were produced before manager creation
		if (this.pendingMessageQueue.length > 0) {
			for (const msg of this.pendingMessageQueue) {
				this.manager.send(msg);
			}
			this.pendingMessageQueue = [];
		}

		// Connect and wait for connected state (or immediate return if already connecting)
		this.manager.connect();

		await new Promise<void>((resolve) => {
			const current = this.manager?.getState();
			if (current === 'connected') {
				resolve();
				return;
			}

			// listen for the first connected state update
			const unsub = this.manager?.on<ConnectionState>('stateChange', (state) => {
				if (state === 'connected') {
					unsub?.();
					resolve();
				}
			});
		});
	}

	private handleEvent(event: unknown): void {
		if (!event || typeof event !== 'object') {
			console.warn('[WS] Received non-object message', event);
			return;
		}

		// Work with a string-keyed view of the payload for runtime checks
		const obj = event as Record<string, unknown>;
		const type = typeof obj.type === 'string' ? obj.type : undefined;
		if (!type) {
			console.warn('[WS] Received message without type', event);
			return;
		}

		switch (type) {
			case 'handshake': {
				const result = handshakePayloadSchema.safeParse(obj.payload);
				if (!result.success) break;
				const payload = result.data;
				this.currentConnectionId = payload.connection_id;
				this._activeUsers = payload.active_users;
				console.log('[WS] Handshake received, active users:', payload.active_users.length);
				break;
			}

			case 'user_connected': {
				const origin = obj.originating_connection_id as string | undefined | null;
				if (origin === this.currentConnectionId) break;
				const result = connectedUserSchema.safeParse(obj.payload);
				if (!result.success) break;
				const payload = result.data;

				if (!this.activeUsers.some((u) => u.user_id === payload.user_id)) {
					this._activeUsers = [...this.activeUsers, payload];
				}
				console.log('[WS] User connected:', payload.username);
				break;
			}

			case 'user_disconnected': {
				const result = disconnectPayloadSchema.safeParse(obj.payload);
				if (!result.success) break;
				const payload = result.data;
				this._activeUsers = this.activeUsers.filter(
					(u) => u.user_id !== payload.user_id || u.user_id === sessionStore.currentUserId
				);
				this._userCursors.delete(payload.user_id);
				console.log('[WS] User disconnected:', payload.user_id);
				break;
			}

			case 'mouse_position': {
				const result = mousePositionEventSchema.safeParse(obj.payload);
				if (!result.success) break;
				const payload = result.data;
				this._userCursors.set(payload.user_id, {
					user_id: payload.user_id,
					username: payload.username,
					x: payload.x,
					y: payload.y,
					page: payload.page,
					visible: payload.visible ?? true,
					lastUpdate: Date.now()
				});
				break;
			}

			case 'create':
			case 'update':
			case 'delete': {
				// Forward comment events to registered handlers
				// make a best-effort cast to CommentEvent
				const ce = obj as unknown as CommentEvent;
				this.commentEventHandlers.forEach((handler) => handler(ce));
				break;
			}

			case 'view_mode_changed': {
				const envelope = obj as unknown as ViewModeChangedEventEnvelope | undefined | null;
				if (!envelope || !envelope.payload) break;
				this.viewModeEventHandlers.forEach((handler) => handler(envelope));

				// Check if user is actively editing - defer refresh until they're done
				const hasEditingComment = !!documentStore.comments.editing.size;
				if (hasEditingComment) {
					documentStore.setViewMode(envelope.payload.view_mode);
				} else {
					invalidateAll();
				}
				break;
			}
		}
	}

	disconnect(): void {
		// Clean up manager subscriptions first
		if (this.managerStateUnsubscribe) {
			this.managerStateUnsubscribe();
			this.managerStateUnsubscribe = null;
		}

		if (this.managerMessageUnsubscribe) {
			this.managerMessageUnsubscribe();
			this.managerMessageUnsubscribe = null;
		}

		if (this.manager) {
			this.manager.disconnect();
			this.manager = null;
		}
		this._state = 'disconnected';
		this._activeUsers = [];
		this._userCursors.clear();
		this.currentConnectionId = null;
		this.commentEventHandlers = [];
		this.viewModeEventHandlers = [];
	}

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

	onCommentEvent(handler: (event: CommentEvent) => void): () => void {
		this.commentEventHandlers.push(handler);
		return () => {
			this.commentEventHandlers = this.commentEventHandlers.filter((h) => h !== handler);
		};
	}

	onViewModeChanged(handler: (event: ViewModeChangedEventEnvelope) => void): () => void {
		this.viewModeEventHandlers.push(handler);
		return () => {
			this.viewModeEventHandlers = this.viewModeEventHandlers.filter((h) => h !== handler);
		};
	}

	send(data: unknown): void {
		if (this.manager) {
			this.manager.send(data);
			return;
		}

		// Manager doesn't exist yet: keep message until connect() creates a manager.
		this.pendingMessageQueue.push(data);
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
