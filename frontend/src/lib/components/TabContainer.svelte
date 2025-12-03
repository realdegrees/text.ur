<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		tabs,
		activeTab = 0,
		variant = 'default'
	}: {
		tabs: { label: string; snippet: Snippet<[]> }[];
		activeTab?: number;
		variant?: 'default' | 'compact';
	} = $props();

	function selectTab(index: number) {
		activeTab = index;
	}

	const isCompact = $derived(variant === 'compact');
</script>

<div class="tab-container w-full">
	{#if tabs.length > 1}
		<div
			class="tab-header relative flex border-b border-text/50"
			class:justify-around={!isCompact}
			class:justify-start={isCompact}
		>
			<div
				class="tab-indicator absolute bottom-0 h-1 bg-primary transition-all duration-300"
				style="width: {isCompact
					? 'auto'
					: `calc(100% / ${tabs.length})`}; transform: translateX(calc({isCompact
					? '0px'
					: `100% * ${activeTab}`})); left: 0;"
			></div>
			{#each tabs as tab, index (index)}
				{#if tab}
					<button
						class="tab-item relative transition-colors hover:bg-primary/40"
						class:flex-1={!isCompact}
						class:px-4={!isCompact}
						class:py-2={!isCompact}
						class:px-2={isCompact}
						class:py-1={isCompact}
						class:text-center={!isCompact}
						class:text-xs={isCompact}
						class:rounded-t={isCompact}
						class:bg-text-opacity-30={isCompact && activeTab === index}
						onclick={() => selectTab(index)}
					>
						{tab.label}
					</button>
				{/if}
			{/each}
		</div>
	{/if}
	<div class="tab-content" class:p-4={!isCompact} class:p-2={isCompact}>
		{@render tabs[activeTab]?.snippet()}
	</div>
</div>
