import { api } from '$api/client';
import {
	type UserRead,
	type CommentCreate,
	type CommentEvent,
	type CommentRead,
	type DocumentRead,
	type ViewMode
} from '$api/types';
import type { Paginated } from '$api/pagination';
import { notification } from '$lib/stores/notificationStore';
import { annotationSchema, type Annotation } from '$types/pdf';
import { SvelteMap } from 'svelte/reactivity';
import { invalidateAll } from '$app/navigation';

export interface FilterState<T = 'author' | 'tag'> {
	type: T;
	value?: 'include' | 'exclude';
	id: number;
	data: T extends 'author' ? { username: string } : { label: string; color: string };
}
export type TypedComment = Omit<CommentRead, 'annotation'> & { annotation: Annotation | null };

export interface CommentState {
	id: number;
	replies: number[];
	source: 'api' | 'client';
	// Interaction state flags
	isCommentHovered?: boolean; // Mouse over the comment
	isHighlightHovered?: boolean; // Mouse over the PDF highlight
	isPinned?: boolean; // Clicked to stay open
	isEditing?: boolean; // In edit mode
	editInputContent: string; // Current content in edit input
	replyInputContent: string; // Current content in reply input
	// UI state
	repliesExpanded?: boolean; // Replies section is collapsed
	isReplying?: boolean; // Reply input box is shown
	// Element Refs
	highlightElements?: HTMLElement[]; // Associated highlight elements in the PDF
}

