<script lang="ts">
	import Pdf from '$lib/components/pdf/Pdf.svelte';
	import { documentStore } from '$lib/runes/document.svelte.js';
	import { documentWebSocket } from '$lib/stores/documentWebSocket.svelte.js';

	let { data } = $props();

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

	// Enable auto-persistence of comment states to localStorage
	documentStore.enablePersistence();

	// WebSocket connection lifecycle (separate effect with cleanup)
	// Only re-runs when documentId actually changes, not on every data refresh
	$effect(() => {
		const docId = documentId; // Track only the ID
		let wsUnsubscribe: (() => void) | null = null;
		let vmUnsubscribe: (() => void) | null = null;

		// Connect to WebSocket for real-time comment updates
		documentWebSocket.connect(docId.toString()).then(() => {
			wsUnsubscribe = documentWebSocket.onCommentEvent((event) => {
				documentStore.handleWebSocketEvent(event);
			});
			vmUnsubscribe = documentWebSocket.onViewModeChanged((ev) =>
				documentStore.handleWebSocketEvent(ev as any)
			);
		});

		// Cleanup when effect re-runs or component unmounts
		return () => {
			wsUnsubscribe?.();
			vmUnsubscribe?.();
			documentWebSocket.disconnect();
		};
	});
</script>

<div class="h-full w-full">
	<Pdf document={data.documentFile} />
</div>
