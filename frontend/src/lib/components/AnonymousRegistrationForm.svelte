<script lang="ts">
	import Field from '$lib/components/advancedInput.svelte';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import { api } from '$api/client';

	let { onSuccess, token }: { onSuccess: () => void; token: string } = $props();

	let username = $state('');
	let isLoading = $state(false);
	let errorMessage = $state<string | null>(null);

	async function handleAnonymousRegister(e: Event) {
		e.preventDefault();
		isLoading = true;
		errorMessage = null;

		if (!username.trim()) {
			errorMessage = 'Username is required';
			isLoading = false;
			return;
		}

		try {
			const result = await api.post('/register', { username, token });

			if (!result.success) {
				errorMessage = result.error.detail || 'Anonymous registration failed';
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
		<div class="text-red-500 text-sm">{errorMessage}</div>
	{/if}
	<Field bind:value={username} label="Username" required />
	<button 
		type="submit" 
		class="bg-primary text-text py-3 rounded-md font-bold  disabled:cursor-not-allowed disabled:opacity-50"
		disabled={isLoading || !username.trim()}
	>
		{#if isLoading}
			<Loading />
		{:else}
			Join
		{/if}
	</button>
</form>