import { writable } from 'svelte/store';
import { api } from '$api/client';
import type { CommentRead, CommentCreate, CommentUpdate } from '$api/types';
import type { Annotation } from '$types/pdf';
import type { Paginated } from '$api/pagination';
import { notification } from './notificationStore';

/**
 * Centralized store for managing comment tree state and API operations
 */
class CommentStore {
	private store = writable<CommentRead[]>([]);
	private documentId: string | null = null;
	private currentUserId: number | null = null;
	private repliesCache: Map<number, CommentRead[]> = new Map();
	private cacheVersion = writable(0); // Incremented when cache changes

	/**
	 * Subscribe to comment changes
	 */
	subscribe = this.store.subscribe;

	/**
	 * Initialize the store with document context and load root comments
	 */
	async initialize(documentId: string, currentUserId: number | null = null): Promise<void> {
		this.documentId = documentId;
		this.currentUserId = currentUserId;
		await this.loadRootComments();
	}

	/**
	 * Load all root-level comments (with annotations, no parent)
	 */
	private async loadRootComments(): Promise<void> {
		if (!this.documentId) return;

		const limit = 50;
		let offset = 0;
		const allComments: CommentRead[] = [];

		while (true) {
			const result = await api.get<Paginated<CommentRead, 'document'>>(
				`/comments?offset=${offset}&limit=${limit}`,
				{
					filters: [
						{ field: 'parent_id', operator: 'exists', value: 'false' },
						{ field: 'annotation', operator: 'exists', value: 'true' },
						{ field: 'document_id', operator: '==', value: this.documentId }
					]
				}
			);

			if (!result.success) {
				notification(result.error);
				return;
			}

			allComments.push(...result.data.data);

			if (result.data.total <= result.data.offset + result.data.limit) {
				break;
			}
			offset += limit;
		}

		this.store.set(allComments);
	}

	/**
	 * Subscribe to cache version changes (for reactivity)
	 */
	subscribeToCacheVersion = this.cacheVersion.subscribe;

	/**
	 * Increment cache version to trigger reactivity
	 */
	private incrementCacheVersion(): void {
		this.cacheVersion.update((v) => v + 1);
	}

	/**
	 * Check if replies are already cached for a comment
	 */
	hasRepliesCache(commentId: number): boolean {
		return this.repliesCache.has(commentId);
	}

	/**
	 * Get cached replies for a comment
	 */
	getCachedReplies(commentId: number): CommentRead[] | undefined {
		return this.repliesCache.get(commentId);
	}

	/**
	 * Load replies for a specific comment (uses cache if available)
	 */
	async loadReplies(commentId: number, forceRefresh: boolean = false): Promise<CommentRead[]> {
		if (!this.documentId) return [];

		// Return cached replies if available and not forcing refresh
		if (!forceRefresh && this.repliesCache.has(commentId)) {
			return this.repliesCache.get(commentId)!;
		}

		const result = await api.get<Paginated<CommentRead, never>>(`/comments?limit=50`, {
			filters: [
				{ field: 'parent_id', operator: '==', value: commentId.toString() },
				{ field: 'document_id', operator: '==', value: this.documentId }
			]
		});

		if (!result.success) {
			notification(result.error);
			return [];
		}

		// Cache the replies
		this.repliesCache.set(commentId, result.data.data);
		this.incrementCacheVersion();

		return result.data.data;
	}

