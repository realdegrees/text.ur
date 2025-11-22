<script lang="ts">
	import Pdf from '$lib/components/pdf/Pdf.svelte';
	import { documentStore } from '$lib/runes/document.svelte.js';
	import { sessionStore } from '$lib/runes/session.svelte.js';

	let { data } = $props();
	let { document, membership, rootComments, documentFile } = data;

	$effect(() => {
		// Initialize the session store with user and membership for permission checks
		sessionStore.currentUser = data.sessionUser;
		sessionStore.currentMembership = membership;

		// Initialize the document store with the loaded document and comments
		documentStore.setDocument(document);
		documentStore.setRootComments(rootComments);
	});
</script>

<div class="h-full w-full">
	<Pdf document={documentFile} />
</div>
