<script lang="ts">
	import LL from '$i18n/i18n-svelte';
	import { api } from '$api/client';
	import { notification } from '$lib/stores/notificationStore';
	import { sessionStore } from '$lib/runes/session.svelte';
	import DownloadIcon from '~icons/material-symbols/download';

	let exporting = $state(false);

	async function handleExport() {
		const user = sessionStore.currentUser;
		if (!user) return;

		exporting = true;
		try {
			const result = await api.get<Record<string, unknown>>(`/users/${user.id}/export`);
			if (!result.success) {
				notification(result.error);
				return;
			}

			const blob = new Blob([JSON.stringify(result.data, null, 2)], {
				type: 'application/json'
			});
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = 'text-ur-data-export.json';
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);
		} finally {
			exporting = false;
		}
	}
</script>

{#if sessionStore.currentUser}
	<button
		class="not-prose flex items-center gap-2 rounded bg-primary px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
		onclick={handleExport}
		disabled={exporting}
	>
		<DownloadIcon class="h-4 w-4" />
		{exporting ? $LL.loading() : $LL.privacy.exportButton()}
	</button>
{:else}
	<p class="text-sm text-text/60 italic">{$LL.privacy.exportLoginRequired()}</p>
{/if}
