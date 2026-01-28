<script lang="ts">
	import CloseIcon from '~icons/material-symbols/close';
	import ExpandIcon from '~icons/material-symbols/open-in-full';
	import { slide } from 'svelte/transition';
	import type { TutorialMedia } from '$lib/types/tutorial';

	interface Props {
		title: string;
		description: string;
		previewMedia?: TutorialMedia;
		onDismiss?: () => void;
		onClick?: () => void;
	}

	let { title, description, previewMedia, onDismiss, onClick }: Props = $props();

	let imageError = $state(false);
</script>

<div class="mx-2 mb-4 w-full rounded-md bg-blue-500/10 p-3" transition:slide>
	<div class="mb-2 flex items-center justify-between">
		<span class="text-xs font-medium text-blue-600 dark:text-blue-400">{title}</span>
		{#if onDismiss}
			<button
				class="text-text/50 hover:text-text"
				onclick={(e) => {
					e.stopPropagation();
					onDismiss();
				}}
				title="Dismiss"
			>
				<CloseIcon class="h-4 w-4" />
			</button>
		{/if}
	</div>

	{#if previewMedia}
		<div
			class="group relative mb-2 aspect-video w-full overflow-hidden rounded bg-black/10 dark:bg-white/10"
		>
			{#if !imageError}
				<button
					class="relative block h-full w-full cursor-pointer"
					onclick={onClick}
					title="Click to expand"
				>
					<img
						src={previewMedia.src}
						alt={previewMedia.alt}
						class="h-full w-full object-cover"
						onerror={() => (imageError = true)}
					/>
					<div
						class="absolute inset-0 flex items-center justify-center bg-black/0 transition-colors group-hover:bg-black/20"
					>
						<ExpandIcon
							class="h-8 w-8 text-white opacity-0 drop-shadow-md transition-opacity group-hover:opacity-100"
						/>
					</div>
				</button>
			{:else}
				<div class="flex h-full w-full items-center justify-center text-[10px] text-text/50">
					Media Placeholder
				</div>
			{/if}
		</div>
	{/if}

	<p class="text-[11px] leading-tight text-text/70">
		{description}
	</p>
</div>
