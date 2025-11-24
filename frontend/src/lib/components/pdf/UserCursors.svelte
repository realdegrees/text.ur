<script lang="ts">
	import { documentWebSocket, type UserCursor } from '$lib/stores/documentWebSocket';
	import { documentStore } from '$lib/runes/document.svelte';
	import { fade } from 'svelte/transition';

	interface Props {
		viewerContainer: HTMLDivElement | null;
	}

	let { viewerContainer }: Props = $props();

	// Check if cursor sharing is enabled (disabled in restricted mode)
	let isCursorSharingEnabled = $derived(documentStore.loadedDocument?.view_mode !== 'restricted');

	// Subscribe to user cursors
	let cursorsMap: Map<number, UserCursor> = $state(new Map());

	$effect(() => {
		const unsubscribe = documentWebSocket.userCursors.subscribe((cursors) => {
			cursorsMap = cursors;
		});
		return unsubscribe;
	});

	// Get page element for a specific page number
	const getPageElement = (pageNumber: number): HTMLElement | null => {
		if (!viewerContainer) return null;
		return viewerContainer.querySelector(
			`[data-page-number="${pageNumber}"]`
		) as HTMLElement | null;
	};

	// Calculate absolute position for a cursor
	const getCursorPosition = (cursor: UserCursor): { x: number; y: number } | null => {
		const pageEl = getPageElement(cursor.page);
		if (!pageEl) return null;

		const containerRect = viewerContainer?.getBoundingClientRect();
		const pageRect = pageEl.getBoundingClientRect();
		if (!containerRect) return null;

		// Convert normalized coordinates to absolute position within viewer
		const x = pageRect.left - containerRect.left + cursor.x * pageRect.width;
		const y = pageRect.top - containerRect.top + cursor.y * pageRect.height;

		return { x, y };
	};

	// Generate a consistent color based on user ID
	const getUserColor = (userId: number): string => {
		const colors = [
			'#3b82f6', // blue
			'#22c55e', // green
			'#a855f7', // purple
			'#f97316', // orange
			'#ec4899', // pink
			'#14b8a6', // teal
			'#6366f1', // indigo
			'#f43f5e' // rose
		];
		return colors[userId % colors.length];
	};

	// Track mouse movement on PDF and send position updates
	const handleMouseMove = (e: MouseEvent) => {
		if (!viewerContainer || !isCursorSharingEnabled) return;

		// Find which page the mouse is over
		const pages = viewerContainer.querySelectorAll('[data-page-number]') as NodeListOf<HTMLElement>;

		for (const pageEl of pages) {
			const pageRect = pageEl.getBoundingClientRect();

			// Check if mouse is within this page
			if (
				e.clientX >= pageRect.left &&
				e.clientX <= pageRect.right &&
				e.clientY >= pageRect.top &&
				e.clientY <= pageRect.bottom
			) {
				const pageNumber = parseInt(pageEl.getAttribute('data-page-number') || '1', 10);

				// Normalize coordinates relative to page
				const x = (e.clientX - pageRect.left) / pageRect.width;
				const y = (e.clientY - pageRect.top) / pageRect.height;

				documentWebSocket.sendMousePosition(x, y, pageNumber, true);
				return;
			}
		}
	};

	// Handle mouse leaving the PDF area
	const handleMouseLeave = () => {
		if (!isCursorSharingEnabled) return;
		documentWebSocket.sendMousePosition(0, 0, 1, false);
	};

	// Attach mouse event listeners
	$effect(() => {
		if (!viewerContainer) return;

		viewerContainer.addEventListener('mousemove', handleMouseMove);
		viewerContainer.addEventListener('mouseleave', handleMouseLeave);

		return () => {
			viewerContainer.removeEventListener('mousemove', handleMouseMove);
			viewerContainer.removeEventListener('mouseleave', handleMouseLeave);
			// Send hidden cursor when leaving document page
			documentWebSocket.sendMousePosition(0, 0, 1, false);
		};
	});

	// Cleanup timer to hide stale cursors
	// TTL: 200ms (4x the 50ms throttle interval) - cursors disappear quickly when user stops sending
	const CURSOR_TTL_MS = 200;
	const CLEANUP_INTERVAL_MS = 100;

	$effect(() => {
		const interval = setInterval(() => {
			const now = Date.now();
			let hasChanges = false;
			cursorsMap.forEach((cursor, userId) => {
				if (cursor.visible && now - cursor.lastUpdate > CURSOR_TTL_MS) {
					// Mark as invisible if stale
					cursorsMap.set(userId, { ...cursor, visible: false });
					hasChanges = true;
				}
			});
			if (hasChanges) {
				// eslint-disable-next-line svelte/prefer-svelte-reactivity
				cursorsMap = new Map(cursorsMap);
			}
		}, CLEANUP_INTERVAL_MS);

		return () => clearInterval(interval);
	});
</script>

<!-- Cursor overlay layer - positioned within the PDF viewer container -->
<!-- Only show cursors when cursor sharing is enabled (not in restricted mode) and user hasn't toggled them off -->
{#if isCursorSharingEnabled && documentStore.showOtherCursors}
	{#each cursorsMap.entries() as [userId, cursor] (userId)}
		{@const position = getCursorPosition(cursor)}
		{#if cursor.visible && position}
			<div
				class="pointer-events-none absolute z-50 transition-all duration-75"
				style="left: {position.x}px; top: {position.y}px;"
				out:fade={{ duration: 400, delay: 2000 }}
			>
				<!-- Cursor pointer SVG -->
				<svg
					class="h-5 w-5 -translate-x-0.5 -translate-y-0.5 drop-shadow-md"
					viewBox="0 0 24 24"
					fill={getUserColor(cursor.user_id)}
					stroke="white"
					stroke-width="1.5"
				>
					<path
						d="M5.5 3.21V20.8c0 .45.54.67.85.35l4.86-4.86a.5.5 0 0 1 .35-.15h6.87a.5.5 0 0 0 .35-.85L6.35 2.86a.5.5 0 0 0-.85.35Z"
					/>
				</svg>
				<!-- Username label -->
				<div
					class="absolute top-3 left-4 rounded-full px-2 py-0.5 text-[10px] font-medium whitespace-nowrap text-white shadow-md"
					style="background-color: {getUserColor(cursor.user_id)};"
				>
					{cursor.username}
				</div>
			</div>
		{/if}
	{/each}
{/if}
