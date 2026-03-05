<script lang="ts">
	import { goto } from '$app/navigation';
	import MembershipList from '$lib/components/membershipList.svelte';
	import { page } from '$app/state';
	import LL from '$i18n/i18n-svelte';
	import CollapseIcon from '~icons/material-symbols/chevron-left';
	import ExpandIcon from '~icons/material-symbols/chevron-right';

	let { data, children } = $props();

	let isExpanded = $state(true);

	function handleGroupSelect(membership: any) {
		const currentPage = page.url.pathname.split('/').pop();
		goto(
			`/dashboard/groups/${membership.group.id}/${(page.params.groupid && currentPage) || 'documents'}`
		);
	}
</script>

<div class="flex w-full grow">
	<!-- left column (groups) -->
	<div
		role="navigation"
		aria-label="Groups sidebar"
		class="no-scrollbar flex h-full shrink-0 flex-col overflow-x-hidden overflow-y-auto border-r border-text/10 bg-inset transition-all duration-200"
		class:w-12={!isExpanded}
		class:w-[200px]={isExpanded}
		class:sm:w-[200px]={isExpanded}
		class:md:w-[300px]={isExpanded}
		class:lg:w-[400px]={isExpanded}
	>
		<!-- Expand/Collapse Button -->
		<button
			class="flex shrink-0 items-center justify-center gap-2 border-b border-text/10 p-2 text-text/50 transition-colors hover:bg-text/5 hover:text-text/70"
			onclick={() => (isExpanded = !isExpanded)}
			title={isExpanded ? $LL.collapse() : $LL.pdf.expand()}
		>
			{#if isExpanded}
				<CollapseIcon class="h-5 w-5" />
				<span class="text-xs">{$LL.collapse()}</span>
			{:else}
				<ExpandIcon class="h-5 w-5" />
			{/if}
		</button>

		<div class="flex flex-col gap-2 p-2 pb-0">
			{#if data.invites}
				<div class="shrink-0">
					<MembershipList
						data={data.invites}
						sessionUser={data.sessionUser}
						accepted={false}
						compact={!isExpanded}
					/>
				</div>
			{/if}
			{#key data}
				{#if data.memberships}
					<MembershipList
						data={data.memberships}
						sessionUser={data.sessionUser}
						accepted={true}
						compact={!isExpanded}
						onSelect={handleGroupSelect}
					/>
				{/if}
			{/key}
		</div>
	</div>

	<!-- right column (subpage content, scrollable) -->
	<div class="h-full flex-1 overflow-y-auto">
		{@render children?.()}
	</div>
</div>
