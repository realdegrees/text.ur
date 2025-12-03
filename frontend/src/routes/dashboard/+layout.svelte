<script lang="ts">
	import { goto } from '$app/navigation';
	import MembershipList from '$lib/components/membershipList.svelte';
	import { page } from '$app/state';

	let { data, children } = $props();

	let isExpanded = $derived(!page.params.groupid);
	let isHovering = $state(false);


	// Sidebar should be expanded if: isExpanded is true OR user is hovering
	const shouldShowExpanded = $derived(isExpanded || isHovering);

	function handleGroupSelect(membership: any) {
		const currentPage = page.url.pathname.split('/').pop();
		goto(
			`/dashboard/groups/${membership.group.id}/${(page.params.groupid && currentPage) || 'documents'}`
		);
		// Collapse sidebar after selection
		isExpanded = false;
	}
</script>

<div class="flex w-full grow">
	<!-- left column (groups) -->
	<div
		role="navigation"
		aria-label="Groups sidebar"
		class="no-scrollbar border-text/10 bg-inset flex h-full shrink-0 flex-col gap-2 overflow-y-auto overflow-x-hidden border-r p-2 pb-0 transition-all duration-200"
		class:w-12={!shouldShowExpanded}
		class:w-[200px]={shouldShowExpanded}
		class:sm:w-[200px]={shouldShowExpanded}
		class:md:w-[300px]={shouldShowExpanded}
		class:lg:w-[400px]={shouldShowExpanded}
		onmouseenter={() => (isHovering = true)}
		onmouseleave={() => (isHovering = false)}
	>
		{#if data.invites}
			<div class="shrink-0">
				<MembershipList
					data={data.invites}
					sessionUser={data.sessionUser}
					accepted={false}
					compact={!shouldShowExpanded}
				/>
			</div>
		{/if}
		{#key data}
			{#if data.memberships}
				<MembershipList
					data={data.memberships}
					sessionUser={data.sessionUser}
					accepted={true}
					compact={!shouldShowExpanded}
					onSelect={handleGroupSelect}
				/>
			{/if}
		{/key}
	</div>

	<!-- right column (subpage content, scrollable) -->
	<div class="h-full flex-1 overflow-y-auto p-4">
		{@render children?.()}
	</div>
</div>
