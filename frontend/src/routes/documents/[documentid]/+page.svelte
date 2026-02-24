<script lang="ts">
	import Pdf from '$lib/components/pdf/Pdf.svelte';
	import { documentStore } from '$lib/runes/document.svelte.js';
	import { documentWebSocket } from '$lib/stores/documentWebSocket.svelte.js';
	import { LL } from '$i18n/i18n-svelte';

	let { data } = $props();

	let wsDisconnected = $derived(
		documentWebSocket.hasConnectedBefore &&
			(documentWebSocket.state === 'disconnected' || documentWebSocket.state === 'error')
	);

	let prevRootComments = $state<typeof data.rootComments | null>(null);

	// Extract document ID to prevent WebSocket effect from re-running on data refresh
	// (invalidateAll updates data object but ID stays the same)
	let documentId = $derived(data.document.id);

	// Initialize session and document stores (reactive to data changes)
	// Use data.X directly so the effect re-runs when invalidateAll() updates data
	$effect(() => {
		if (JSON.stringify(prevRootComments) !== JSON.stringify(data.rootComments)) {
			prevRootComments = data.rootComments;
			documentStore.setTopLevelComments(data.rootComments);
		}
	});
	$effect(() => {
		documentStore.loadedDocument = data.document;
	});
	$effect(() => {
		documentStore.groupReactions = data.scoreConfig?.reactions ?? [];
	});
	$effect(() => {
		documentStore.setTaskData(data.tasks, data.taskResponses);
	});

	// Enable auto-persistence of comment states to localStorage
	documentStore.enablePersistence();

	// WebSocket connection lifecycle (separate effect with cleanup)
	// Only re-runs when documentId actually changes, not on every data refresh
	$effect(() => {
		const docId = documentId; // Track only the ID
		let wsUnsubscribe: (() => void) | null = null;
		let vmUnsubscribe: (() => void) | null = null;
		let taskUnsubscribe: (() => void) | null = null;

		// Connect to WebSocket for real-time comment updates
		documentWebSocket
			.connect(docId.toString())
			.then(() => {
				wsUnsubscribe = documentWebSocket.onCommentEvent((event) => {
					documentStore.handleWebSocketEvent(event);
				});
				vmUnsubscribe = documentWebSocket.onViewModeChanged((ev) =>
					documentStore.handleWebSocketEvent(ev as any)
				);
				taskUnsubscribe = documentWebSocket.onTasksUpdated(() => {
					documentStore.handleTasksUpdatedEvent();
				});
			})
			.catch((err) => {
				console.error('[WS] Connection failed:', err.message);
			});

		// Cleanup when effect re-runs or component unmounts
		return () => {
			wsUnsubscribe?.();
			vmUnsubscribe?.();
			taskUnsubscribe?.();
			documentWebSocket.disconnect();
		};
	});
</script>

<div class="relative h-full w-full">
	{#if wsDisconnected}
		<div
			class="absolute top-0 right-0 left-0 z-50 bg-yellow-500/90 px-4 py-2 text-center text-sm font-medium text-black"
		>
			{$LL.documentView.wsDisconnected()}
		</div>
	{/if}
	<Pdf document={data.documentFile} />
</div>