	/**
	 * Create a new comment (can be root or reply)
	 */
	async create(data: {
		content?: string;
		annotation?: Annotation;
		parentId?: number;
		visibility?: 'public' | 'private' | 'restricted';
	}): Promise<CommentRead | null> {
		if (!this.documentId) return null;

		const commentData: CommentCreate = {
			document_id: this.documentId,
			content: data.content || null,
			annotation: data.annotation ? (data.annotation as unknown as { [k: string]: unknown }) : null,
			parent_id: data.parentId || null,
			visibility: data.visibility || 'public'
		};

		const result = await api.post<CommentRead>('/comments', commentData);

		if (!result.success) {
			notification(result.error);
			return null;
		}

		// Update local state
		if (data.parentId) {
			// Add to parent's cached replies and increment num_replies
			const cachedReplies = this.repliesCache.get(data.parentId) || [];
			this.repliesCache.set(data.parentId, [...cachedReplies, result.data]);
			this.incrementCacheVersion();

			// Increment parent's num_replies count
			this.updateCommentInTree(data.parentId, (comment) => ({
				...comment,
				num_replies: comment.num_replies + 1
			}));
		} else {
			// Add as root comment
			this.store.update((comments) => [...comments, result.data]);
		}

		return result.data;
	}

	/**
	 * Update an existing comment in the local tree
	 */
	private updateCommentInTree(commentId: number, updater: (comment: CommentRead) => CommentRead): void {
		// First, try to update in the root store
		let found = false;
		this.store.update((comments) => {
			const updated = comments.map((comment) => {
				if (comment.id === commentId) {
					found = true;
					return updater(comment);
				}
				return comment;
			});
			return updated;
		});

		// If not found in root, search through all cached replies
		if (!found) {
			for (const [parentId, replies] of this.repliesCache.entries()) {
				const updatedReplies = replies.map((reply) =>
					reply.id === commentId ? updater(reply) : reply
				);
				if (updatedReplies !== replies) {
					this.repliesCache.set(parentId, updatedReplies);
					this.incrementCacheVersion();
					found = true;
					break;
				}
			}
		}
	}

	/**
	 * Update an existing comment
	 */
	async update(commentId: number, data: CommentUpdate): Promise<boolean> {
		const result = await api.update(`/comments/${commentId}`, data);

		if (!result.success) {
			notification(result.error);
			return false;
		}

		// Update in local tree
		this.updateCommentInTree(commentId, (comment) => ({
			...comment,
			content: data.content ?? comment.content,
			visibility: data.visibility ?? comment.visibility,
			annotation: data.annotation ?? comment.annotation,
			updated_at: new Date().toISOString()
		}));

		return true;
	}

	/**
	 * Find the parent ID of a comment by searching the cache
	 */
	private findParentId(commentId: number): number | null {
		// Search through cached replies to find which parent contains this comment
		for (const [parentId, replies] of this.repliesCache.entries()) {
			if (replies.some((reply) => reply.id === commentId)) {
				return parentId;
			}
		}
		return null;
	}

	/**
	 * Delete a comment
	 */
	async delete(commentId: number, parentId?: number): Promise<boolean> {
		const result = await api.delete(`/comments/${commentId}`);

		if (!result.success) {
			notification(result.error);
			return false;
		}

		// If parentId not provided, try to find it
		const actualParentId = parentId ?? this.findParentId(commentId);

		// Update local state
		if (actualParentId) {
			// Remove from parent's cached replies
			const cachedReplies = this.repliesCache.get(actualParentId) || [];
			this.repliesCache.set(
				actualParentId,
				cachedReplies.filter((reply) => reply.id !== commentId)
			);
			this.incrementCacheVersion();

			// Decrement parent's num_replies count
			this.updateCommentInTree(actualParentId, (comment) => ({
				...comment,
				num_replies: Math.max(0, comment.num_replies - 1)
			}));
		} else {
			// Remove root comment from store and its cache
			this.repliesCache.delete(commentId);
			this.incrementCacheVersion();
			this.store.update((comments) => comments.filter((comment) => comment.id !== commentId));
		}

		return true;
	}

	/**
	 * Get current userId
	 */
	getCurrentUserId(): number | null {
		return this.currentUserId;
	}

	/**
	 * Clear the store
	 */
	clear(): void {
		this.store.set([]);
		this.repliesCache.clear();
		this.documentId = null;
		this.currentUserId = null;
	}
}

// Export singleton instance
export const commentStore = new CommentStore();
