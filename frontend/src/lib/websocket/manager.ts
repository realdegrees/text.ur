import type {
	ConnectionState,
	IWebSocketManager,
	WebSocketConfig
} from '$types/websocket';

/**
 * WebSocket manager with auto-reconnect and event handling
 */
export class WebSocketManager implements IWebSocketManager {
	private ws: WebSocket | null = null;
	private config: Required<WebSocketConfig>;
	private state: ConnectionState = 'disconnected';
	private reconnectAttempts = 0;
	private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
	private eventHandlers: Map<string, Set<(data: unknown) => void>> = new Map();
	private messageQueue: unknown[] = [];

	constructor(config: WebSocketConfig) {
		this.config = {
			reconnectDelay: 1000,
			maxReconnectDelay: 30000,
			maxReconnectAttempts: Infinity,
			...config
		};
	}

	/**
	 * Connect to WebSocket server
	 */
	connect(): void {
		if (this.ws?.readyState === WebSocket.OPEN || this.state === 'connecting') {
			return;
		}

		this.setState('connecting');

		try {
			this.ws = new WebSocket(this.config.url);

			this.ws.onopen = () => {
				this.setState('connected');
				this.reconnectAttempts = 0;

				// Send any queued messages
				while (this.messageQueue.length > 0) {
					const data = this.messageQueue.shift();
					if (data) this.send(data);
				}

				this.emit('open', null);
			};

			this.ws.onmessage = (event) => {
				try {
					const data = JSON.parse(event.data);
					this.emit('message', data);
				} catch (error) {
					console.error('Failed to parse WebSocket message:', error);
				}
			};

			this.ws.onerror = (error) => {
				console.error('WebSocket error:', error);
				this.setState('error');
				this.emit('error', error);
			};

			this.ws.onclose = (event) => {
				this.ws = null;
				this.setState('disconnected');
				this.emit('close', event);

				// Attempt reconnection if not a normal closure
				if (event.code !== 1000 && this.reconnectAttempts < this.config.maxReconnectAttempts) {
					this.scheduleReconnect();
				}
			};
		} catch (error) {
			console.error('Failed to create WebSocket connection:', error);
			this.setState('error');
			this.emit('error', error);
		}
	}

	/**
	 * Disconnect from WebSocket server
	 */
	disconnect(): void {
		if (this.reconnectTimeout) {
			clearTimeout(this.reconnectTimeout);
			this.reconnectTimeout = null;
		}

		if (this.ws) {
			this.ws.close(1000, 'Normal closure');
			this.ws = null;
		}

		this.setState('disconnected');
		this.reconnectAttempts = 0;
		this.messageQueue = [];
	}

	/**
	 * Send data to WebSocket server
	 */
	send(data: unknown): void {
		if (this.ws?.readyState === WebSocket.OPEN) {
			this.ws.send(JSON.stringify(data));
		} else {
			// Queue message for later if not connected
			this.messageQueue.push(data);
		}
	}

	/**
	 * Subscribe to WebSocket events
	 * @returns Unsubscribe function
	 */
	on<T = unknown>(event: string, handler: (data: T) => void): () => void {
		if (!this.eventHandlers.has(event)) {
			this.eventHandlers.set(event, new Set());
		}

		const handlers = this.eventHandlers.get(event)!;
		handlers.add(handler as (data: unknown) => void);

		// Return unsubscribe function
		return () => {
			handlers.delete(handler as (data: unknown) => void);
			if (handlers.size === 0) {
				this.eventHandlers.delete(event);
			}
		};
	}

	/**
	 * Get current connection state
	 */
	getState(): ConnectionState {
		return this.state;
	}

	/**
	 * Emit event to all registered handlers
	 */
	private emit(event: string, data: unknown): void {
		const handlers = this.eventHandlers.get(event);
		if (handlers) {
			handlers.forEach((handler) => {
				try {
					handler(data);
				} catch (error) {
					console.error(`Error in WebSocket event handler for "${event}":`, error);
				}
			});
		}
	}

	/**
	 * Set connection state and emit state change event
	 */
	private setState(state: ConnectionState): void {
		if (this.state !== state) {
			this.state = state;
			this.emit('stateChange', state);
		}
	}

	/**
	 * Schedule reconnection with exponential backoff
	 */
	private scheduleReconnect(): void {
		if (this.reconnectTimeout) {
			return;
		}

		const delay = Math.min(
			this.config.reconnectDelay * Math.pow(2, this.reconnectAttempts),
			this.config.maxReconnectDelay
		);

		this.reconnectAttempts++;

		this.reconnectTimeout = setTimeout(() => {
			this.reconnectTimeout = null;
			this.connect();
		}, delay);
	}
}
