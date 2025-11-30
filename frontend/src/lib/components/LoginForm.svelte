<script lang="ts">
	import Field from '$lib/components/advancedInput.svelte';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import { api } from '$api/client';

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
				errorMessage = result.error.detail || 'Invalid username/email or password';
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
		<div class="error-message">{errorMessage}</div>
	{/if}
	<Field bind:value={username} label="Username/Email" required />
	<Field bind:value={password} label="Password" hidden required />
	<button type="submit" class="submit-button" disabled={isLoading}>
		{#if isLoading}
			<Loading />
		{:else}
			Login
		{/if}
	</button>
</form>

<style>
	.error-message {
		color: red;
		font-size: 0.875rem;
	}
	.submit-button {
		background-color: var(--color-primary);
		color: white;
		padding: 0.75rem;
		border-radius: 0.375rem;
		font-weight: bold;
		cursor: pointer;
	}
	.submit-button:disabled {
		background-color: gray;
		cursor: not-allowed;
	}
</style>
