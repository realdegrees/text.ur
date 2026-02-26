<script lang="ts">
	import Field from '$lib/components/advancedInput.svelte';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import { api } from '$api/client';
	import { resolveErrorMessage } from '$lib/util/errorMessage';
	import InfoBanner from '$lib/components/InfoBanner.svelte';
	import LL from '$i18n/i18n-svelte';

	let { onSuccess, token }: { onSuccess: () => void; token: string } = $props();

	let username = $state('');
	let isLoading = $state(false);
	let errorMessage = $state<string | null>(null);

	async function handleAnonymousRegister(e: Event) {
		e.preventDefault();
		isLoading = true;
		errorMessage = null;

		if (!username.trim()) {
			errorMessage = $LL.sharelink.errors.usernameRequired();
			isLoading = false;
			return;
		}

		try {
			const result = await api.post('/register', { username, token });

			if (!result.success) {
				errorMessage = resolveErrorMessage(result.error);
				return;
			}

			onSuccess();
		} finally {
			isLoading = false;
		}
	}
</script>

<form onsubmit={handleAnonymousRegister} class="flex flex-col gap-4">
	{#if errorMessage}
		<InfoBanner variant="error">{errorMessage}</InfoBanner>
	{/if}
	<Field bind:value={username} label="Username" required />
	<button
		type="submit"
		class="rounded-md bg-primary py-3 font-bold text-text disabled:cursor-not-allowed disabled:opacity-50"
		disabled={isLoading || !username.trim()}
	>
		{#if isLoading}
			<Loading />
		{:else}
			Join
		{/if}
	</button>
</form>
