<script lang="ts">
	import type { TextLayerItem } from '$types/pdf';

	interface Props {
		textLayerRef?: HTMLDivElement | null;
		textLayerItems: TextLayerItem[];
		width: number;
		height: number;
		onTextSelection?: () => void;
		onMouseMove?: (event: MouseEvent) => void;
		onMouseLeave?: () => void;
	}

	let {
		textLayerRef = $bindable(null),
		textLayerItems = [],
		width,
		height,
		onTextSelection = () => {},
		onMouseMove = () => {},
		onMouseLeave = () => {}
	}: Props = $props();
</script>

<div
	bind:this={textLayerRef}
	class="text-layer pointer-events-auto absolute left-0 top-0"
	style:width="{width}px"
	style:height="{height}px"
	onmouseup={onTextSelection}
	onmousemove={onMouseMove}
	onmouseleave={onMouseLeave}
	role="textbox"
	tabindex="0"
	aria-label="PDF text content"
>
	{#each textLayerItems as item (item.id)}
		<div
			class="pointer-events-auto absolute origin-top-left cursor-text select-text whitespace-pre text-transparent"
			style:left="{item.left}px"
			style:top="{item.top}px"
			style:font-size="{item.fontSize}px"
			style:font-family={item.fontFamily}
			style:transform="rotate({item.angle}rad)"
		>
			{item.text}
		</div>
	{/each}
</div>

<style>
	.text-layer {
		line-height: 1;
	}

	.text-layer :global(::selection) {
		background: rgba(0, 123, 255, 0.3);
	}
</style>
