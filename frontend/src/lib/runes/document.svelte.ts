import { api } from '$api/client';
import type { Paginated } from '$api/pagination';
import type {
	CommentCreate,
	CommentEvent,
	CommentRead,
	CommentUpdate,
	DocumentRead
} from '$api/types';
import { notification } from '$lib/stores/notificationStore';
import type { Annotation, CommentGroup, PageData } from '$types/pdf';
import { SvelteMap } from 'svelte/reactivity';

export interface CachedComment extends CommentRead {
	highlightElement: HTMLElement | null;
	replies?: CachedComment[];
	isActive: boolean;
}

const toCachedComment = (comment: CommentRead): CachedComment => ({
	...comment,
	highlightElement: null,
	isActive: false
});

/** Search the comment in root comments and replies recursively */
const findComment = (inComments: CachedComment[], commentId: number): CachedComment | undefined => {
	return (
		inComments.find((c) => c.id === commentId) ??
		findComment(
			inComments.flatMap((c) => c.replies ?? []),
			commentId
		)
	);
};

const removeCommentRecursively = (
	fromComments: CachedComment[],
	commentId: number
): CachedComment[] => {
	return fromComments
		.filter((c) => c.id !== commentId)
		.map((c) => ({
			...c,
			replies: c.replies ? removeCommentRecursively(c.replies, commentId) : []
		}));
};

/**
 * Generate a stable group ID from comment IDs.
 * Uses the smallest comment ID to ensure stability when comments are added/removed from group.
 */
const generateStableGroupId = (commentIds: number[]): string => {
	return `group-${Math.min(...commentIds)}`;
};

/**
 * Compute the vertical position of a comment's highlight relative to scroll container.
 * Returns null if required refs are not available or element is detached from DOM.
 */
const getHighlightTop = (
	comment: CachedComment,
	scrollContainerRef: HTMLElement | null
): number | null => {
	if (!comment.highlightElement || !scrollContainerRef) return null;

	// Verify element is still connected to the DOM
	if (!comment.highlightElement.isConnected) return null;

	const highlightRect = comment.highlightElement.getBoundingClientRect();
	const scrollRect = scrollContainerRef.getBoundingClientRect();
	const scrollTop = scrollContainerRef.scrollTop;

	return highlightRect.top - scrollRect.top + scrollTop;
};

