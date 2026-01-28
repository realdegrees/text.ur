<script lang="ts">
	import CloseIcon from '~icons/material-symbols/close';
	import ArrowBackIcon from '~icons/material-symbols/arrow-back';
	import ArrowForwardIcon from '~icons/material-symbols/arrow-forward';
	import { fade } from 'svelte/transition';
	import type { TutorialStep } from '$lib/types/tutorial';

	/**
	 * Tutorial overlay modal for multi-step guides.
	 */
	interface Props {
		steps: TutorialStep[];
		onClose: () => void;
		initialStepIndex?: number;
	}

	let { steps, onClose, initialStepIndex = 0 }: Props = $props();

	let currentStepIndex: number = $state(initialStepIndex);
	let currentStep: TutorialStep = $derived(steps[currentStepIndex]);

	/**
	 * Move to the next tutorial step.
	 */
	function nextStep(): void {
		if (currentStepIndex < steps.length - 1) {
			currentStepIndex++;
		}
	}

	/**
	 * Move to the previous tutorial step.
	 */
	function prevStep(): void {
		if (currentStepIndex > 0) {
			currentStepIndex--;
		}
	}

	/**
	 * Handle keyboard navigation and close.
	 */
	function handleKeydown(event: KeyboardEvent): void {
		if (event.key === 'Escape') {
			onClose();
		} else if (event.key === 'ArrowRight') {
			nextStep();
		} else if (event.key === 'ArrowLeft') {
			prevStep();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div
	class="fixed inset-0 z-100 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm sm:p-8"
	transition:fade={{ duration: 200 }}
	onclick={onClose}
	role="button"
	tabindex="0"
	onkeydown={(e) => e.key === 'Enter' && onClose()}
>
	<div
		class="relative flex max-h-[90vh] w-full max-w-6xl flex-col overflow-hidden rounded-xl bg-background shadow-2xl ring-1 ring-white/10"
		onclick={(e) => e.stopPropagation()}
		role="presentation"
	>
		<!-- Header / Navigation Bar -->
		<div
			class="flex shrink-0 items-center justify-between gap-4 border-b border-text/10 bg-background px-6 py-4"
		>
			<div class="flex items-center gap-2">
				<button
					class="rounded-full p-2 text-text/60 transition-colors hover:bg-text/10 hover:text-text disabled:opacity-30 disabled:hover:bg-transparent"
					onclick={prevStep}
					disabled={currentStepIndex === 0}
					title="Previous step"
				>
					<ArrowBackIcon class="h-5 w-5" />
				</button>
			</div>

			<!-- Step Titles / Indicators -->
			<div class="no-scrollbar flex flex-1 justify-center gap-2 overflow-x-auto">
				{#each steps as step, i (i)}
					<button
						class="rounded-md px-3 py-1.5 text-sm font-medium whitespace-nowrap transition-all {i ===
						currentStepIndex
							? 'bg-text/5 text-text shadow-sm ring-1 ring-text/10'
							: 'text-text/50 hover:bg-text/5 hover:text-text/80'}"
						onclick={() => (currentStepIndex = i)}
					>
						{step.title}
					</button>
				{/each}
			</div>

			<div class="flex items-center gap-2">
				<button
					class="rounded-full p-2 text-text/60 transition-colors hover:bg-text/10 hover:text-text disabled:opacity-30 disabled:hover:bg-transparent"
					onclick={nextStep}
					disabled={currentStepIndex === steps.length - 1}
					title="Next step"
				>
					<ArrowForwardIcon class="h-5 w-5" />
				</button>
				<div class="mx-2 h-6 w-px bg-text/10"></div>
				<button
					class="rounded-full p-2 text-text/60 transition-colors hover:bg-red-500/10 hover:text-red-600"
					onclick={onClose}
					title="Close tutorial"
				>
					<CloseIcon class="h-5 w-5" />
				</button>
			</div>
		</div>

		<!-- Media Section -->
		{#if currentStep.media}
			<div class="flex min-h-0 flex-1 items-center justify-center bg-black/5 dark:bg-white/5">
				<img
					src={currentStep.media.src}
					alt={currentStep.media.alt}
					class="max-h-[60vh] w-full object-contain"
				/>
			</div>
		{/if}

		<!-- Content Section -->
		<div class="shrink-0 bg-background p-6 text-text">
			<!-- Note: Title is now in the header navigation -->

			{#if currentStep.component}
				{@const StepComponent = currentStep.component}
				<StepComponent {...currentStep.componentProps} />
			{:else if currentStep.description}
				<p class="text-sm text-text/80">{currentStep.description}</p>
			{/if}
		</div>
	</div>
</div>
