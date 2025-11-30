import { api } from '$api/client';
import type { CommentCreate, CommentEvent, CommentRead, DocumentRead, ViewMode } from '$api/types';
import type { Paginated } from '$api/pagination';
import { notification } from '$lib/stores/notificationStore';
import { annotationSchema, type Annotation } from '$types/pdf';
import { SvelteMap } from 'svelte/reactivity';

type AuthorFilterState = 'include' | 'exclude';
export type TypedComment = Omit<CommentRead, 'annotation'> & { annotation: Annotation | null };

export interface CommentState {
	id: number;
	replies?: number[];
	// Interaction state flags
	isCommentHovered?: boolean; // Mouse over the comment
	isHighlightHovered?: boolean; // Mouse over the PDF highlight
	isPinned?: boolean; // Clicked to stay open
	isEditing?: boolean; // In edit mode
	editInputContent: string; // Current content in edit input
	replyInputContent: string; // Current content in reply input
	// UI state
	repliesExpanded?: boolean; // Replies section is collapsed
	showReplyInput?: boolean; // Reply input box is shown
	// Element Refs
	highlightElements?: HTMLElement[]; // Associated highlight elements in the PDF
}

const createDocumentStore = () => {
	const _comments = new SvelteMap<number, TypedComment>();

	// Resets the store and loads root comments for a document
	const setRootComments = (rootComments: CommentRead[]) => {
		// Add/update comments
		rootComments.forEach((c) => {
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
					replyInputContent: ''
				});
				commentStates.set(cachedComment.id, newState);				
			}
		});

		// Remove states that no longer exist
		const commentKeys = new Set(_comments.keys());
		Array.from(commentStates.keys()).forEach((commentId) => {
			if (!commentKeys.has(commentId)) {
				commentStates.delete(commentId);
			}
		});
	};

	// TODO maybe the delay when editing is openened can be removed entirely with the new state splitting
	// eslint-disable-next-line @typescript-eslint/no-unused-vars
	const setViewMode = (viewMode: ViewMode) => {
		// ? Since the best approach for view_mode changes is to refetch data from the backend on change,
		// ? we dont really care about the view mode as it will be updates anyway once the refresh happens.
		if (!loadedDocument) return;
		if (comments.editing.size) {
			refreshFlag = true; // Delay until active comment edit is done
		}
	};

	const commentStates: SvelteMap<number, CommentState> = new SvelteMap<number, CommentState>();
	const authorFilterStates = new SvelteMap<number, AuthorFilterState>();
	let showCursors: boolean = $state<boolean>(true);
	let refreshFlag = $state<boolean>(false);
	let loadedDocument: DocumentRead | undefined = $state<DocumentRead | undefined>(undefined);
	let documentScale: number = $state<number>(1);
	let numPages: number = $state<number>(0);
	let pdfViewerRef: HTMLElement | null = $state<HTMLElement | null>(null);
	let scrollContainerRef: HTMLElement | null = $state<HTMLElement | null>(null);
	let commentSidebarRef: HTMLDivElement | null = $state<HTMLDivElement | null>(null);

	const filteredComments = $derived.by((): SvelteMap<number, TypedComment> => {
		void _comments; // Ensure _comments is tracked as a dependency

		// Build an array of comment values from the internal SvelteMap for array filtering
		const allComments: TypedComment[] = [..._comments.values()] as TypedComment[];
		let filteredArray: TypedComment[] = allComments;

		// Filter by author filter states (include/exclude/none)
		const included = new Set<number>(
			[...authorFilterStates.entries()].filter(([, v]) => v === 'include').map(([k]) => k)
		);
		const excluded = new Set<number>(
			[...authorFilterStates.entries()].filter(([, v]) => v === 'exclude').map(([k]) => k)
		);

		// If there are include filters, show only those authors. Otherwise, if exclude filters exist, hide those authors.
		if (included.size > 0) {
			filteredArray = filteredArray.filter(
				(c: TypedComment) => !!c.user?.id && included.has(c.user.id)
			);
		} else if (excluded.size > 0) {
			filteredArray = filteredArray.filter(
				(c: TypedComment) => !(c.user?.id && excluded.has(c.user.id))
			);
		}

		// Return a SvelteMap constructed from the filtered array
		const filteredMap = new SvelteMap<number, TypedComment>(filteredArray.map((c) => [c.id, c]));
		return filteredMap;
	});

	const commentsWithAnnotation = $derived.by((): (TypedComment & { annotation: Annotation })[] => {
		return Array.from(filteredComments.values()).filter(
			(c): c is TypedComment & { annotation: Annotation } => !!c.annotation
		);
	});

	// Methods to update local comment data without API calls (on events)
	const commentsLocal = $derived.by(() => ({
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
		create: (data: TypedComment) => {
			/** Add new comment to the local store. */
			// Add new comment to parent replies if applicable
			const parentState = commentStates.get(data?.parent_id || -1);
			if (parentState && parentState.replies) {
				commentStates.set(data?.parent_id || -1, {
					...parentState,
					replies: [...parentState.replies, data.id]
				});
			}

			// Increment num_replies in parent comment
			const parentComment: TypedComment | undefined = data.parent_id
				? _comments.get(data.parent_id)
				: undefined;
			if (parentComment) {
				parentComment.num_replies = (parentComment.num_replies || 0) + 1;
			}

			// Add new comment to local comments map and add a state entry
			_comments.set(data.id, data);
			const newState = $state<CommentState>({
				id: data.id,
				replies: [],
				editInputContent: data.content ?? '',
				replyInputContent: ''
			});
			commentStates.set(data.id, newState);
		},
		delete: (commentId: number) => {
			/** Delete a comment and its replies from the local store. */
			// Delete all replies and their states from the local map
			const commentState = commentStates.get(commentId);
			const commentToDelete: TypedComment | undefined = _comments.get(commentId);
			commentState?.replies?.forEach((replyId) => {
				commentStates.delete(replyId);
				_comments.delete(replyId);
			});

			// Remove reply reference in parent comment state
			const parentCommentState = commentStates.get(commentToDelete?.parent_id || -1);
			const parentComment: TypedComment | undefined = commentToDelete?.parent_id
				? _comments.get(commentToDelete.parent_id)
				: undefined;
			if (parentCommentState && !!parentCommentState.replies?.length) {
				commentStates.set(commentToDelete?.parent_id || -1, {
					...parentCommentState,
					replies: parentCommentState.replies?.filter((id) => id !== commentId)
				});
			}

			// Decrement num_replies in parent comment state
			if (parentComment) {
				parentComment.num_replies = (parentComment.num_replies || 1) - 1;
			}

			// Remove own comment state and comment
			commentStates.delete(commentId);
			_comments.delete(commentId);
		}
	}));

	const comments = $derived.by(() => ({
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

			commentsLocal.delete(commentId);
		},
		loadMoreReplies: async (commentId: number) => {
			const limit = 20;
			const offset = commentStates.get(commentId)?.replies?.length || 0;
			const targetComment: TypedComment | undefined = _comments.get(commentId);

			// Dont load more if all replies are already loaded
			if (!targetComment || (targetComment.num_replies || 0) <= offset) return;
			if (!targetComment || targetComment.num_replies <= offset) return;

			const result = await api.get<Paginated<CommentRead>>(
				`/comments?limit=${limit}&offset=${offset}`,
				{
					filters: [{ field: 'parent_id', operator: '==', value: commentId.toString() }]
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
				commentsLocal.create(c);
			});
		},
		getState: (commentId: number): CommentState | undefined => {
			return commentStates.get(commentId);
		},
		getComment: (commentId: number): TypedComment | undefined => {
			return _comments.get(commentId);
		},
		/**
		 * Reset interaction flags for all existing comment states.
		 */
		resetStates: (): void => {
			/** Reset interaction-related boolean flags for all comment states. */
			for (const state of commentStates.values()) {
				state.isEditing = false;
				state.isPinned = false;
				state.isHighlightHovered = false;
				state.isCommentHovered = false;
			}
		},
		// Comment subsets
		all: new SvelteMap(_comments),
		pinned: new SvelteMap(commentStates.entries().filter(([, state]) => state.isPinned)),
		withAnnotations: commentsWithAnnotation,
		editing: new SvelteMap(commentStates.entries().filter(([, state]) => state.isEditing)),
		highlightHovered: new SvelteMap(
			commentStates.entries().filter(([, state]) => state.isHighlightHovered)
		),
		commentHovered: new SvelteMap(
			commentStates.entries().filter(([, state]) => state.isCommentHovered)
		)
	}));

	const filters = $derived({
		toggleAuthorFilter: (userId: number): void => {
			let state = authorFilterStates.get(userId);
			if (!state) {
				state = 'include';
			} else if (state === 'include') {
				state = 'exclude';
			} else {
				state = undefined;
			}

			if (state) authorFilterStates.set(userId, state);
			else authorFilterStates.delete(userId);
		},
		/** Clear all author filters (reset to none) */
		clearAuthorFilter: (): void => {
			authorFilterStates.clear();
		},

		authorFilters: authorFilterStates
	});

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
				const vm = event.payload as { view_mode?: ViewMode };

				if (vm?.view_mode) {
					setViewMode(vm.view_mode);
					console.log(`[WS] Document view_mode updated to ${vm.view_mode}`);
				}
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
		get refreshFlag() {
			return refreshFlag;
		},
		set refreshFlag(value) {
			refreshFlag = value;
		},
		handleWebSocketEvent,
		setRootComments,
		setViewMode
	};
};

export const documentStore = createDocumentStore();
