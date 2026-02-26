<script lang="ts">
	import Field from '$lib/components/advancedInput.svelte';
	import InfoBanner from '$lib/components/InfoBanner.svelte';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import { api } from '$api/client';
	import { resolveErrorMessage } from '$lib/util/errorMessage';

	let { onSuccess }: { onSuccess: () => void } = $props();

	let username = $state('');
	let password = $state('');
	let isLoading = $state(false);
	let errorMessage = $state<string | null>(null);

	async function handleLogin(e: Event) {
		e.preventDefault();
		isLoading = true;
		errorMessage = null;

		try {
			const formData = new FormData();
			formData.append('username', username);
			formData.append('password', password);

			const result = await api.post('/login', formData);

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

<form onsubmit={handleLogin} class="flex flex-col gap-4">
	{#if errorMessage}
		<InfoBanner variant="error">{errorMessage}</InfoBanner>
	{/if}
	<Field bind:value={username} label="Username/Email" required />
	<Field bind:value={password} label="Password" hidden required />
	<div class="flex justify-end">
		<a
			href="/password-reset/request"
			class="-mt-2 text-sm text-primary no-underline hover:underline"
		>
			Forgot password?
		</a>
	</div>
	<button type="submit" class="w-full btn-primary py-3" disabled={isLoading}>
		{#if isLoading}
			<Loading />
		{:else}
			Login
		{/if}
	</button>
</form>
