<script lang="ts">
	import TutorialCard from '$lib/components/common/TutorialCard.svelte';
	import TutorialOverlay from '$lib/components/common/TutorialOverlay.svelte';
	import DensityTutorialContent from './tutorials/DensityTutorialContent.svelte';
	import type { TutorialStep } from '$lib/types/tutorial';

	interface Props {
		isExpanded: boolean;
	}

	let { isExpanded }: Props = $props();

	let isDismissed = $state(false);
	let isOverlayOpen = $state(false);

	const shouldShow = $derived(!isDismissed && isExpanded);

	const tutorialSteps: TutorialStep[] = [
		{
			title: 'Managing High Activity Documents',
			component: DensityTutorialContent,
			media: {
				src: '/images/density-workflow.gif',
				alt: 'Workflow explanation'
			}
		}
	];
</script>

{#if isOverlayOpen}
	<TutorialOverlay steps={tutorialSteps} onClose={() => (isOverlayOpen = false)} />
{/if}

{#if shouldShow}
	<TutorialCard
		title="Tutorials"
		description="Use visibility filters and pins to manage high comment density more effectively."
		previewMedia={{
			src: '/images/density-workflow.gif',
			alt: 'Workflow'
		}}
		onDismiss={() => (isDismissed = true)}
		onClick={() => (isOverlayOpen = true)}
	/>
{/if}
