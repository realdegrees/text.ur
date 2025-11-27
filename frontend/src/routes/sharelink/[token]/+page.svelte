<script lang="ts">
	import { api } from '$api/client';
	import { invalidate, invalidateAll } from '$app/navigation';
	import { LL } from '$i18n/i18n-svelte';
	import Field from '$lib/components/advancedInput.svelte';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import type { PageData } from './$types';
	import { page } from '$app/state';
	import type { UserCreate } from '$api/types';

	let { data }: { data: PageData } = $props();

	let username = $state('');
	let firstName = $state('');
	let lastName = $state('');
	let isLoading = $state(false);
	let error = $state('');

	async function handleAnonymousRegister() {
		if (!username.trim()) {
			error = $LL.sharelink.errors.usernameRequired();
			return;
		}

		isLoading = true;
		error = '';

		try {
			const response = await api.post('/register', {
				token: data.token,
				username: username.trim(),
				first_name: firstName.trim() || undefined,
				last_name: lastName.trim() || undefined
			} satisfies UserCreate);

			if (!response.success) {
				error = response.error.detail || $LL.sharelink.errors.registerFailed();
				return;
			}

			// Now the api login has attached auth cookies so we can invalidate and let the page ssr handle the group join
			invalidateAll();
		} catch (err: any) {
			error = err.detail || $LL.sharelink.errors.registerFailed();
		} finally {
			isLoading = false;
		}
	}
</script>

<div class="flex h-full w-full items-center justify-center p-4">
	<div class="w-full max-w-md overflow-hidden rounded-lg bg-inset p-8 shadow-lg">
		<h1 class="mb-2 text-center text-3xl font-bold text-text">{$LL.sharelink.title()}</h1>
		<p class="text-muted mb-6 text-center text-sm">
			{$LL.sharelink.description()}
		</p>

		{#if error}
			<div
				class="mb-4 rounded border border-red-300 bg-red-100 p-3 text-red-700 dark:border-red-700 dark:bg-red-900/30 dark:text-red-300"
			>
				{error}
			</div>
		{/if}

		<form
			onsubmit={(e) => {
				e.preventDefault();
				handleAnonymousRegister();
			}}
			class="flex flex-col gap-4"
		>
			<Field name="username" label={$LL.username()} bind:value={username} required />
			<Field name="firstName" label={$LL.firstName()} bind:value={firstName} />
			<Field name="lastName" label={$LL.lastName()} bind:value={lastName} />

			<button
				type="submit"
				disabled={isLoading}
				class="w-full rounded bg-primary px-4 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:bg-gray-400 dark:disabled:bg-gray-600"
			>
				{#if isLoading}
					<Loading class="m-auto" />
				{:else}
					{$LL.continue()}
				{/if}
			</button>
		</form>

		<div class="mt-4 text-center">
			<a
				href="/login?redirect=/sharelink/{data.token}"
				class="text-primary underline transition-colors hover:text-secondary"
				onclick={() => invalidate(page.url.pathname)}
			>
				{$LL.sharelink.alreadyHaveAccount()}
			</a>
		</div>
	</div>
</div>
