<script lang="ts">
	import type { GroupMembershipRead } from '$api/types';
	import InfiniteScrollList from '$lib/components/infiniteScrollList.svelte';
	import OwnerIcon from '~icons/material-symbols/admin-panel-settings-outline';
	import PendingIcon from '~icons/material-symbols/pending-outline';
	import PeopleIcon from '~icons/material-symbols/group-outline';

	let { data } = $props();
	let memberships = $derived(data.memberships);
	let group = $derived(data.selectedGroup!);
</script>

<div class="flex h-full w-full flex-col gap-4">
	<!-- Members List -->
	<div class="flex flex-col gap-2">
		<div class="flex flex-row items-center justify-end">
			<span class="text-sm text-text/70">Total: {memberships.total}</span>
		</div>

		{#if memberships.total === 0}
			<div class="flex flex-col items-center justify-center gap-2 rounded-md bg-text/5 p-8">
				<PeopleIcon class="h-12 w-12 text-text/30" />
				<p class="text-text/70">No members in this group yet</p>
			</div>
		{:else}
			<InfiniteScrollList data={memberships} url={`/groups/${group.id}/memberships`} step={10}>
				{#snippet itemSnippet(membership: GroupMembershipRead)}
					<div
						class="flex flex-row items-center justify-between rounded-md bg-text/5 p-2 transition-all hover:bg-text/10"
					>
						<div class="flex flex-col gap-2">
							<div class="flex flex-row items-center gap-2">
								<span class="text-sm font-semibold">{membership.user.username}</span>
								{#if membership.user.first_name || membership.user.last_name}
									<span class="my-auto text-sm text-text/70"
										>({membership.user.first_name} {membership.user.last_name})</span
									>
								{/if}
								{#if membership.is_owner}
									<div
										class="flex flex-row items-center gap-1 rounded-full bg-primary/20 px-2 py-0.5 text-xs"
									>
										<OwnerIcon class="h-3 w-3" />
										<span>Owner</span>
									</div>
								{/if}
								{#if !membership.accepted}
									<div
										class="flex flex-row items-center gap-1 rounded-full bg-text/20 px-2 py-0.5 text-xs"
									>
										<PendingIcon class="h-3 w-3" />
										<span>Pending</span>
									</div>
								{/if}
							</div>
							{#if membership.permissions.length > 0}
								<div class="flex flex-row flex-wrap gap-1">
									{#each membership.permissions as permission (permission)}
										<span class="rounded bg-text/10 px-2 py-0.5 font-mono text-xs text-text/70">
											{permission}
										</span>
									{/each}
								</div>
							{/if}
						</div>
					</div>
				{/snippet}
			</InfiniteScrollList>
		{/if}
	</div>
</div>
