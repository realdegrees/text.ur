import { writable, derived } from 'svelte/store';
import { WebSocketManager } from '$lib/websocket/manager';
import type { ConnectionState } from '$types/websocket';
import { browser } from '$app/environment';
import { api } from '$api/client';
import { env } from '$env/dynamic/public';
import type { CommentEvent } from '$api/types';

/**
 * WebSocket connection for a specific document
 */
class DocumentWebSocketStore {
	private manager: WebSocketManager | null = null;
	private documentId: string | null = null;

	// Connection state
	private stateStore = writable<ConnectionState>('disconnected');

	// Export as readonly
	public readonly state = derived(this.stateStore, ($state) => $state);

	/**
	 * Initialize WebSocket connection for a document
	 * Uses httponly cookies for authentication (no token needed)
	 */
	async connect(documentId: string): Promise<void> {
		if (!browser) return;

		// Disconnect any existing connection
		this.disconnect();

		this.documentId = documentId;

		// Get connection ID from API client

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

		// Connect
		this.manager.connect();
	}

	/**
	 * Disconnect from WebSocket
	 */
	disconnect(): void {
		if (this.manager) {
			this.manager.disconnect();
			this.manager = null;
		}
		this.documentId = null;
		this.stateStore.set('disconnected');
	}

	/**
	 * Subscribe to comment events
	 */
	onCommentEvent(handler: (event: CommentEvent) => void): () => void {
		if (!this.manager) {
			console.warn('Cannot subscribe to comment events: WebSocket not connected');
			return () => {};
		}

		return this.manager.on<CommentEvent>('message', handler);
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
