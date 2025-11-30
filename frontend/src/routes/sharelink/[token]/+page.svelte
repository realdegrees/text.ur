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
		<div class="bg-inset w-full rounded-lg p-6 shadow-md">
			<div class="mb-4">
				<h1 class="text-3xl font-bold">You have been invited to {data.shareLink.group.name}</h1>
				<p class="text-muted text-sm">Members: {data.shareLink.group.member_count}</p>
				<p class="text-muted text-sm">Owner: {data.shareLink.group.owner?.username}</p>
				<p class="text-muted text-sm">Created: {formatDateTime(data.shareLink.group.created_at)}</p>

				<p>
					Your membership will be bound to this invite link. If it is revoked or expires you will be
					removed from the group.
				</p>
			</div>
		</div>

		{#if data.shareLink.expires_at || data.shareLink.permissions.length > 0 || (!data.shareLink.allow_anonymous_access && !data.sessionUser)}
			<div class="bg-inset w-full rounded-lg p-6 shadow-md">
				<h2 class="text-xl font-semibold">Sharelink Details</h2>
				{#if data.shareLink.expires_at}
					<p class="text-sm">Expires At: {formatDateTime(data.shareLink.expires_at)}</p>
				{/if}
				{#if data.shareLink.permissions.length > 0}
					<p class="mb-2 text-sm">You will automatically receive these permissions:</p>
					<div class="flex flex-wrap gap-1">
						{#each data.shareLink.permissions as perm (perm)}
							<Badge item={perm} label={permissionLabel(perm)} showRemove={false} />
						{/each}
					</div>
					<p class="mt-2 text-xs">
						Invite link permissions are continuously synced with your membership permissions.
					</p>
				{/if}
				{#if !data.shareLink.allow_anonymous_access && !data.sessionUser}
					<p class="text-sm">This invite link requires an account.</p>
				{/if}
			</div>
		{/if}

		{#if !data.sessionUser}
			<div class="bg-inset w-full rounded-lg p-6 shadow-md">
				<TabContainer
					tabs={[
						...(data.shareLink.allow_anonymous_access
							? [{ label: 'Guest', snippet: AnonymousRegistration }]
							: []),
						{ label: 'Login', snippet: Login }
					]}
				/>
				<a href="/login" class="block text-center text-xs text-blue-500/80"
					>If you do not have an account you can register here and then visit this link again.</a
				>
			</div>
		{:else}
			<button
				class="bg-primary h-8 w-full cursor-pointer rounded"
				onclick={joinGroup}
			>
				Join
			</button>
		{/if}
	</div>
</div>

{#snippet Login()}
	<LoginForm onSuccess={() => invalidateAll()} />
{/snippet}
{#snippet AnonymousRegistration()}
	<AnonymousRegistrationForm onSuccess={() => {
		invalidateAll();
		joinGroup();
	}} token={data.shareLink.token} />
{/snippet}
