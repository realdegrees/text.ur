<script lang="ts">
	import TabContainer from '$lib/components/TabContainer.svelte';
	import LoginForm from '$lib/components/LoginForm.svelte';
	import type { PageData } from './$types';
	import AnonymousRegistrationForm from '$lib/components/AnonymousRegistrationForm.svelte';
	import { formatDateTime } from '$lib/util/dateFormat';
	import { goto, invalidateAll } from '$app/navigation';
	import { api } from '$api/client';
	import LL from '$i18n/i18n-svelte.js';
	import Badge from '$lib/components/badge.svelte';
	import { get } from 'svelte/store';

	let { data }: { data: PageData } = $props();

	/**
	 * Return a localized label for a permission key.
	 */
	function permissionLabel(permissionKey: string): string {
		const ll = get(LL) as any;
		const permissionsMap = ll.permissions as Record<string, () => string> | undefined;
		return permissionsMap?.[permissionKey]?.() || permissionKey;
	}

	async function joinGroup() {
		const joinResponse = await api.post(`/sharelinks/${data.shareLink.token}/use`, {}, { fetch });
		if (joinResponse.success) {
			goto(`/dashboard/groups/${data.shareLink.group.id}/documents`);
		}
	}
</script>

<div class="mt-20 flex h-full w-full flex-col items-center gap-6 p-6">
	<div class="flex w-full max-w-2xl flex-col gap-3">
		<div class="w-full rounded-lg bg-inset p-6 shadow-md">
			<div class="mb-4">
				<h1 class="text-3xl font-bold">{$LL.sharelink.description({ name: data.shareLink.group.name })}</h1>
				<p class="text-muted text-sm">{$LL.sharelink.members({ count: data.shareLink.group.member_count })}</p>
				<p class="text-muted text-sm">{$LL.sharelink.owner({ username: data.shareLink.group.owner?.username ?? '' })}</p>
				<p class="text-muted text-sm">{$LL.sharelink.created({ date: formatDateTime(data.shareLink.group.created_at) })}</p>

			<p>{$LL.sharelink.membershipWarning()}</p>
			</div>
		</div>

		{#if data.shareLink.expires_at || data.shareLink.permissions.length > 0 || (!data.shareLink.allow_anonymous_access && !data.sessionUser)}
			<div class="w-full rounded-lg bg-inset p-6 shadow-md">
				<h2 class="text-xl font-semibold">{$LL.sharelink.details()}</h2>
				{#if data.shareLink.expires_at}
					<p class="text-sm">{$LL.sharelink.expiresAt({ date: formatDateTime(data.shareLink.expires_at) })}</p>
				{/if}
				{#if data.shareLink.permissions.length > 0}
					<p class="mb-2 text-sm">{$LL.sharelink.permissionsReceived()}</p>
					<div class="flex flex-wrap gap-1">
						{#each data.shareLink.permissions as perm (perm)}
							<Badge item={perm} label={permissionLabel(perm)} showRemove={false} />
						{/each}
					</div>
				<p class="mt-2 text-xs">{$LL.sharelink.permissionsNote()}</p>
				{/if}
				{#if !data.shareLink.allow_anonymous_access && !data.sessionUser}
					<p class="text-sm">{$LL.sharelink.accountRequired()}</p>
				{/if}
			</div>
		{/if}

		{#if !data.sessionUser}
			<div class="w-full rounded-lg bg-inset p-6 shadow-md">
				<TabContainer
					tabs={[
						...(data.shareLink.allow_anonymous_access
							? [{ label: $LL.guest(), snippet: AnonymousRegistration }]
							: []),
						{ label: $LL.login(), snippet: Login }
					]}
				/>
			<a href="/login" class="block text-center text-xs text-blue-500/80"
				>{$LL.sharelink.noAccountRegister()}</a
			>
			</div>
		{:else}
		<button class="h-8 w-full cursor-pointer rounded bg-primary" onclick={joinGroup}>
			{$LL.sharelink.joinButton()}
		</button>
		{/if}
	</div>
</div>

{#snippet Login()}
	<LoginForm onSuccess={() => invalidateAll()} />
{/snippet}
{#snippet AnonymousRegistration()}
	<AnonymousRegistrationForm
		onSuccess={() => {
			invalidateAll();
			joinGroup();
		}}
		token={data.shareLink.token}
	/>
{/snippet}
