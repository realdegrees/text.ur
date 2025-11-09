<script lang="ts">
	import type { GroupRead } from '$api/types';
	import { goto } from '$app/navigation';
	import LL from '$i18n/i18n-svelte';
	import InfiniteScrollList from '$lib/components/infiniteScrollList.svelte';
	import ChevronDown from '~icons/material-symbols/keyboard-arrow-down';
	import AddIcon from '~icons/material-symbols/add-circle-outline';

	let { data, children } = $props();
	console.log(data);
</script>

<div class="flex w-full grow">
	<!-- left column (groups) -->
	<div class="flex h-full flex-col gap-2 p-2 pb-0 sm:w-[200px] md:w-[300px] lg:w-[400px]">
		<div class="flex flex-row items-center justify-between">
			<h2 class="w-full text-left text-2xl">{$LL.myGroups()}</h2>
			<a
				href="/dashboard/groups/create"
				class="flex flex-row items-center gap-1 rounded-md bg-primary px-3 py-1 text-sm text-background transition-all hover:bg-primary/80"
				title="Create new group"
			>
				<AddIcon class="h-4 w-4" />
				<span>New</span>
			</a>
		</div>
		<hr class="border-text/50" />
		<InfiniteScrollList
			data={data.groups}
			url="/groups"
			step={2}
			filters={[{ field: 'accepted', operator: '==', value: 'true' }]}
			onSelect={(group) => {
				goto(`/dashboard/groups/${group.id}`);
			}}
		>
			{#snippet itemSnippet(group: GroupRead)}
				<div
					class="flex w-full flex-row items-center justify-start rounded p-2 shadow-black transition-shadow hover:shadow-inner-sym-[5px]"
				>
					<div
						class:bg-primary={group.id === data.selectedGroup?.id}
						class="mr-4 h-full rounded-sm"
					>
						<ChevronDown class="h-6 w-6 -rotate-90" />
					</div>
					<div class="flex w-full flex-col gap-1">
						<h3 class=" text-left font-semibold">{group.name}</h3>
						<div class="flex flex-row gap-4 text-sm">
							<span>{$LL.group.memberships.owner()}: {group.owner?.username}</span>
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
