<script lang="ts">
	import ShareLinksManager from '$lib/components/shareLinksManager.svelte';

	let { data } = $props();
	let group = $derived(data.membership.group);
</script>

<div class="flex h-full w-full flex-col p-6">
	<ShareLinksManager shareLinks={data.shareLinks} groupId={group.id} />
</div>
