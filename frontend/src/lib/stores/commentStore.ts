import { writable, get } from 'svelte/store';
import { api } from '$api/client';
import type { CommentRead, CommentCreate, CommentUpdate } from '$api/types';
import type { Annotation } from '$types/pdf';
import type { Paginated } from '$api/pagination';
import { notification } from './notificationStore';

/**
 * Utility functions for manipulating nested comment trees
 */
class CommentTreeUtils {
	/**
	 * Recursively find and update a comment in the tree
	 */
	static updateInTree(
		comments: CommentRead[],
		commentId: number,
		updater: (comment: CommentRead) => CommentRead
	): CommentRead[] {
		return comments.map((comment) => {
			if (comment.id === commentId) {
				return updater(comment);
			}
			if (comment.replies && comment.replies.length > 0) {
				return {
					...comment,
					replies: this.updateInTree(comment.replies, commentId, updater)
				};
			}
			return comment;
		});
	}

	/**
	 * Recursively find and delete a comment from the tree
	 */
	static deleteFromTree(comments: CommentRead[], commentId: number): CommentRead[] {
		return comments
			.filter((comment) => comment.id !== commentId)
			.map((comment) => {
				if (comment.replies && comment.replies.length > 0) {
					return {
						...comment,
						replies: this.deleteFromTree(comment.replies, commentId)
					};
				}
				return comment;
			});
	}

	/**
	 * Recursively add a reply to a parent comment in the tree
	 */
	static addReplyToTree(
		comments: CommentRead[],
		parentId: number,
		newReply: CommentRead
	): CommentRead[] {
		return comments.map((comment) => {
			if (comment.id === parentId) {
				return {
					...comment,
					replies: [...(comment.replies || []), newReply]
				};
			}
			if (comment.replies && comment.replies.length > 0) {
				return {
					...comment,
					replies: this.addReplyToTree(comment.replies, parentId, newReply)
				};
			}
			return comment;
		});
	}
}

/**
 * Centralized store for managing comment tree state and API operations
 */
class CommentStore {
	private store = writable<CommentRead[]>([]);
	private documentId: string | null = null;
	private currentUserId: number | null = null;

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
	 * Load replies for a specific comment
	 */
	async loadReplies(commentId: number): Promise<CommentRead[]> {
		if (!this.documentId) return [];

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
			// Add as reply to parent
			this.store.update((comments) =>
				CommentTreeUtils.addReplyToTree(comments, data.parentId!, result.data)
			);
		} else {
			// Add as root comment
			this.store.update((comments) => [...comments, result.data]);
		}

		return result.data;
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

		// Update local state
		this.store.update((comments) =>
			CommentTreeUtils.updateInTree(comments, commentId, (comment) => ({
				...comment,
				content: data.content ?? comment.content,
				visibility: data.visibility ?? comment.visibility,
				annotation: data.annotation ?? comment.annotation,
				updated_at: new Date().toISOString()
			}))
		);

		return true;
	}

	/**
	 * Delete a comment
	 */
	async delete(commentId: number): Promise<boolean> {
		const result = await api.delete(`/comments/${commentId}`);

		if (!result.success) {
			notification(result.error);
			return false;
		}

		// Update local state
		this.store.update((comments) => CommentTreeUtils.deleteFromTree(comments, commentId));

		return true;
	}

	/**
	 * Update replies for a specific comment (used when async loading)
	 */
	updateReplies(commentId: number, replies: CommentRead[]): void {
		this.store.update((comments) =>
			CommentTreeUtils.updateInTree(comments, commentId, (comment) => ({
				...comment,
				replies
			}))
		);
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
		this.documentId = null;
		this.currentUserId = null;
	}
}

// Export singleton instance
export const commentStore = new CommentStore();

// Export utility class for direct use if needed
export { CommentTreeUtils };
