import { browser } from '$app/environment';
import type { CommentState } from '$lib/runes/document.svelte';

/**
 * Fields from CommentState persisted across page refreshes.
 * Note: editInputContent is NOT persisted as it's just a draft while editing
 */
type PersistedFields = Pick<CommentState, 'isPinned' | 'replyInputContent' | 'repliesExpanded'>;

interface StorageEntry {
	states: Record<number, Partial<PersistedFields>>;
	lastAccessed: number;
}

const PREFIX = 'text.ur:comment-state';
const TTL_MS = 30 * 24 * 60 * 60 * 1000;

const getKey = (userId: number, documentId: string) => `${PREFIX}:${userId}:${documentId}`;

export function cleanupExpiredCommentStates(): void {
	if (!browser) return;

	const now = Date.now();
	const keysToRemove: string[] = [];

	for (let i = 0; i < localStorage.length; i++) {
		const key = localStorage.key(i);
		if (!key?.startsWith(PREFIX)) continue;

		try {
			const data = JSON.parse(localStorage.getItem(key)!) as StorageEntry;
			if (now - data.lastAccessed > TTL_MS) keysToRemove.push(key);
		} catch {
			keysToRemove.push(key);
		}
	}

	keysToRemove.forEach((key) => localStorage.removeItem(key));
}

export function saveCommentStates(
	userId: number,
	documentId: string,
	states: Map<number, CommentState>
): void {
	if (!browser) return;

	const statesObj: Record<number, Partial<PersistedFields>> = {};

	for (const [commentId, state] of states) {
		const persisted: Partial<PersistedFields> = {};

		// Only save isPinned if explicitly true
		if (state.isPinned === true) persisted.isPinned = true;

		// Only save repliesExpanded if explicitly true
		if (state.repliesExpanded === true) persisted.repliesExpanded = true;

		// Only save reply input content if it's not empty
		if (state.replyInputContent && state.replyInputContent.trim()) {
			persisted.replyInputContent = state.replyInputContent;
		}

		if (Object.keys(persisted).length > 0) statesObj[commentId] = persisted;
	}

	console.log('[commentStorage] Saving states:', {
		userId,
		documentId,
		key: getKey(userId, documentId),
		stateCount: Object.keys(statesObj).length,
		states: statesObj
	});

	try {
		localStorage.setItem(
			getKey(userId, documentId),
			JSON.stringify({ states: statesObj, lastAccessed: Date.now() })
		);
	} catch (error) {
		console.warn('Failed to save comment states:', error);
	}
}

export function loadCommentStates(
	userId: number,
	documentId: string
): Map<number, Partial<PersistedFields>> {
	const result = new Map<number, Partial<PersistedFields>>();

	if (!browser) return result;

	try {
		const key = getKey(userId, documentId);
		const stored = localStorage.getItem(key);

		console.log('[commentStorage] Loading states:', {
			userId,
			documentId,
			key,
			hasStored: !!stored
		});

		if (!stored) return result;

		const entry = JSON.parse(stored) as StorageEntry;

		if (Date.now() - entry.lastAccessed > TTL_MS) {
			console.log('[commentStorage] States expired, removing');
			localStorage.removeItem(key);
			return result;
		}

		entry.lastAccessed = Date.now();
		localStorage.setItem(key, JSON.stringify(entry));

		Object.entries(entry.states).forEach(([id, state]) => {
			result.set(parseInt(id), state);
		});

		console.log('[commentStorage] Loaded states:', {
			stateCount: result.size,
			states: Object.fromEntries(result)
		});
	} catch (error) {
		console.warn('Failed to load comment states:', error);
	}

	return result;
}

export function clearCommentStates(userId: number, documentId: string): void {
	if (!browser) return;
	localStorage.removeItem(getKey(userId, documentId));
}

export function clearAllCommentStates(userId: number): void {
	if (!browser) return;
	const prefix = `${PREFIX}:${userId}:`;
	for (let i = localStorage.length - 1; i >= 0; i--) {
		const key = localStorage.key(i);
		if (key?.startsWith(prefix)) localStorage.removeItem(key);
	}
}
