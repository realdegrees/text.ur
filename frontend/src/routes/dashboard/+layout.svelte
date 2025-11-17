<script lang="ts">
	import { goto } from '$app/navigation';
	import MembershipList from '$lib/components/membershipList.svelte';
	import { page } from '$app/state';

	let { data, children } = $props();
</script>

<div class="flex w-full grow">
	<!-- left column (groups) -->
	<div class="flex h-full flex-col gap-2 p-2 pb-0 sm:w-[200px] md:w-[300px] lg:w-[400px]">
		<div class="shrink-0">
			<MembershipList data={data.invites} sessionUser={data.sessionUser!} accepted={false} />
		</div>
		<MembershipList
			data={data.memberships}
			sessionUser={data.sessionUser!}
			accepted={true}
			onSelect={(membership) => {
				const currentPage = page.url.pathname.split('/').pop();
				goto(
					`/dashboard/groups/${membership.group.id}/${(page.params.groupid && currentPage) || 'documents'}`
				);
			}}
		/>
	</div>

	<!-- right column (subpage content, scrollable) -->
	<div class="h-full flex-1 overflow-y-auto p-4">
		{@render children?.()}
	</div>
</div>
