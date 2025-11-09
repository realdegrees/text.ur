<script lang="ts">
	import { enhance } from '$app/forms';
	import type { ActionData } from './$types';
	import { LL } from '$i18n/i18n-svelte';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import { Tween } from 'svelte/motion';
	import { cubicOut } from 'svelte/easing';
	import Field from '$lib/components/advancedInput.svelte';

	let { form = $bindable<ActionData>() } = $props();

	let isRegistering = $state(false);
	let isLoading = $state(false);

	const toggleMode = () => (isRegistering = !isRegistering);

	const handleSubmit = () => {
		isLoading = true;
		return async ({ update }: { update: () => Promise<void> }) => {
			await update();
			isLoading = false;
		};
	};

	let containerEl: HTMLDivElement;
	let innerEl: HTMLDivElement;
	const height = new Tween(0, { duration: 250, easing: cubicOut });

	$effect(() => {
		if (innerEl) height.set(innerEl.offsetHeight);
	});
</script>

<div class="flex h-full w-full items-center justify-center p-4">
	<div
		class="w-full max-w-md overflow-hidden rounded-lg bg-inset p-8 shadow-lg"
		bind:this={containerEl}
		style="height: {height}px"
	>
		<div bind:this={innerEl}>
			<h1 class="mb-6 text-center text-3xl font-bold text-text">
				{isRegistering ? $LL.register() : $LL.login()}
			</h1>

			{#if form?.error}
				<div
					class="mb-4 rounded border border-red-300 bg-red-100 p-3 text-red-700 dark:border-red-700 dark:bg-red-900/30 dark:text-red-300"
				>
					{form.error}
				</div>
			{/if}

			{#if form?.success}
				<div
					class="mb-4 rounded border border-green-300 bg-green-100 p-3 text-green-700 dark:border-green-700 dark:bg-green-900/30 dark:text-green-300"
				>
					{form.message}
				</div>
			{/if}

			<form
				method="POST"
				action="?/{isRegistering ? 'register' : 'login'}"
				use:enhance={handleSubmit}
				class="flex flex-col gap-4"
			>
				{#if isRegistering}
					<Field name="username" label={$LL.username()} required />
					<Field name="email" label={$LL.email()} required />
					<Field name="firstName" label={$LL.firstName()} />
					<Field name="lastName" label={$LL.lastName()} />
					<Field name="password" label={$LL.password()} hidden required />
					<Field name="confirmPassword" label={$LL.confirmPassword()} hidden required />
				{:else}
					<Field name="username" label={$LL.usernameOrEmail()} required />
					<Field name="password" label={$LL.password()} hidden required />
				{/if}

				<button
					type="submit"
					class="w-full rounded bg-primary px-4 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:bg-gray-400 dark:disabled:bg-gray-600"
					disabled={isLoading}
				>
					{#if isLoading}
						<Loading class="m-auto" />
					{:else}
						{isRegistering ? $LL.register() : $LL.login()}
					{/if}
				</button>
			</form>

			<div class="mt-4 text-center">
				<button
					type="button"
					class="text-primary underline transition-colors hover:text-secondary disabled:cursor-not-allowed disabled:text-gray-400"
					onclick={toggleMode}
					disabled={isLoading}
				>
					{isRegistering ? $LL.alreadyHaveAccount() : $LL.needAccount()}
				</button>
			</div>
		</div>
	</div>
</div>
