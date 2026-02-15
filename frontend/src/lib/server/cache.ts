/**
 * Simple in-memory TTL cache for server-side use.
 * Entries expire after the configured TTL and are lazily cleaned up.
 */
export class TTLCache<T> {
	private cache = new Map<string, { data: T; expires: number }>();

	constructor(private ttlMs: number) {}

	get(key: string): T | undefined {
		const entry = this.cache.get(key);
		if (!entry) return undefined;
		if (Date.now() > entry.expires) {
			this.cache.delete(key);
			return undefined;
		}
		return entry.data;
	}

	set(key: string, data: T): void {
		this.cache.set(key, { data, expires: Date.now() + this.ttlMs });
	}

	delete(key: string): void {
		this.cache.delete(key);
	}
}

/** Cache for /api/users/me responses, keyed by access_token. 30-second TTL. */
export const userCache = new TTLCache<unknown>(30_000);
