<script lang="ts">
	import type { Snippet } from 'svelte';
	import { onMount } from 'svelte';

	interface Props {
		speed?: number;
		direction?: 'left' | 'right';
		mode?: 'infinite' | 'bounce';
		bounceDirection?: 'left' | 'right';
		componentClass?: string;
		children?: Snippet<[]>;
	}

	let {
		speed = 50,
		direction = 'left',
		mode = 'infinite',
		bounceDirection = 'left',
		componentClass = '',
		children
	}: Props = $props();

	let containerRef: HTMLDivElement;
	let contentRef: HTMLDivElement;
	let animationId: number | null = null;
	let currentPosition = $state(0);
	let currentDirection = $state(bounceDirection);
	let contentWidth = $state(0);
	let containerWidth = $state(0);
	let copiesNeeded = $state(3);

	onMount(() => {
		updateDimensions();
		startAnimation();

		const resizeObserver = new ResizeObserver(() => {
			updateDimensions();
		});

		if (containerRef) resizeObserver.observe(containerRef);
		if (contentRef) resizeObserver.observe(contentRef);

		return () => {
			stopAnimation();
			resizeObserver.disconnect();
		};
	});

	function updateDimensions(): void {
		if (!contentRef || !containerRef) return;

		contentWidth = contentRef.offsetWidth;
		containerWidth = containerRef.offsetWidth;

		if (mode === 'infinite' && contentWidth > 0) {
			copiesNeeded = Math.max(Math.ceil(containerWidth / contentWidth) + 1, 2);
		}

		if (mode === 'infinite') {
			currentPosition = direction === 'left' ? 0 : -contentWidth;
		} else {
			currentPosition = 0;
		}
	}

	function startAnimation(): void {
		let lastTimestamp = 0;

		const animate = (timestamp: number): void => {
			if (!lastTimestamp) lastTimestamp = timestamp;
			const delta = timestamp - lastTimestamp;
			lastTimestamp = timestamp;

			if (mode === 'infinite') {
				animateInfinite(delta);
			} else {
				animateBounce(delta);
			}

			animationId = requestAnimationFrame(animate);
		};

		animationId = requestAnimationFrame(animate);
	}

	function animateInfinite(delta: number): void {
		const distance = (speed * delta) / 1000;

		if (direction === 'left') {
			currentPosition -= distance;
			if (currentPosition <= -contentWidth) {
				currentPosition += contentWidth;
			}
		} else {
			currentPosition += distance;
			if (currentPosition >= 0) {
				currentPosition -= contentWidth;
			}
		}
	}

	function animateBounce(delta: number): void {
		const distance = (speed * delta) / 1000;
		const maxOffset = Math.max(contentWidth - containerWidth, 0);

		if (currentDirection === 'left') {
			currentPosition -= distance;
			if (currentPosition <= -maxOffset) {
				currentPosition = -maxOffset;
				currentDirection = 'right';
			}
		} else {
			currentPosition += distance;
			if (currentPosition >= 0) {
				currentPosition = 0;
				currentDirection = 'left';
			}
		}
	}

	function stopAnimation(): void {
		if (animationId !== null) {
			cancelAnimationFrame(animationId);
			animationId = null;
		}
	}

	$effect(() => {
		if (mode || direction || speed) {
			stopAnimation();
			updateDimensions();
			startAnimation();
		}
	});
</script>

<div bind:this={containerRef} class="relative w-fit overflow-hidden {componentClass}">
	<div class="inline-flex whitespace-nowrap">
		<div
			bind:this={contentRef}
			class="inline-flex"
			style="transform: translateX({currentPosition}px);"
		>
			{@render children?.()}
		</div>
		{#if mode === 'infinite'}
			{#each Array.from({ length: copiesNeeded }, (_, i) => i) as i (i)}
				<div class="inline-flex" style="transform: translateX({currentPosition}px);">
					{@render children?.()}
				</div>
			{/each}
		{/if}
	</div>
</div>

<style>
	div {
		will-change: transform;
	}
</style>
