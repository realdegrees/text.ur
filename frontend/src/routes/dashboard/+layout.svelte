<script lang="ts">
	import type { MembershipFilter, MembershipRead } from '$api/types';
	import { goto } from '$app/navigation';
	import LL from '$i18n/i18n-svelte';
	import InfiniteScrollList from '$lib/components/infiniteScrollList.svelte';
	import ChevronDown from '~icons/material-symbols/keyboard-arrow-down';
	import AddIcon from '~icons/material-symbols/add-circle-outline';
	import { api } from '$api/client.js';
	import { page } from '$app/state';
	import type { Paginated } from '$api/pagination';
	import type { TypedFilter } from '$api/filters';
	import { notification } from '$lib/stores/notificationStore';

	let { data, children } = $props();	
</script>

<div class="flex w-full grow">
	<!-- left column (groups) -->
	<div class="flex h-full flex-col gap-2 p-2 pb-0 sm:w-[200px] md:w-[300px] lg:w-[400px]">
		<div class="flex flex-row items-center justify-between">
			<h2 class="w-full text-left text-2xl">{$LL.myGroups()}</h2>
			<a
				href="/dashboard/groups/create"
				class="bg-primary text-background hover:bg-primary/80 flex flex-row items-center gap-1 rounded-md px-3 py-1 text-sm transition-all"
				title="Create new group"
			>
				<AddIcon class="h-4 w-4" />
				<span>New</span>
			</a>
		</div>
		<hr class="border-text/50" />
		<InfiniteScrollList
			data={data.memberships}
			loadMore={async (offset, limit) => {
				const filters: TypedFilter<MembershipFilter>[] = [
					{
						field: 'accepted',
						operator: '==',
						value: 'true'
					}
				];
				if (page.params.groupid) {
					filters.push({
						field: 'group_id',
						operator: '!=',
						value: page.params.groupid
					});
				}
				const result = await api.get<Paginated<MembershipRead>, 'user'>(
					`/memberships?offset=${offset}&limit=${limit}`,
					{
						filters
					}
				);
				
				if (!result.success) {
					const errorMessage = $LL.errors[result.error.error_code]?.() || result.error.detail;
					notification('error', errorMessage);
					return undefined;
				}
				
				return result.data;
			}}
			step={2}
			onSelect={(membership) => {
				// Stay on the same selected subpage when switching groups
				const currentPage = page.url.pathname.split('/').pop();
				goto(`/dashboard/groups/${membership.group.id}/${page.params.groupid && currentPage || 'documents'}`);
			}}
		>
			{#snippet itemSnippet(membership: Omit<MembershipRead, "user">)}
				<div
					class:bg-primary={membership.group.id === page.params.groupid}
					class=" group flex w-full flex-row items-center justify-start rounded p-2 shadow-black transition-shadow"
				>
					<div class="group-hover:bg-primary mr-4 h-full rounded-sm">
						<ChevronDown class="h-6 w-6 -rotate-90" />
					</div>
					<div class="hover:shadow-inner-sym-[5px] flex w-full flex-col gap-1">
						<h3 class=" text-left font-semibold">{membership.group.name}</h3>
						<div class="flex flex-row gap-4 text-sm">
							<span>{$LL.group.memberships.owner()}: {membership.group.owner?.username}</span>
						</div>
					</div>
				</div>
			{/snippet}
		</InfiniteScrollList>
	</div>

	<!-- right column (subpage content, scrollable) -->
	<div class="h-full flex-1 overflow-y-auto p-4">
		{@render children?.()}
	</div>
</div>
