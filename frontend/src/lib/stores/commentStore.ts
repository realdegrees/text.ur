import { writable } from 'svelte/store';
import { api } from '$api/client';
import type { CommentRead, CommentCreate, CommentUpdate, CommentEvent } from '$api/types';
import type { Annotation } from '$types/pdf';
import {
	computeScaledBoundingBoxes,
	computeHighlightScreenPosition,
	groupCommentsByProximity,
	resolveCollisions
} from '$lib/util/positionUtils';
import type { Paginated } from '$api/pagination';
import { notification } from './notificationStore';

/**
 * Enhanced LocalComment with all computed UI metadata
 */
export interface LocalComment extends CommentRead {
	// Page metadata for the page where the annotation lives
	pageData: { pageNumber: number; width: number; height: number } | null;

	// Scaled bounding boxes (normalized 0-1 → pixel coordinates at current scale)
	scaledBoundingBoxes: Array<{ x: number; y: number; width: number; height: number }>;

	// Screen-space positions relative to sidebar coordinate system
	screenPosition: {
		highlight: {
			leftX: number;
			rightX: number;
			top: number;
			bottom: number;
		};
		comment: {
			idealTop: number;    // Where comment wants to be (aligned with highlight)
			actualTop: number;   // Where comment is after collision avoidance
		};
	} | null;

	// Grouping metadata
	groupId: string | null;         // ID of group this comment belongs to
	groupIndex: number;             // Position within group (0-based)
	isGroupActive: boolean;         // Is this comment's group expanded/hovered

	// DOM element references (registered by components)
	pageElement: HTMLElement | null;
	highlightElement: HTMLElement | null;
}

/**
 * CommentGroup represents a cluster of comments that are positioned close together
 */
export interface CommentGroup {
	id: string;
	commentIds: number[];
	activeCommentId: number;  // Which comment's highlight to show connection line to
	idealTop: number;         // Average ideal position of all comments in group
	actualTop: number;        // Final position after collision detection
	isExpanded: boolean;      // Is the group showing full comment cards
	isHovered: boolean;       // Is the group currently hovered
	element?: HTMLElement | null;
}

/**
 * Layout computation options
 */
interface LayoutOptions {
	scale: number;
	sidebarRef: HTMLElement | null;
	hoveredCommentId: number | null;
	focusedCommentId: number | null;
	isDragging: boolean;
}

/**
 * Centralized store for managing comment tree state and API operations.
 * Handles all position computation and grouping logic.
 */
class CommentStore {
	// Core data
	private store = writable<LocalComment[]>([]);
	private documentId: string | null = null;
	private currentUserId: number | null = null;
	private repliesCache: Map<number, CommentRead[]> = new Map();

	// DOM references (registered by components)
	private pageElementMap: Map<number, HTMLElement | null> = new Map();
	private pdfContainerRef: HTMLElement | null = null;
	private scrollContainerRef: HTMLElement | null = null;
	private pageDataArrayValue: Array<{ pageNumber: number; width: number; height: number }> | null = null;

	private highlightElementMap: WeakMap<HTMLElement, number> = new WeakMap();
	private cacheVersion = writable(0);
	private computedGroups = writable<CommentGroup[]>([]);
	private currentLayoutOptions: LayoutOptions | null = null;

	subscribe = this.store.subscribe;
	subscribeToGroups = this.computedGroups.subscribe;
	subscribeToCacheVersion = this.cacheVersion.subscribe;

	async initialize(documentId: string, currentUserId: number | null = null): Promise<void> {
		this.documentId = documentId;
		this.currentUserId = currentUserId;
		await this.loadRootComments();
	}

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