const createDocumentStore = () => {
	// Core state
	let comments = $state<CachedComment[]>([]);
	let loadedDocument = $state<DocumentRead | undefined>(undefined);

	// DOM refs (bound via bind:this in components)
	let pdfViewerRef = $state<HTMLElement | null>(null);
	let scrollContainerRef = $state<HTMLElement | null>(null);
	let commentSidebarRef = $state<HTMLDivElement | null>(null);
	const pageData = new SvelteMap<number, PageData>();

	// Group memory: maps groupId -> last active commentId in that group
	const lastActivePerGroup = new SvelteMap<string, number>();

	// Layout version - needed because getBoundingClientRect isn't reactive
	let layoutVersion = $state(0);

	/**
	 * Trigger layout recalculation (for scale changes, highlight registration, etc.)
	 */
	const invalidateLayout = (): void => {
		layoutVersion++;
	};

	/**
	 * Set the active comment. Updates isActive on all comments.
	 * Optionally remembers the selection for a group.
	 */
	const setActive = (commentId: number | null, groupId?: string): void => {
		// Remember last active for the group
		if (groupId && commentId !== null) {
			lastActivePerGroup.set(groupId, commentId);
		}

		// Update isActive on all comments - map creates new array to trigger reactivity
		comments = comments.map((c) => {
			c.isActive = c.id === commentId;
			return c;
		});
	};

	/**
	 * Get the last active comment ID for a group, or null if none.
	 */
	const getLastActiveForGroup = (groupId: string): number | null => {
		return lastActivePerGroup.get(groupId) ?? null;
	};

	/**
	 * Derived: Comment groups with stable IDs.
	 * Groups comments by vertical proximity of their highlights.
	 * Returns empty array if DOM refs aren't ready.
	 */
	const commentGroups = $derived.by((): CommentGroup[] => {
		// Read layoutVersion to trigger recalculation when layout changes
		void layoutVersion;

		// Early return if refs not ready
		if (!scrollContainerRef || !commentSidebarRef) {
			return [];
		}

		// Filter comments that have highlight elements and compute their positions
		const positionedComments: Array<{ comment: CachedComment; top: number }> = [];

		for (const comment of comments) {
			const top = getHighlightTop(comment, scrollContainerRef);
			if (top !== null) {
				positionedComments.push({ comment, top });
			}
		}

		if (positionedComments.length === 0) {
			return [];
		}

		// Sort by vertical position
		positionedComments.sort((a, b) => a.top - b.top);

		// Group by proximity (comments within 40px of the first in group are grouped)
		const GROUP_THRESHOLD = 40;
		const groups: CommentGroup[] = [];
		let currentGroup: Array<{ comment: CachedComment; top: number }> = [];

		for (const item of positionedComments) {
			if (currentGroup.length === 0) {
				currentGroup.push(item);
			} else {
				const firstTop = currentGroup[0].top;
				if (Math.abs(item.top - firstTop) <= GROUP_THRESHOLD) {
					currentGroup.push(item);
				} else {
					// Finalize current group
					const commentIds = currentGroup.map((c) => c.comment.id);
					const avgTop = currentGroup.reduce((sum, c) => sum + c.top, 0) / currentGroup.length;
					groups.push({
						id: generateStableGroupId(commentIds),
						commentIds,
						idealTop: avgTop,
						actualTop: avgTop // Will be adjusted by collision detection
					});
					currentGroup = [item];
				}
			}
		}

		// Add last group
		if (currentGroup.length > 0) {
			const commentIds = currentGroup.map((c) => c.comment.id);
			const avgTop = currentGroup.reduce((sum, c) => sum + c.top, 0) / currentGroup.length;
			groups.push({
				id: generateStableGroupId(commentIds),
				commentIds,
				idealTop: avgTop,
				actualTop: avgTop
			});
		}

		// Apply collision detection using fixed height estimate
		// (Dynamic heights cause reactivity loops - groups render -> register -> invalidate -> recompute)
		const COLLAPSED_HEIGHT = 32;
		const MIN_GAP = 8;

		for (let i = 0; i < groups.length; i++) {
			const group = groups[i];

			if (i === 0) {
				group.actualTop = Math.max(0, group.idealTop);
			} else {
				const prev = groups[i - 1];
				const prevBottom = prev.actualTop + COLLAPSED_HEIGHT + MIN_GAP;
				group.actualTop = Math.max(group.idealTop, prevBottom);
			}
		}

		return groups;
	});

	// ============ Reply Loading ============

	/**
	 * Load replies for a comment. Stores results in comment.replies.
	 */
	const loadReplies = async (
		commentId: number,
		forceRefresh: boolean = false
	): Promise<CachedComment[]> => {
		if (!loadedDocument) return [];

		const comment = findComment(comments, commentId);
		if (!comment) return [];

		// Return cached if available and not forcing refresh
		if (!forceRefresh && comment.replies !== undefined) {
			return comment.replies;
		}

		const result = await api.get<Paginated<CommentRead, never>>(`/comments?limit=50`, {
			filters: [
				{ field: 'parent_id', operator: '==', value: commentId.toString() },
				{ field: 'document_id', operator: '==', value: loadedDocument.id }
			]
		});

		if (!result.success) {
			notification(result.error);
			return [];
		}

		// Store replies directly on the comment
		comment.replies = result.data.data.map(toCachedComment);
		

		return comment.replies;
	};

	/**
	 * Get cached replies for a comment (synchronous).
	 */
	const getCachedReplies = (commentId: number): CachedComment[] | undefined => {
		const comment = findComment(comments, commentId);
		return comment?.replies;
	};

	// ============ Comment CRUD ============

	/**
	 * Load root comments for a document.
	 */
	const loadRootComments = async (document: DocumentRead): Promise<void> => {
		const limit = 50;
		let offset = 0;

		comments = [];
		loadedDocument = document;
		layoutVersion = 0;
		lastActivePerGroup.clear();

		while (true) {
			const result = await api.get<Paginated<CommentRead, 'document'>>(
				`/comments?offset=${offset}&limit=${limit}`,
				{
					filters: [
						{ field: 'parent_id', operator: 'exists', value: 'false' },
						{ field: 'annotation', operator: 'exists', value: 'true' },
						{ field: 'document_id', operator: '==', value: document.id }
					]
				}
			);

			if (!result.success) {
				notification(result.error);
				loadedDocument = undefined;
				return;
			}

			comments = [...comments, ...result.data.data.map((c) => toCachedComment(c))];

			if (result.data.total <= result.data.offset + result.data.limit) {
				break;
			}
			offset += limit;
		}
	};

	/**
	 * Create a new comment (root or reply).
	 */
	const createComment = async (options: {
		annotation?: Annotation;
		content?: string;
		parentId?: number;
		visibility?: 'public' | 'private' | 'restricted';
	}): Promise<CommentRead | null> => {
		if (!loadedDocument) return null;

		const result = await api.post<CommentRead>('/comments', {
			annotation: options.annotation
				? (options.annotation as unknown as Record<string, unknown>)
				: null,
			content: options.content ?? null,
			document_id: loadedDocument.id,
			parent_id: options.parentId ?? null,
			visibility: options.visibility ?? loadedDocument.view_mode
		} satisfies CommentCreate);

		if (!result.success) {
			notification(result.error);
			return null;
		}

		if (options.parentId) {
			// Add to parent's replies array
			const parentComment = findComment(comments, options.parentId);
			if (parentComment) {
				if (!parentComment.replies) {
					parentComment.replies = [];
				}
				parentComment.replies = [...parentComment.replies, toCachedComment(result.data)];
				parentComment.num_replies = (parentComment.num_replies || 0) + 1;
				
			}
		} else {
			// Add as root comment
			comments = [...comments, toCachedComment(result.data)];
		}

		return result.data;
	};

	/**
	 * Update a comment.
	 */
	const updateComment = async (commentId: number, data: CommentUpdate): Promise<boolean> => {
		const result = await api.update(`/comments/${commentId}`, data);
		if (!result.success) {
			notification(result.error);
			return false;
		}

		// Update in comments array (includes nested replies via findComment)
		const targetComment = findComment(comments, commentId);
		if (targetComment) {
			Object.assign(targetComment, data);
			
		}

		return true;
	};

	/**
	 * Delete a comment.
	 */
	const deleteComment = async (commentId: number, parentId?: number): Promise<boolean> => {
		const result = await api.delete(`/comments/${commentId}`);
		if (!result.success) {
			notification(result.error);
			return false;
		}

		if (parentId) {
			// Remove from parent's replies array
			const parentComment = findComment(comments, parentId);
			if (parentComment && parentComment.replies) {
				parentComment.replies = parentComment.replies.filter((r) => r.id !== commentId);
				parentComment.num_replies = Math.max(0, (parentComment.num_replies || 0) - 1);
				
			}
		} else {
			// Remove from root comments
			comments = removeCommentRecursively(comments, commentId);
		}

		return true;
	};

	/**
	 * Handle WebSocket events for real-time updates.
	 */
	const handleWebSocketEvent = (event: CommentEvent): void => {
		if (!event.payload) {
			console.warn('Received WebSocket event with no payload', event);
			return;
		}

		const comment = event.payload;

		switch (event.type) {
			case 'create':
				if (comment.parent_id) {
					// Add to parent's replies if loaded
					const parentComment = findComment(comments, comment.parent_id);
					if (parentComment) {
						if (parentComment.replies && !parentComment.replies.some((r) => r.id === comment.id)) {
							parentComment.replies = [...parentComment.replies, toCachedComment(comment)];
						}
						parentComment.num_replies = (parentComment.num_replies || 0) + 1;
						
					}
				} else {
					// Add as root comment if not already present
					if (!comments.some((c) => c.id === comment.id)) {
						comments = [...comments, toCachedComment(comment)];
					}
				}
				break;

			case 'update': {
				const targetComment = findComment(comments, comment.id);
				if (targetComment) {
					// Preserve local state (highlightElement, isActive, replies)
					const { highlightElement, isActive, replies } = targetComment;
					Object.assign(targetComment, comment, { highlightElement, isActive, replies });
					
				}
				break;
			}

			case 'delete': {
				// Try to remove from nested replies first, otherwise from root
				const removed = removeFromReplies(comments, comment.id);
				if (!removed) {
					comments = removeCommentRecursively(comments, comment.id);
				}
				break;
			}

			default:
				console.warn('Unknown WebSocket event type:', event.type);
		}
	};

	/**
	 * Helper: Remove a comment from any parent's replies array.
	 * Returns true if found and removed.
	 */
	const removeFromReplies = (fromComments: CachedComment[], commentId: number): boolean => {
		for (const c of fromComments) {
			if (c.replies) {
				const idx = c.replies.findIndex((r) => r.id === commentId);
				if (idx !== -1) {
					c.replies = c.replies.filter((r) => r.id !== commentId);
					c.num_replies = Math.max(0, (c.num_replies || 0) - 1);
					return true;
				}
				// Recurse into nested replies
				if (removeFromReplies(c.replies, commentId)) {
					return true;
				}
			}
		}
		return false;
	};

	/**
	 * Clear all state (call on destroy).
	 */
	const clear = (): void => {
		comments = [];
		loadedDocument = undefined;
		lastActivePerGroup.clear();
		layoutVersion = 0;
	};

	return {
		// State (reactive getters)
		get comments() {
			return comments;
		},
		set comments(value: CachedComment[]) {
			comments = value;
		},
		get commentGroups() {
			return commentGroups;
		},

		// DOM refs (need both get and set for bind:this)
		get pdfViewerRef() {
			return pdfViewerRef;
		},
		set pdfViewerRef(value: HTMLElement | null) {
			pdfViewerRef = value;
		},
		get scrollContainerRef() {
			return scrollContainerRef;
		},
		set scrollContainerRef(value: HTMLElement | null) {
			scrollContainerRef = value;
		},
		get commentSidebarRef() {
			return commentSidebarRef;
		},
		set commentSidebarRef(value: HTMLDivElement | null) {
			commentSidebarRef = value;
		},
		pageData,

		// Methods
		setActive,
		getLastActiveForGroup,
		invalidateLayout,
		loadReplies,
		getCachedReplies,
		loadRootComments,
		create: createComment,
		updateComment,
		deleteComment,
		handleWebSocketEvent,
		clear
	};
};

export const documentStore = createDocumentStore();
