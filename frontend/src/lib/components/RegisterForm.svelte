<script lang="ts">
	import Field from '$lib/components/advancedInput.svelte';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import { api } from '$api/client';

	let { onSuccess }: { onSuccess: () => void } = $props();

	let username = $state('');
	let email = $state('');
	let firstName = $state('');
	let lastName = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let isLoading = $state(false);
	let errorMessage = $state<string | null>(null);
	let successMessage = $state<string | null>(null);

	async function handleRegister(e: Event) {
		e.preventDefault();
		isLoading = true;
		errorMessage = null;
		successMessage = null;

		if (password !== confirmPassword) {
			errorMessage = 'Passwords do not match';
			isLoading = false;
			return;
		}

		try {
			const result = await api.post('/register', {
				username,
				email,
				password,
				first_name: firstName || undefined,
				last_name: lastName || undefined
			});

			if (!result.success) {
				errorMessage = result.error.detail || 'Registration failed';
				return;
			}

			successMessage = 'Registration successful! Please check your email to verify your account.';
			onSuccess();
		} finally {
			isLoading = false;
		}
	}
</script>

<form onsubmit={handleRegister} class="flex flex-col gap-4">
	{#if errorMessage}
		<div class="error-message">{errorMessage}</div>
	{/if}
	{#if successMessage}
		<div class="success-message">{successMessage}</div>
	{/if}
	<Field bind:value={username} label="Username" required />
	<Field bind:value={email} label="Email" required />
	<Field bind:value={firstName} label="First Name" />
	<Field bind:value={lastName} label="Last Name" />
	<Field bind:value={password} label="Password" hidden required />
	<Field bind:value={confirmPassword} label="Confirm Password" hidden required />
	<button type="submit" class="submit-button" disabled={isLoading}>
		{#if isLoading}
			<Loading />
		{:else}
			Register
		{/if}
	</button>
</form>

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