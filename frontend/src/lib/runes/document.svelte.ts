import { api } from '$api/client';
import type {
	CommentCreate,
	CommentEvent,
	CommentRead,
	CommentUpdate,
	DocumentRead,
	ViewMode
} from '$api/types';
import type { Paginated } from '$api/pagination';
import { notification } from '$lib/stores/notificationStore';
import type { Annotation } from '$types/pdf';

export interface CachedComment extends CommentRead {
	replies?: CachedComment[];
	// Interaction state flags
	isHighlightHovered?: boolean; // Mouse over the PDF highlight
	isBadgeHovered?: boolean; // Mouse over the comment badge
	isSelected?: boolean; // Currently selected/active comment
	isPinned?: boolean; // Clicked to stay open
	isEditing?: boolean; // In edit mode
	// UI state
	isRepliesCollapsed?: boolean; // Replies section is collapsed
}

const toCachedComment = (comment: CommentRead): CachedComment => ({
	...comment
});

/** Search the comment in root comments and replies recursively */
const findComment = (inComments: CachedComment[], commentId: number): CachedComment | undefined => {
	for (const c of inComments) {
		if (c.id === commentId) return c;
		if (c.replies) {
			const found = findComment(c.replies, commentId);
			if (found) return found;
		}
	}
	return undefined;
};

