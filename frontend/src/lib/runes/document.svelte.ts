import { api } from '$api/client';
import type { CommentCreate, CommentEvent, CommentRead, CommentUpdate, DocumentRead } from '$api/types';
import { notification } from '$lib/stores/notificationStore';
import type { Annotation } from '$types/pdf';

export interface CachedComment extends CommentRead {
	replies?: CachedComment[];
	// States
	isActive?: boolean; // Is this comment currently active/selected/hovered
}
const toCachedComment = (comment: CommentRead): CachedComment => ({
	...comment,
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

const removeCommentRecursively = (fromComments: CachedComment[], commentId: number): CachedComment[] => {
	return fromComments
		.filter((c) => c.id !== commentId)
		.map((c) => ({
			...c,
			replies: c.replies ? removeCommentRecursively(c.replies, commentId) : []
		}));
};

const createDocumentStore = () => {
	let comments: CachedComment[] = $state<CachedComment[]>([]);
    const loadedDocument: DocumentRead | undefined = $state<DocumentRead | undefined>(undefined);
	const pdfViewerRef: HTMLElement | null = $state<HTMLElement | null>(null);
	const scrollContainerRef: HTMLElement | null = $state<HTMLElement | null>(null);
	const commentSidebarRef: HTMLDivElement | null = $state<HTMLDivElement | null>(null);

	// Resets the store and loads root comments for a document
	const setRootComments = async (rootComments: CommentRead[]): Promise<void> => {
		comments = rootComments.map(toCachedComment);
	};

	// Sets a comment as active
	const setActive = (commentId: number) => {
		comments = comments.map((c) => (c.id === commentId ? { ...c, isActive: true } : { ...c }));
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
        annotation: Annotation;
        parentId?: number;
    }) => {
        if (!loadedDocument) return;
		const result = await api.post<CommentRead>('/comments', {
            annotation: options.annotation ? options.annotation as unknown as Record<string, unknown> : undefined, // TODO add validation
            document_id: loadedDocument.id,
            visibility: loadedDocument.view_mode
        } satisfies CommentCreate);
		if (!result.success) {
			notification(result.error);
			return;
		}
		if (options.parentId) {
			const parentComment = findComment(comments, options.parentId);
			if (parentComment) {
				parentComment.replies = parentComment.replies || [];
				parentComment.replies.push(toCachedComment(result.data));
			}
		}
		comments = [...comments]; // trigger reactivity
	};

	const deleteComment = async (commentId: number) => {
		const result = await api.delete(`/comments/${commentId}`);
		if (!result.success) {
			notification(result.error);
			return;
		}

		comments = removeCommentRecursively(comments, commentId);
	};

	const handleWebSocketEvent = (event: CommentEvent): void => {
		if (!event.payload) {
			console.warn('Received WebSocket event with no payload', event);
			return;
		}

		const comment = event.payload;

		switch (event.type) {
			case 'create':
				if (comment.parent_id) {
					const parentComment = findComment(comments, comment.parent_id);
					if (parentComment) {
						parentComment.replies = parentComment.replies || [];
						parentComment.replies.push(toCachedComment(comment));
					}
					comments = [...comments]; // trigger reactivity
				} else {
					comments = [...comments, toCachedComment(comment)];
				}
				break;

			case 'update': {
				const targetComment = findComment(comments, comment.id);
				if (targetComment) {
					Object.assign(targetComment, comment);
					comments = [...comments]; // trigger reactivity
				}
				break;
			}

			case 'delete': {
				comments = removeCommentRecursively(comments, comment.id);
				break;
			}

			default:
				console.warn('Unknown WebSocket event type:', event.type);
		}
	};


	return {
        comments,
		setActive,
		setRootComments,
		updateComment: updateComment,
		create: createComment,
		deleteComment,
		pdfViewerRef,
		scrollContainerRef,
		commentSidebarRef,
        handleWebSocketEvent
	};
};

export const documentStore = createDocumentStore();
