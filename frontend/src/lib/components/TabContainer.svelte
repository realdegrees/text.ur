<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		tabs,
		activeTab = 0
	}: { tabs: { label: string; snippet: Snippet<[]> }[]; activeTab?: number } = $props();

	function selectTab(index: number) {
		activeTab = index;
	}
</script>

<div class="tab-container w-full">
	{#if tabs.length > 1}
		<div class="tab-header relative flex border-b border-text/50 justify-around">
			<div
				class="tab-indicator absolute bottom-0 h-1 bg-primary transition-all duration-300"
				style="width: calc(100% / {tabs.length}); transform: translateX(calc(100% * {activeTab})); left: 0;"
			></div>
			{#each tabs as tab, index (index)}
				{#if tab}
					<button
						class="tab-item relative flex-1 text-center px-4 py-2 transition-colors hover:bg-primary/40"
						onclick={() => selectTab(index)}
					>
						{tab.label}
					</button>
				{/if}
			{/each}
		</div>
	{/if}
	<div class="tab-content p-4">
		{@render tabs[activeTab]?.snippet()}
	</div>
</div>
