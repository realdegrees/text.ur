<script lang="ts">
	import Field from '$lib/components/advancedInput.svelte';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import { api } from '$api/client';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';

	// Extract token from URL params before clearing it
	const token = $page.params.token;

	// Clear token from URL immediately for security (prevents it staying in browser history)
	onMount(() => {
		if (typeof window !== 'undefined') {
			window.history.replaceState({}, '', '/password-reset');
		}
	});

	let password = $state('');
	let confirmPassword = $state('');
	let isLoading = $state(false);
	let errorMessage = $state<string | null>(null);

	async function handlePasswordReset(e: Event) {
		e.preventDefault();
		isLoading = true;
		errorMessage = null;

		if (password !== confirmPassword) {
			errorMessage = 'Passwords do not match';
			isLoading = false;
			return;
		}

		if (password.length < 8) {
			errorMessage = 'Password must be at least 8 characters';
			isLoading = false;
			return;
		}

		try {
			const result = await api.update(`/login/reset/verify/${token}`, { password });

			if (!result.success) {
				errorMessage =
					result.error.detail || 'Failed to reset password. The link may be expired or invalid.';
				return;
			}

			// Success! Redirect to login with a success message
			goto('/login?reset=success');
		} finally {
			isLoading = false;
		}
	}
</script>

<div class="mt-20 flex h-fit w-full justify-center">
	<div class="w-full max-w-md overflow-hidden rounded-lg bg-inset p-8 shadow-lg">
		<h1 class="mb-2 text-2xl font-bold">Set New Password</h1>
		<p class="mb-6 text-sm text-gray-600">Enter your new password below.</p>

		<form onsubmit={handlePasswordReset} class="flex flex-col gap-4">
			{#if errorMessage}
				<div class="error-message">{errorMessage}</div>
			{/if}
			<Field bind:value={password} label="New Password" hidden required />
			<Field bind:value={confirmPassword} label="Confirm Password" hidden required />
			<button type="submit" class="submit-button" disabled={isLoading}>
				{#if isLoading}
					<Loading />
				{:else}
					Reset Password
				{/if}
			</button>
		</form>

		<div class="mt-4 text-center text-sm">
			<a href="/login" class="text-blue-500 hover:underline">Back to Login</a>
		</div>
	</div>
</div>

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
