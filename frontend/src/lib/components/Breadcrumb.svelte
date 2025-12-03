<script lang="ts">
	import { page } from '$app/stores';
	import ChevronRight from '~icons/material-symbols/chevron-right';
	import type { BreadcrumbItem } from '$types/breadcrumb';

	// Read breadcrumbs from current page data
	const breadcrumbs = $derived($page.data.breadcrumbs as BreadcrumbItem[] | undefined);
</script>

{#if breadcrumbs && breadcrumbs.length > 0}
	<nav class="text-md flex items-center gap-2">
		{#each breadcrumbs as crumb, i (crumb)}
			{#if i > 0}
				<ChevronRight class="h-4 w-4 text-text/30" />
			{/if}

			{#if crumb.href}
				<a href={crumb.href} class="text-text/70 transition-colors hover:text-text">
					{crumb.label}
				</a>
			{:else}
				<span class="font-medium text-text">
					{crumb.label}
				</span>
			{/if}
		{/each}
	</nav>
{/if}