/** Get all comments flattened (root + all nested replies) */
const flattenComments = (inComments: CachedComment[]): CachedComment[] => {
	const result: CachedComment[] = [];
	for (const c of inComments) {
		result.push(c);
		if (c.replies) {
			result.push(...flattenComments(c.replies));
		}
	}
	return result;
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

/** Find the parent comment of a given comment by its parent_id */
const findParentOfComment = (
	inComments: CachedComment[],
	parentId: number | null | undefined
): CachedComment | undefined => {
	if (!parentId) return undefined;
	return findComment(inComments, parentId);
};

const createDocumentStore = () => {
	let comments: CachedComment[] = $state<CachedComment[]>([]);
	let loadedDocument: DocumentRead | undefined = $state<DocumentRead | undefined>(undefined);
	// Track if a comment card is actively being interacted with (badge hovered or tab clicked)
	let isCommentCardActive: boolean = $state<boolean>(false);
	let pdfViewerRef: HTMLElement | null = $state<HTMLElement | null>(null);
	let scrollContainerRef: HTMLElement | null = $state<HTMLElement | null>(null);
	let commentSidebarRef: HTMLDivElement | null = $state<HTMLDivElement | null>(null);
	// Track which comment has an active reply input
	let replyingToCommentId: number | null = $state<number | null>(null);
	// Filter state (local only - doesn't affect fetched data)
	// Map of user ID -> filter state (include | exclude). Absence = none.
	type AuthorFilterState = 'include' | 'exclude';
	let authorFilterStates: Map<number, AuthorFilterState> = $state<Map<number, AuthorFilterState>>(
		new Map()
	);
	// Flag to defer invalidation when view mode changes during editing
	let pendingViewModeRefresh: boolean = $state<boolean>(false);
	// Toggle for showing other users' cursors
	let showOtherCursors: boolean = $state<boolean>(true);

	const setDocument = (document: DocumentRead) => {
		loadedDocument = document;
	};

	const setCommentCardActive = (active: boolean) => {
		isCommentCardActive = active;
	};

	const setPdfViewerRef = (ref: HTMLElement | null) => {
		pdfViewerRef = ref;
	};

	const setScrollContainerRef = (ref: HTMLElement | null) => {
		scrollContainerRef = ref;
	};

	const setCommentSidebarRef = (ref: HTMLDivElement | null) => {
		commentSidebarRef = ref;
	};

	// Resets the store and loads root comments for a document
	const setRootComments = async (rootComments: CommentRead[]): Promise<void> => {
		comments = rootComments.map(toCachedComment);
	};

	// Helper to update a flag on a specific comment (clears the flag on all others)
	const setCommentFlag = (
		commentId: number | null,
		flag: 'isHighlightHovered' | 'isBadgeHovered' | 'isSelected' | 'isPinned' | 'isEditing'
	) => {
		const allComments = flattenComments(comments);
		for (const c of allComments) {
			c[flag] = c.id === commentId;
		}
		comments = [...comments]; // trigger reactivity
	};

	// Set highlight hovered state (when mouse is over PDF highlight)
	const setHighlightHovered = (commentId: number | null) => {
		setCommentFlag(commentId, 'isHighlightHovered');
	};

	// Set badge hovered state (when mouse is over comment badge)
	const setBadgeHovered = (commentId: number | null) => {
		setCommentFlag(commentId, 'isBadgeHovered');
	};

	// Set selected state
	const setSelected = (commentId: number | null) => {
		setCommentFlag(commentId, 'isSelected');
	};

	// Set pinned state
	const setPinned = (commentId: number | null) => {
		setCommentFlag(commentId, 'isPinned');
	};

	// Set editing state
	const setEditing = (commentId: number | null) => {
		setCommentFlag(commentId, 'isEditing');
		// When editing ends, check if we have a pending view mode refresh
		if (commentId === null && pendingViewModeRefresh) {
			pendingViewModeRefresh = false;
			// Dynamically import to avoid circular dependency
			import('$app/navigation').then(({ invalidateAll }) => invalidateAll());
		}
	};

	// Set pending view mode refresh flag (called when view mode changes during editing)
	const setPendingViewModeRefresh = (pending: boolean) => {
		pendingViewModeRefresh = pending;
	};

	// Set replying state (tracks which comment has reply input open)
	const setReplyingTo = (commentId: number | null) => {
		replyingToCommentId = commentId;
	};

	// Filter setters
	/**
	 * Cycle a user's filter state: none -> include -> exclude -> none
	 */
	const toggleAuthorFilter = (userId: number): void => {
		// eslint-disable-next-line svelte/prefer-svelte-reactivity
		const newStates = new Map(authorFilterStates);
		const current = newStates.get(userId);

		if (!current) {
			newStates.set(userId, 'include');
		} else if (current === 'include') {
			newStates.set(userId, 'exclude');
		} else {
			newStates.delete(userId);
		}

		authorFilterStates = newStates;
	};

	/** Clear all author filters (reset to none) */
	const clearAuthorFilter = (): void => {
		authorFilterStates = new Map();
	};

	const setShowOtherCursors = (show: boolean) => {
		showOtherCursors = show;
	};

	// Toggle replies collapsed state for a specific comment
	const toggleRepliesCollapsed = (commentId: number) => {
		const comment = findComment(comments, commentId);
		if (comment) {
			comment.isRepliesCollapsed = !comment.isRepliesCollapsed;
			comments = [...comments]; // trigger reactivity
		}
	};

	// Clear all interaction state on all comments
	const clearAllInteractionState = () => {
		const allComments = flattenComments(comments);
		for (const c of allComments) {
			c.isHighlightHovered = false;
			c.isBadgeHovered = false;
			c.isSelected = false;
			c.isPinned = false;
			c.isEditing = false;
		}
		isCommentCardActive = false;
		comments = [...comments]; // trigger reactivity
	};

	const updateComment = async (commentId: number, data: CommentUpdate) => {
		const result = await api.update(`/comments/${commentId}`, data);
		if (!result.success) {
			notification(result.error);
			return;
		}
		const targetComment = findComment(comments, commentId);
		if (targetComment) {
			Object.assign(targetComment, data);
		}
		comments = [...comments]; // trigger reactivity
	};

	const createComment = async (options: {
		annotation?: Annotation;
		content?: string;
		parentId?: number;
	}): Promise<CachedComment | undefined> => {
		if (!loadedDocument) return;
		const result = await api.post<CommentRead>('/comments', {
			annotation: options.annotation
				? (options.annotation as unknown as Record<string, unknown>)
				: undefined,
			content: options.content,
			parent_id: options.parentId,
			document_id: loadedDocument.id,
			visibility: 'public' // New highlight comments are always public by default
		} satisfies CommentCreate);
		if (!result.success) {
			notification(result.error);
			return;
		}
		const newComment = toCachedComment(result.data);
		if (options.parentId) {
			const parentComment = findComment(comments, options.parentId);
			if (parentComment) {
				// Only add to replies array if replies are already loaded
				// Otherwise, increment num_replies so the "Load replies" button updates
				if (parentComment.replies) {
					parentComment.replies.push(newComment);
				} else if (parentComment.num_replies === 0) {
					parentComment.replies = [toCachedComment(newComment)];
				}
				parentComment.num_replies = (parentComment.num_replies || 0) + 1;
			}
			comments = [...comments]; // trigger reactivity
		} else {
			// Root comment - add to top level
			comments = [...comments, newComment];
		}
		return newComment;
	};

	const deleteComment = async (commentId: number) => {
		// Find the comment first to get its parent_id
		const commentToDelete = findComment(comments, commentId);

		const result = await api.delete(`/comments/${commentId}`);
		if (!result.success) {
			notification(result.error);
			return;
		}

		// Decrement parent's num_replies if this was a reply
		if (commentToDelete?.parent_id) {
			const parentComment = findParentOfComment(comments, commentToDelete.parent_id);
			if (parentComment && parentComment.num_replies > 0) {
				parentComment.num_replies--;
			}
		}

		comments = removeCommentRecursively(comments, commentId);
	};

	const loadReplies = async (commentId: number): Promise<CachedComment[] | undefined> => {
		const result = await api.get<Paginated<CommentRead>>('/comments', {
			filters: [{ field: 'parent_id', operator: '==', value: commentId.toString() }]
		});
		if (!result.success) {
			notification(result.error);
			return;
		}

		const replies = result.data.data.map(toCachedComment);
		const parentComment = findComment(comments, commentId);
		if (parentComment) {
			parentComment.replies = replies;
			comments = [...comments]; // trigger reactivity
		}
		return replies;
	};

	const handleWebSocketEvent = (
		event:
			| CommentEvent
			| { type: 'view_mode_changed'; payload: { document_id?: string; view_mode?: ViewMode } }
	): void => {
		// Handle explicit view-mode changed events (no longer delivered as 'custom')
		if (event.type === 'view_mode_changed') {
			const vm = event.payload as { document_id?: string; view_mode?: ViewMode };
			if (vm?.view_mode && vm?.document_id && loadedDocument) {
				loadedDocument.view_mode = vm.view_mode;
				console.log(`[WS] Document view_mode updated to ${vm.view_mode}`);
			}
			return;
		}

		if (!event.payload) {
			console.warn('Received WebSocket event with no payload', event);
			return;
		}

		// payload is narrowed per-case; we'll cast to CommentRead when handling comment events below

		switch (event.type) {
			case 'create':
				{
					const comment = event.payload as CommentRead;
					if (comment.parent_id) {
						const parentComment = findComment(comments, comment.parent_id);
						if (parentComment) {
							// Only add to replies array if replies are already loaded unless the number of replies was 0 then we can safely add it
							if (parentComment.replies) {
								parentComment.replies.push(toCachedComment(comment));
							} else if (parentComment.num_replies === 0) {
								parentComment.replies = [toCachedComment(comment)];
							}
							parentComment.num_replies = (parentComment.num_replies || 0) + 1;
						}
						comments = [...comments]; // trigger reactivity
					} else {
						comments = [...comments, toCachedComment(comment)];
					}
				}
				break;

			case 'update': {
				const comment = event.payload as CommentRead;
				const targetComment = findComment(comments, comment.id);
				if (targetComment) {
					Object.assign(targetComment, comment);
					comments = [...comments]; // trigger reactivity
				}
				break;
			}

			case 'delete': {
				const comment = event.payload as CommentRead;
				// Decrement parent's num_replies if this was a reply
				if (comment.parent_id) {
					const parentComment = findParentOfComment(comments, comment.parent_id);
					if (parentComment && parentComment.num_replies > 0) {
						parentComment.num_replies--;
					}
				}
				comments = removeCommentRecursively(comments, comment.id);
				break;
			}

			default:
				console.warn('Unknown WebSocket event type (unexpected):', event);
		}
	};

	// Helper getters to find comments by state
	const getHoveredComment = (): CachedComment | undefined => {
		return flattenComments(comments).find((c) => c.isHighlightHovered || c.isBadgeHovered);
	};

	const getSelectedComment = (): CachedComment | undefined => {
		return flattenComments(comments).find((c) => c.isSelected);
	};

	const getPinnedComment = (): CachedComment | undefined => {
		return flattenComments(comments).find((c) => c.isPinned);
	};

	const getEditingComment = (): CachedComment | undefined => {
		return flattenComments(comments).find((c) => c.isEditing);
	};

	return {
		get comments() {
			return comments;
		},
		get loadedDocument() {
			return loadedDocument;
		},
		get isCommentCardActive() {
			return isCommentCardActive;
		},
		get pdfViewerRef() {
			return pdfViewerRef;
		},
		get scrollContainerRef() {
			return scrollContainerRef;
		},
		get commentSidebarRef() {
			return commentSidebarRef;
		},
		// Filter state getters
		get authorFilterStates() {
			return authorFilterStates;
		},
		/** Return a set of user IDs that are currently included */
		get authorFilterIds() {
			return new Set<number>(
				[...authorFilterStates.entries()].filter(([, v]) => v === 'include').map(([k]) => k)
			);
		},
		get hasActiveFilter() {
			return authorFilterStates.size > 0;
		},
		get showOtherCursors() {
			return showOtherCursors;
		},
		// Helper getters
		get hoveredComment() {
			return getHoveredComment();
		},
		get selectedComment() {
			return getSelectedComment();
		},
		get pinnedComment() {
			return getPinnedComment();
		},
		get editingComment() {
			return getEditingComment();
		},
		get replyingToCommentId() {
			return replyingToCommentId;
		},
		// Returns true if any input is active (editing or replying)
		get hasActiveInput() {
			return getEditingComment() !== undefined || replyingToCommentId !== null;
		},
		// Methods
		setDocument,
		setCommentCardActive,
		setPdfViewerRef,
		setScrollContainerRef,
		setCommentSidebarRef,
		setRootComments,
		// New flag setters
		setHighlightHovered,
		setBadgeHovered,
		setSelected,
		setPinned,
		setEditing,
		setReplyingTo,
		clearAllInteractionState,
		toggleRepliesCollapsed,
		// Filter methods
		toggleAuthorFilter,
		clearAuthorFilter,
		// Cursor visibility
		setShowOtherCursors,
		// View mode refresh deferral
		setPendingViewModeRefresh,
		// CRUD operations
		updateComment,
		create: createComment,
		deleteComment,
		loadReplies,
		handleWebSocketEvent
	};
};

export const documentStore = createDocumentStore();
