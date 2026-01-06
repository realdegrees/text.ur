<script lang="ts">
	import Field from '$lib/components/advancedInput.svelte';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import { api } from '$api/client';

	let email = $state('');
	let isLoading = $state(false);
	let errorMessage = $state<string | null>(null);
	let successMessage = $state<string | null>(null);

	async function handleResetRequest(e: Event) {
		e.preventDefault();
		isLoading = true;
		errorMessage = null;
		successMessage = null;

		try {
			const result = await api.post('/login/reset', { email });

			if (!result.success) {
				errorMessage = result.error.detail || 'Failed to send reset email';
				return;
			}

			successMessage =
				'Password reset email sent! Please check your inbox for further instructions.';
			email = ''; // Clear the form
		} finally {
			isLoading = false;
		}
	}
</script>

<div class="mt-20 flex h-fit w-full justify-center">
	<div class="w-full max-w-md overflow-hidden rounded-lg bg-inset p-8 shadow-lg">
		<h1 class="mb-2 text-2xl font-bold">Reset Password</h1>
		<p class="mb-6 text-sm text-gray-600">
			Enter your email address and we'll send you a link to reset your password.
		</p>

		<form onsubmit={handleResetRequest} class="flex flex-col gap-4">
			{#if errorMessage}
				<div class="error-message">{errorMessage}</div>
			{/if}
			{#if successMessage}
				<div class="success-message">{successMessage}</div>
			{/if}
			<Field bind:value={email} label="Email" required />
			<button type="submit" class="submit-button" disabled={isLoading}>
				{#if isLoading}
					<Loading />
				{:else}
					Send Reset Link
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
	.success-message {
		color: green;
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