		// Convert to LocalComment with initial null values
		this.store.set(
			allComments.map((c) => this.createLocalComment(c))
		);
	}

	/**
	 * Create a LocalComment from a CommentRead with default UI metadata
	 */
	private createLocalComment(comment: CommentRead): LocalComment {
		return {
			...comment,
			pageData: null,
			scaledBoundingBoxes: [],
			screenPosition: null,
			groupId: null,
			groupIndex: 0,
			isGroupActive: false,
			pageElement: null,
			highlightElement: null
		};
	}

	/**
	 * Increment cache version to trigger reactivity
	 */
	private incrementCacheVersion(): void {
		this.cacheVersion.update((v) => v + 1);
	}

	/**
	 * CORE METHOD: Recompute all layout positions and grouping.
	 * This is called by the parent component whenever layout-affecting state changes.
	 * No batching/debouncing - runs synchronously for smooth scaling/resizing.
	 */
	recomputeLayout(options: LayoutOptions): void {
		this.currentLayoutOptions = options;
		const { scale, sidebarRef, hoveredCommentId, focusedCommentId } = options;

		// Early exit if required refs aren't available
		if (!sidebarRef || !this.pdfContainerRef || !this.scrollContainerRef || !this.pageDataArrayValue) {
			return;
		}

		const pageDataArray = this.pageDataArrayValue;

		// Step 1: Update all comment positions
		this.store.update((comments) => {
			return comments.map((comment) => {
				const annotation = comment.annotation as unknown as Annotation;
				if (!annotation?.pageNumber) return comment;

				// Find page data
				const pageData = pageDataArray.find((p) => p.pageNumber === annotation.pageNumber);
				if (!pageData) return comment;

				// Compute scaled bounding boxes
				const scaledBoxes = computeScaledBoundingBoxes(annotation, pageData, scale);

				// Compute screen position for highlight
				const highlightScreenPos = computeHighlightScreenPosition({
					annotation,
					pageData,
					scale,
					pageElement: this.pageElementMap.get(annotation.pageNumber) ?? null,
					highlightElement: comment.highlightElement,
					pdfContainerRef: this.pdfContainerRef,
					scrollContainerRef: this.scrollContainerRef,
					sidebarRef,
					scaledBoxes
				});

				// Update comment with new data
				return {
					...comment,
					pageData,
					scaledBoundingBoxes: scaledBoxes,
					screenPosition: highlightScreenPos ? {
						highlight: highlightScreenPos,
						comment: {
							idealTop: highlightScreenPos.top,
							actualTop: highlightScreenPos.top // Will be updated after collision detection
						}
					} : null
				};
			});
		});

		// Step 2: Group comments by proximity
		let currentComments: LocalComment[] = [];
		this.store.subscribe((c) => { currentComments = c; })();

		const groups = groupCommentsByProximity(currentComments, {
			groupThreshold: 40,
			hoveredCommentId,
			focusedCommentId
		});

		// Step 3: Apply collision detection to groups
		const resolvedGroups = resolveCollisions(groups, {
			minGap: 8,
		});

		// Step 4: Update comments with final positions and group metadata
		this.store.update((comments) => {
			return comments.map((comment) => {
				// Find which group this comment belongs to
				const group = resolvedGroups.find((g) => g.commentIds.includes(comment.id));
				if (!group) return comment;

				// Update with group metadata and final position
				return {
					...comment,
					groupId: group.id,
					groupIndex: group.commentIds.indexOf(comment.id),
					isGroupActive: group.isExpanded || group.isHovered,
					screenPosition: comment.screenPosition ? {
						...comment.screenPosition,
						comment: {
							...comment.screenPosition.comment,
							actualTop: group.actualTop
						}
					} : null
				};
			});
		});

		// Step 5: Update computed groups
		this.computedGroups.set(resolvedGroups);
	}


	/**
	 * Set page data array (called by PdfViewer when pages are rendered)
	 */
	setPageDataArray(pageData: Array<{ pageNumber: number; width: number; height: number }>): void {
		if (!pageData || pageData.length === 0) return;
		this.pageDataArrayValue = pageData;
		this.incrementCacheVersion();

		// Trigger recompute if we have layout options
		if (this.currentLayoutOptions) {
			this.recomputeLayout(this.currentLayoutOptions);
		}
	}

	getPageDataArray(): Array<{ pageNumber: number; width: number; height: number }> | null {
		return this.pageDataArrayValue;
	}

	registerPageElement(pageNumber: number, element: HTMLElement | null): void {
		this.pageElementMap.set(pageNumber, element);
	}

	getPageElement(pageNumber: number): HTMLElement | null {
		return this.pageElementMap.get(pageNumber) ?? null;
	}

	registerPdfContainerRef(element: HTMLElement | null): void {
		this.pdfContainerRef = element;
	}

	getPdfContainerRef(): HTMLElement | null {
		return this.pdfContainerRef;
	}

	registerScrollContainerRef(element: HTMLElement | null): void {
		this.scrollContainerRef = element;
	}

	getScrollContainerRef(): HTMLElement | null {
		return this.scrollContainerRef;
	}

	registerAnnotationHighlightElement(commentId: number, element: HTMLElement | null): void {
		this.store.update((comments) =>
			comments.map((c) => (c.id === commentId ? { ...c, highlightElement: element } : c))
		);

		if (element) {
			this.highlightElementMap.set(element, commentId);
		} else {
			const existing = this.getLocalComment(commentId)?.highlightElement;
			if (existing) this.highlightElementMap.delete(existing);
		}
	}

	findCommentByHighlightElement(node: HTMLElement | null): number | null {
		if (!node) return null;

		let el: HTMLElement | null = node;
		while (el) {
			const id = this.highlightElementMap.get(el);
			if (id !== undefined) return id;
			el = el.parentElement;
		}
		return null;
	}

	getLocalComment(commentId: number): LocalComment | undefined {
		let result: LocalComment | undefined;
		this.store.subscribe((comments) => {
			result = comments.find((c) => c.id === commentId);
		})();
		return result;
	}

	getCachedReplies(commentId: number): CommentRead[] | undefined {
		return this.repliesCache.get(commentId);
	}

	async loadReplies(commentId: number, forceRefresh: boolean = false): Promise<CommentRead[]> {
		if (!this.documentId) return [];

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

		this.repliesCache.set(commentId, result.data.data);
		this.incrementCacheVersion();
		return result.data.data;
	}

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
			const cachedReplies = this.repliesCache.get(data.parentId) || [];
			this.repliesCache.set(data.parentId, [...cachedReplies, result.data]);
			this.incrementCacheVersion();

			this.updateCommentInTree(data.parentId, (comment) => ({
				...comment,
				num_replies: comment.num_replies + 1
			}));
		} else {
			this.store.update((comments) => [
				...comments,
				this.createLocalComment(result.data)
			]);

			// Recompute layout to position the new comment
			if (this.currentLayoutOptions) {
				this.recomputeLayout(this.currentLayoutOptions);
			}
		}

		return result.data;
	}

	async update(commentId: number, data: CommentUpdate): Promise<boolean> {
		const result = await api.update(`/comments/${commentId}`, data);

		if (!result.success) {
			notification(result.error);
			return false;
		}

		this.updateCommentInTree(commentId, (comment) => ({
			...comment,
			content: data.content ?? comment.content,
			visibility: data.visibility ?? comment.visibility,
			annotation: data.annotation ?? comment.annotation,
			updated_at: new Date().toISOString()
		}));

		return true;
	}

	async delete(commentId: number, parentId?: number): Promise<boolean> {
		const result = await api.delete(`/comments/${commentId}`);

		if (!result.success) {
			notification(result.error);
			return false;
		}

		const actualParentId = parentId ?? this.findParentId(commentId);

		if (actualParentId) {
			const cachedReplies = this.repliesCache.get(actualParentId) || [];
			this.repliesCache.set(
				actualParentId,
				cachedReplies.filter((reply) => reply.id !== commentId)
			);
			this.incrementCacheVersion();

			this.updateCommentInTree(actualParentId, (comment) => ({
				...comment,
				num_replies: Math.max(0, comment.num_replies - 1)
			}));
		} else {
			this.repliesCache.delete(commentId);
			this.incrementCacheVersion();
			this.store.update((comments) => comments.filter((comment) => comment.id !== commentId));
		}

		return true;
	}

	private updateCommentInTree(
		commentId: number,
		updater: (comment: CommentRead) => CommentRead
	): void {
		let found = false;
		this.store.update((comments) => {
			const updated = comments.map((comment) => {
				if (comment.id === commentId) {
					found = true;
					return updater(comment) as LocalComment;
				}
				return comment;
			});
			return updated;
		});

		if (!found) {
			for (const [parentId, replies] of this.repliesCache.entries()) {
				const index = replies.findIndex((reply) => reply.id === commentId);
				if (index !== -1) {
					const updatedReplies = [...replies];
					updatedReplies[index] = updater(replies[index]);
					this.repliesCache.set(parentId, updatedReplies);
					this.incrementCacheVersion();
					break;
				}
			}
		}
	}

	private findParentId(commentId: number): number | null {
		for (const [parentId, replies] of this.repliesCache.entries()) {
			if (replies.some((reply) => reply.id === commentId)) {
				return parentId;
			}
		}
		return null;
	}

	getCurrentUserId(): number | null {
		return this.currentUserId;
	}

	handleWebSocketEvent(event: CommentEvent): void {
		if (!event.payload) {
			console.warn('Received WebSocket event with no payload', event);
			return;
		}

		const comment = event.payload;

		switch (event.type) {
			case 'create':
				if (comment.parent_id) {
					const cachedReplies = this.repliesCache.get(comment.parent_id) || [];
					if (!cachedReplies.some((r) => r.id === comment.id)) {
						this.repliesCache.set(comment.parent_id, [...cachedReplies, comment]);
						this.incrementCacheVersion();

						this.updateCommentInTree(comment.parent_id, (parent) => ({
							...parent,
							num_replies: parent.num_replies + 1
						}));
					}
				} else {
					this.store.update((comments) => {
						if (comments.some((c) => c.id === comment.id)) {
							return comments;
						}
						return [...comments, this.createLocalComment(comment)];
					});

					// Recompute layout to position the new comment
					if (this.currentLayoutOptions) {
						this.recomputeLayout(this.currentLayoutOptions);
					}
				}
				break;

			case 'update':
				this.updateCommentInTree(comment.id, () => comment);
				break;

			case 'delete': {
				const parentId = this.findParentId(comment.id);

				if (parentId) {
					const cachedReplies = this.repliesCache.get(parentId) || [];
					this.repliesCache.set(
						parentId,
						cachedReplies.filter((reply) => reply.id !== comment.id)
					);
					this.incrementCacheVersion();

					this.updateCommentInTree(parentId, (parent) => ({
						...parent,
						num_replies: Math.max(0, parent.num_replies - 1)
					}));
				} else {
					this.repliesCache.delete(comment.id);
					this.incrementCacheVersion();
					this.store.update((comments) => comments.filter((c) => c.id !== comment.id));
				}
				break;
			}

			default:
				console.warn('Unknown WebSocket event type:', event.type);
		}
	}

	clear(): void {
		this.store.set([]);
		this.repliesCache.clear();
		this.documentId = null;
		this.currentUserId = null;
		this.computedGroups.set([]);
		this.currentLayoutOptions = null;
	}
}

export const commentStore = new CommentStore();
