<script lang="ts">
	import type { DocumentRead } from '$api/types';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import ChevronDownIcon from '~icons/material-symbols/keyboard-arrow-down';
	import ChevronUpIcon from '~icons/material-symbols/keyboard-arrow-up';
	import CalendarIcon from '~icons/material-symbols/calendar-today-outline';
	import LL from '$i18n/i18n-svelte';
	// Tag display removed per request

	interface Props {
		document: DocumentRead;
	}

	let { document }: Props = $props();

	let isExpanded = $state(false);

	// Format last updated date
	function formatDate(dateString: string | undefined): string {
		if (!dateString) return $LL.relativeTime.never();
		const date = new Date(dateString);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);
		const diffHours = Math.floor(diffMs / 3600000);
		const diffDays = Math.floor(diffMs / 86400000);

		if (diffMins < 1) return $LL.relativeTime.justNow();
		if (diffMins < 60) return $LL.relativeTime.nMinutesAgo({ count: diffMins });
		if (diffHours < 24) return $LL.relativeTime.nHoursAgo({ count: diffHours });
		if (diffDays < 7) return $LL.relativeTime.nDaysAgo({ count: diffDays });

		return date.toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	let hasContent = $derived(document.description && document.description.trim().length > 0);
</script>

{#if hasContent}
	<div class=" bg-inset">
		<!-- Header with collapse toggle -->
		<button
			type="button"
			onclick={() => (isExpanded = !isExpanded)}
			class="doc-info-header flex w-full items-center justify-between border-b border-text/10 px-3 py-2 transition-colors hover:bg-text/5"
		>
			<div class="flex items-center gap-3">
				<h2 class="text-sm font-semibold text-text/80">{$LL.pdf.documentInfo()}</h2>
				<!-- Last Updated -->
				<div class="flex items-center gap-1.5 text-xs text-text/50">
					<CalendarIcon class="h-3.5 w-3.5" />
					<span>{$LL.memberScore.updatedAgo({ time: formatDate(document.updated_at) })}</span>
				</div>
			</div>
			<div class="flex items-center gap-2">
				{#if isExpanded}
					<ChevronUpIcon class="h-5 w-5 text-text/50" />
				{:else}
					<ChevronDownIcon class="h-5 w-5 text-text/50" />
				{/if}
			</div>
		</button>

		<!-- Content (collapsible) -->
		{#if isExpanded}
			<div class="flex flex-col gap-4 px-3 py-2">
				<!-- Description -->
				{#if document.description && document.description.trim().length > 0}
					<div class="flex flex-col gap-2">
						<MarkdownRenderer content={document.description} class="text-sm text-text/80" />
					</div>
				{/if}

				<!-- Tags removed according to request -->
			</div>
		{/if}
	</div>
{/if}