const createDocumentStore = () => {
	const _comments = new SvelteMap<number, TypedComment>();
	const commentStates: SvelteMap<number, CommentState> = new SvelteMap<number, CommentState>();
	let filterStates = $state<FilterState[]>([]);
	let showCursors: boolean = $state<boolean>(true);
	let loadedDocument: DocumentRead | undefined = $state<DocumentRead | undefined>(undefined);
	let documentScale: number = $state<number>(1);
	let numPages: number = $state<number>(0);
	let pdfViewerRef: HTMLElement | null = $state<HTMLElement | null>(null);
	let scrollContainerRef: HTMLElement | null = $state<HTMLElement | null>(null);
	let commentSidebarRef: HTMLDivElement | null = $state<HTMLDivElement | null>(null);

	// Resets the store and loads root comments for a document
	const setTopLevelComments = (comments: CommentRead[]) => {
		// Add/update comments
		comments.forEach((c) => {
			const annotationParsed = annotationSchema.safeParse(c.annotation);
			const cachedComment: TypedComment = {
				...c,
				annotation: annotationParsed.success ? annotationParsed.data : null
			};
			_comments.set(cachedComment.id, cachedComment);

			// Ensure commentState exists for this comment
			if (!commentStates.has(cachedComment.id)) {
				const newState = $state<CommentState>({
					id: cachedComment.id,
					replies: [],
					editInputContent: cachedComment.content ?? '',
					replyInputContent: '',
					source: 'api'
				});
				commentStates.set(cachedComment.id, newState);
			}
		});

		// Recursively remove replies as well
		const removeComment = (commentId: number) => {
			console.log(`Removing stale comment ${commentId}`);
			const commentState = commentStates.get(commentId);
			if (commentState?.replies?.length) {
				commentState.replies.forEach((replyId) => {
					removeComment(replyId);
				});
			}
			if (commentState) {
				// Reset hover state, preserve everything else for when its available again
				const state = commentStates.get(commentId);
				if (state) {
					state.isHighlightHovered = false;
					state.isCommentHovered = false;
					// ! We must reset replies here because replies are deleted when setting to restricted so they need to
					// ! be loaded back in and therefore they cant be expanded by default but we are still preserving most states like edit content etc
					state.repliesExpanded = false;
					state.replies = [];
				}
			}
			_comments.delete(commentId);
		};

		// Remove top level comments and their replies from the local store that are not present in the new set
		const commentKeys = new Set(comments.map(({ id }) => id));
		[...topLevelComments].forEach(({ id }) => {
			if (!commentKeys.has(id)) {
				removeComment(id);
			}
		});
	};

	const topLevelComments = $derived.by(() => {
		return Array.from(_comments.values()).filter(
			(c): c is TypedComment & { annotation: Annotation } => !!c.annotation
		);
	});

	const filteredTopLevelComments = $derived.by(() => {
		// Build an array of comment values from the internal SvelteMap for array filtering
		const allComments = [...topLevelComments.values()];
		let filteredArray = allComments;

		// Build arrays of include/exclude filter states.
		const includedFilters: FilterState[] = filterStates.filter(
			(state) => state.value === 'include'
		);
		const excludedFilters: FilterState[] = filterStates.filter(
			(state) => state.value === 'exclude'
		);

		const includedAuthorIds: number[] = includedFilters
			.filter((f) => f.type === 'author')
			.map((f) => f.id);
		const includedTagIds: number[] = includedFilters
			.filter((f) => f.type === 'tag')
			.map((f) => f.id);

		const excludedAuthorIds: number[] = excludedFilters
			.filter((f) => f.type === 'author')
			.map((f) => f.id);
		const excludedTagIds: number[] = excludedFilters
			.filter((f) => f.type === 'tag')
			.map((f) => f.id);

		// Apply include filters: if any include filters exist, narrow to comments matching included authors/tags.
		if (includedFilters.length > 0) {
			if (includedAuthorIds.length > 0) {
				filteredArray = filteredArray.filter(
					(comment) => !!comment.user?.id && includedAuthorIds.includes(comment.user.id)
				);
			}
			if (includedTagIds.length > 0) {
				filteredArray = filteredArray.filter(
					(comment) => !!comment.tags && comment.tags.some((t) => includedTagIds.includes(t.id))
				);
			}
		}

		if (excludedFilters.length > 0) {
			// Apply exclude filters when no include filters present.
			if (excludedAuthorIds.length > 0) {
				filteredArray = filteredArray.filter(
					(comment) => !(comment.user?.id && excludedAuthorIds.includes(comment.user.id))
				);
			}
			if (excludedTagIds.length > 0) {
				filteredArray = filteredArray.filter(
					(comment) => !(comment.tags && comment.tags.some((t) => excludedTagIds.includes(t.id)))
				);
			}
		}

		// if a comment is excluded from view then it needs to have its hover state reset, everything else can be preserved for when it shows again
		const hiddenCommentIds = allComments.filter((c) => !filteredArray.includes(c)).map((c) => c.id);
		for (const commentId of hiddenCommentIds) {
			const state = commentStates.get(commentId);
			if (!state) continue;
			state.isHighlightHovered = false;
			state.isCommentHovered = false;
		}

		return filteredArray;
	});

	const topLevelAuthors = $derived.by(() => {
		const authors: UserRead[] = [];
		for (const comment of topLevelComments.values()) {
			if (comment.user && !authors.find((a) => a.id === comment.user!.id)) {
				authors.push(comment.user);
			}
		}
		return authors;
	});

	// Methods to update local comment data without API calls (on events)
	const commentsLocal = $derived({
		update: (existing: TypedComment) => {
			/** Update an existing comment in the local map. */
			const existingComment: TypedComment | undefined = _comments.get(existing.id);
			if (!existingComment) return;
			const updatedComment: TypedComment = {
				...existingComment,
				...existing,
				visibility: existing.visibility ?? existingComment.visibility
			};
			_comments.set(existing.id, updatedComment);
		},
		create: (
			data: TypedComment,
			skip_num_replies_increment?: boolean,
			source: 'api' | 'client' = 'client'
		) => {
			const existingComment: TypedComment | undefined = _comments.get(data.id);
			if (existingComment) {
				// Comment already exists, perform an update instead
				commentsLocal.update(data);
				return;
			}
			// Increment num_replies in parent comment
			const parentComment: TypedComment | undefined = data.parent_id
				? _comments.get(data.parent_id)
				: undefined;
			if (parentComment && !skip_num_replies_increment) {
				// ! Set on map directly here because comments are not deeply reactive, only states
				_comments.set(parentComment.id, {
					...parentComment,
					num_replies: parentComment.num_replies + 1
				});
			}

			// Add new comment to parent replies if applicable
			const parentState = commentStates.get(data?.parent_id || -1);
			if (parentState) {
				parentState.replies = [...parentState.replies, data.id]; // TODO the new comment needs to be sorted by created_at
				parentState.repliesExpanded = true;
			}

			// Add new comment to local comments map and add a state entry
			_comments.set(data.id, data);

			const stateExists = commentStates.has(data.id);
			if (stateExists) {
				return;
			}

			const newState = $state<CommentState>({
				id: data.id,
				replies: [],
				editInputContent: data.content ?? '',
				replyInputContent: '',
				source: source
			});
			commentStates.set(data.id, newState);
		},
		delete: (commentId: number, deleteState = false) => {
			/** Delete a comment and its replies from the local store. */
			// Delete all replies and their states from the local map
			const commentState = commentStates.get(commentId);
			const commentToDelete: TypedComment | undefined = _comments.get(commentId);
			/**
			 * Recursively delete replies for a given comment id.
			 */
			const deleteRepliesRecursively = (rootId: number): void => {
				// Get the state for the current comment id
				const stateForRoot: CommentState | undefined = commentStates.get(rootId);
				// Copy reply ids to avoid mutation during iteration
				const replyIds: number[] = [...(stateForRoot?.replies ?? [])];

				// Recursively delete each reply and its nested replies
				for (const replyId of replyIds) {
					deleteRepliesRecursively(replyId);
					_comments.delete(replyId);
					commentStates.delete(replyId);
				}
			};

			// Start recursive deletion from immediate replies of the comment to delete
			if (commentState?.replies?.length) {
				const immediateReplyIds: number[] = [...commentState.replies];
				for (const replyId of immediateReplyIds) {
					deleteRepliesRecursively(replyId);
					_comments.delete(replyId);
					commentStates.delete(replyId);
				}
			}

			// Remove reply reference in parent comment state
			const parentCommentState = commentStates.get(commentToDelete?.parent_id || -1);
			const parentComment: TypedComment | undefined = commentToDelete?.parent_id
				? _comments.get(commentToDelete.parent_id)
				: undefined;
			if (parentCommentState && !!parentCommentState.replies?.length) {
				parentCommentState.replies = parentCommentState.replies.filter((id) => id !== commentId);
			}

			// Decrement num_replies in parent comment state
			if (parentComment) parentComment.num_replies--;

			// Remove own comment and reset hover state, preserve rest of the state
			if (commentState) {
				commentState.isHighlightHovered = false;
				commentState.isCommentHovered = false;
			}
			_comments.delete(commentId);
			if (deleteState) {
				commentStates.delete(commentId);
			}
		}
	});

	const comments = $derived({
		update: async (comment: TypedComment) => {
			const result = await api.update(`/comments/${comment.id}`, comment);
			if (!result.success) {
				notification(result.error);
				return;
			}
			commentsLocal.update(comment);
		},
		create: async (
			data: Omit<CommentCreate, 'document_id' | 'annotation'> & { annotation: Annotation | null }
		): Promise<number | undefined> => {
			if (!loadedDocument) return;
			const result = await api.post<CommentRead>('/comments', {
				...data,
				document_id: loadedDocument?.id
			});
			if (!result.success) {
				notification(result.error);
				return;
			}
			const annotationParsed = annotationSchema.safeParse(result.data!.annotation);
			const cachedComment: TypedComment = {
				...result.data!,
				annotation: annotationParsed.success ? annotationParsed.data : null
			};

			commentsLocal.create(cachedComment);
			return cachedComment.id;
		},
		delete: async (commentId: number) => {
			const result = await api.delete(`/comments/${commentId}`);
			if (!result.success) {
				notification(result.error);
				return;
			}

			commentsLocal.delete(commentId, true);
		},
		addTag: async (commentId: number, tagId: number) => {
			const result = await api.post(`/comments/${commentId}/tags/${tagId}`, {});
			if (!result.success) {
				notification(result.error);
				return;
			}

			// Optimistically update the comment with the new tag
			const comment = _comments.get(commentId);
			const tag = loadedDocument?.tags.find((t) => t.id === tagId);
			if (comment && tag && !comment.tags.some((t) => t.id === tagId)) {
				comment.tags = [...comment.tags, tag];
				_comments.set(commentId, comment);
			}
		},
		removeTag: async (commentId: number, tagId: number) => {
			const result = await api.delete(`/comments/${commentId}/tags/${tagId}`);
			if (!result.success) {
				notification(result.error);
				return;
			}

			// Optimistically update the comment by removing the tag
			const comment = _comments.get(commentId);
			if (comment) {
				comment.tags = comment.tags.filter((t) => t.id !== tagId);
				_comments.set(commentId, comment);
			}
		},
		loadMoreReplies: async (commentId: number) => {
			const limit = 20;
			// Offset by the amount of comments that were already received from the api
			const offset =
				commentStates
					.get(commentId)
					?.replies.map((id) => commentStates.get(id))
					.reduce((acc, state) => acc + (state?.source === 'api' ? 1 : 0), 0) || 0;
			const targetComment: TypedComment | undefined = _comments.get(commentId);
			const targetState: CommentState | undefined = commentStates.get(commentId);

			// Dont load more if all replies are already loaded
			if (!targetComment || (targetComment.num_replies || 0) <= offset) return;
			if (!targetComment || targetComment.num_replies <= offset) return;
			if (!targetState) return;

			const result = await api.get<Paginated<CommentRead>>(
				`/comments?limit=${limit}&offset=${offset}`,
				{
					filters: [
						{ field: 'parent_id', operator: '==', value: commentId.toString() },
						// Exclude comments that were created locally
						{
							field: 'id',
							operator: 'notin',
							value: `[${targetState.replies.filter((id) => commentStates.get(id)?.source === 'client').join(',')}]`
						}
					]
				}
			);
			if (!result.success) {
				notification(result.error);
				return;
			}

			const data = result.data.data.map((c) => {
				const annotationParsed = annotationSchema.safeParse(c.annotation);
				return {
					...c,
					annotation: annotationParsed.success ? annotationParsed.data : null
				} as TypedComment;
			});

			// Add loaded replies to local comments array
			data.forEach((c) => {
				commentsLocal.create(c, true, 'api');
			});
		},
		getState: (commentId: number): CommentState | undefined => {
			return commentStates.get(commentId);
		},
		getComment: (commentId: number): TypedComment | undefined => {
			return _comments.get(commentId);
		},
		topLevelAuthors: topLevelAuthors,
		// Comment subsets
		all: new SvelteMap(_comments),
		pinned: new SvelteMap(
			Array.from(commentStates.entries()).filter(([, state]) => state.isPinned)
		),
		topLevelComments: filteredTopLevelComments,
		editing: new SvelteMap(
			Array.from(commentStates.entries()).filter(([, state]) => state.isEditing)
		),
		replying: new SvelteMap(
			Array.from(commentStates.entries()).filter(([, state]) => state.isReplying)
		),
		highlightHovered: new SvelteMap(
			Array.from(commentStates.entries()).filter(([, state]) => state.isHighlightHovered)
		),
		commentHovered: new SvelteMap(
			Array.from(commentStates.entries()).filter(([, state]) => state.isCommentHovered)
		)
	});

	/**
	 * Simple getter for filters with overloaded return types.
	 */
	function getFilters(type: FilterState['type']): FilterState[];
	function getFilters(type: FilterState['type'], id: number): FilterState | undefined;
	function getFilters(
		type: FilterState['type'],
		id?: number
	): FilterState | FilterState[] | undefined {
		// Return a single filter when id is provided
		if (id !== undefined) {
			return filterStates.find((state) => state.type === type && state.id === id);
		}
		// Return all filters of the requested type when id is not provided
		return filterStates.filter((state) => state.type === type);
	}

	function clearFilter(type?: FilterState['type']): void;
	function clearFilter(type: FilterState['type'], id: number): void;
	function clearFilter(type?: FilterState['type'], id?: number): void {
		if (id !== undefined) {
			// Remove specific filter
			filterStates = filterStates.filter((state) => !(state.type === type && state.id === id));
		} else if (type !== undefined) {
			// Remove all filters of the given type
			filterStates = filterStates.filter((state) => state.type !== type);
		} else {
			// Remove all filters
			filterStates = [];
		}
	}

	const filters = $derived({
		toggle: (filter: Omit<FilterState, 'value'>): void => {
			const currentIndex = filterStates.findIndex(
				(s) => s.id === filter.id && s.type === filter.type
			);
			const current = filterStates[currentIndex];
			let value: FilterState['value'] | undefined = current?.value;
			if (!value) {
				value = 'include';
			} else if (value === 'include') {
				value = 'exclude';
			} else {
				value = undefined;
			}

			if (value === undefined) {
				// Remove filter
				filterStates.splice(
					filterStates.findIndex((s) => s.id === filter.id && s.type === filter.type),
					1
				);
			} else if (current) {
				// Add or update filter
				filterStates.splice(currentIndex, 1, { ...filter, value });
			} else {
				filterStates.push({ ...filter, value });
			}
		},
		clear: clearFilter,
		get: getFilters,
		get all() {
			return filterStates;
		}
	});

	const clearHighlightReferences = (): void => {
		/** Clear all highlight element references from comment states. */
		for (const state of commentStates.values()) {
			state.highlightElements = undefined;
		}
	};

	// Store timeouts for debounced hover state updates
	const hoverTimeouts = new SvelteMap<number, { highlight?: number; comment?: number }>();

	/**
	 * Set highlight hover state with debouncing on the "false" transition.
	 * - When setting to true: immediately set and clear any pending debounced false assignment
	 * - When setting to false: debounce the assignment by 300ms
	 */
	const setHighlightHoveredDebounced = (commentId: number, hovered: boolean): void => {
		const state = commentStates.get(commentId);
		if (!state) return;

		const timeouts = hoverTimeouts.get(commentId) || {};

		if (hovered) {
			// Clear any pending "unhover" timeout
			if (timeouts.highlight) {
				clearTimeout(timeouts.highlight);
				hoverTimeouts.set(commentId, { ...timeouts, highlight: undefined });
			}
			// Immediately set to true
			state.isHighlightHovered = true;
		} else {
			// Delay setting to false by 300ms
			const timeoutId = setTimeout(() => {
				state.isHighlightHovered = false;
				const currentTimeouts = hoverTimeouts.get(commentId);
				if (currentTimeouts) {
					hoverTimeouts.set(commentId, { ...currentTimeouts, highlight: undefined });
				}
			}, 50) as unknown as number;

			hoverTimeouts.set(commentId, { ...timeouts, highlight: timeoutId });
		}
	};

	/**
	 * Set comment hover state with debouncing on the "false" transition.
	 * - When setting to true: immediately set and clear any pending debounced false assignment
	 * - When setting to false: debounce the assignment by 100ms
	 */
	const setCommentHoveredDebounced = (commentId: number, hovered: boolean): void => {
		const state = commentStates.get(commentId);
		if (!state) return;

		const timeouts = hoverTimeouts.get(commentId) || {};

		if (hovered) {
			// Clear any pending "unhover" timeout
			if (timeouts.comment) {
				clearTimeout(timeouts.comment);
				hoverTimeouts.set(commentId, { ...timeouts, comment: undefined });
			}
			// Immediately set to true
			state.isCommentHovered = true;
		} else {
			// Delay setting to false by 100ms
			const timeoutId = setTimeout(() => {
				state.isCommentHovered = false;
				const currentTimeouts = hoverTimeouts.get(commentId);
				if (currentTimeouts) {
					hoverTimeouts.set(commentId, { ...currentTimeouts, comment: undefined });
				}
			}, 50) as unknown as number;

			hoverTimeouts.set(commentId, { ...timeouts, comment: timeoutId });
		}
	};

	const handleWebSocketEvent = (
		event:
			| CommentEvent
			| { type: 'view_mode_changed'; payload: { document_id?: string; view_mode?: ViewMode } }
	): void => {
		if (!event.payload) {
			console.warn('Received WebSocket event with no payload', event);
			return;
		}

		switch (event.type) {
			case 'create': {
				const payload = event.payload as CommentRead;
				const annotationParsed = annotationSchema.safeParse(payload.annotation);
				const cachedComment: TypedComment = {
					...payload,
					annotation: annotationParsed.success ? annotationParsed.data : null
				};
				commentsLocal.create(cachedComment);
				break;
			}
			case 'update': {
				const payload = event.payload as CommentRead;
				const annotationParsed = annotationSchema.safeParse(payload.annotation);
				const cachedComment: TypedComment = {
					...payload,
					annotation: annotationParsed.success ? annotationParsed.data : null
				};
				commentsLocal.update(cachedComment);
				break;
			}
			case 'delete':
				commentsLocal.delete((event.payload as CommentRead).id);
				break;
			case 'view_mode_changed': {
				invalidateAll();
				break;
			}
			default:
				console.warn('Unknown WebSocket event type (unexpected):', event);
		}
	};

	return {
		get comments() {
			return comments;
		},
		get filters() {
			return filters;
		},
		get loadedDocument() {
			return loadedDocument;
		},
		set loadedDocument(value) {
			loadedDocument = value;
		},
		get documentScale() {
			return documentScale;
		},
		set documentScale(value) {
			documentScale = value;
		},
		get numPages() {
			return numPages;
		},
		set numPages(value) {
			numPages = value;
		},
		get scrollContainerRef() {
			return scrollContainerRef;
		},
		set scrollContainerRef(value) {
			scrollContainerRef = value;
		},
		get pdfViewerRef() {
			return pdfViewerRef;
		},
		set pdfViewerRef(value) {
			pdfViewerRef = value;
		},
		get commentSidebarRef() {
			return commentSidebarRef;
		},
		set commentSidebarRef(value) {
			commentSidebarRef = value;
		},
		get showCursors() {
			return showCursors;
		},
		set showCursors(value) {
			showCursors = value;
		},
		handleWebSocketEvent,
		setTopLevelComments,
		clearHighlightReferences,
		setHighlightHoveredDebounced,
		setCommentHoveredDebounced
	};
};

export const documentStore = createDocumentStore();
