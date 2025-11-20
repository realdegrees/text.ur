<script lang="ts">
	let {
		onDragStart = () => {},
		onDragMove = () => {},
		onDragEnd = () => {},
		isDragging = $bindable(false)
	}: {
		onDragStart?: () => void;
		onDragMove?: (deltaX: number) => void;
		onDragEnd?: () => void;
		isDragging?: boolean;
	} = $props();

	let isHovered = $state(false);
	let mouseY = $state(0);
	let dividerRef: HTMLDivElement | null = $state(null);

	function handleMouseMove(e: MouseEvent) {
		if (!dividerRef) return;
		const rect = dividerRef.getBoundingClientRect();
		mouseY = e.clientY - rect.top;
	}

	function handleMouseDown(e: MouseEvent) {
		isDragging = true;
		e.preventDefault();

		const startX = e.clientX;
		onDragStart();

		function handleMouseMoveWhileDragging(moveEvent: MouseEvent) {
			const deltaX = moveEvent.clientX - startX;
			onDragMove(deltaX);

			// Update handle position while dragging
			if (dividerRef) {
				const rect = dividerRef.getBoundingClientRect();
				mouseY = moveEvent.clientY - rect.top;
			}
		}

		function handleMouseUp() {
			isDragging = false;
			onDragEnd();
			document.removeEventListener('mousemove', handleMouseMoveWhileDragging);
			document.removeEventListener('mouseup', handleMouseUp);
		}

		document.addEventListener('mousemove', handleMouseMoveWhileDragging);
		document.addEventListener('mouseup', handleMouseUp);
	}
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div
	bind:this={dividerRef}
	class="sticky top-0 w-1 self-stretch bg-text/20 transition-colors hover:bg-primary/50 active:bg-primary shrink-0"
	class:bg-primary={isDragging}
	class:cursor-grab={isHovered && !isDragging}
	class:cursor-grabbing={isDragging}
	onmousedown={handleMouseDown}
	onmouseenter={() => (isHovered = true)}
	onmouseleave={() => (isHovered = false)}
	onmousemove={handleMouseMove}
	role="separator"
	aria-orientation="vertical"
	aria-label="Resize sidebar"
	style="min-height: 100vh;"
>
	{#if (isHovered || isDragging)}
		<!-- Top circle with left chevron -->
		<div
			class="absolute left-1/2 -translate-x-1/2 w-6 h-6 bg-primary rounded-full shadow-lg flex items-center justify-center transition-opacity"
			style="top: {mouseY - 45}px;"
			role="presentation"
		>
			<svg
				class="w-3 h-3 text-white"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="3"
					d="M15 19l-7-7 7-7"
				/>
			</svg>
		</div>


		<!-- Middle invisible hover target (improves hover detection) -->
		<div
			class="absolute left-1/2 -translate-x-1/2 w-14 h-14 bg-transparent rounded-full pointer-events-auto transition-opacity"
			style="top: {mouseY - 15}px; opacity: 0;"
			role="presentation"
			onmouseenter={() => (isHovered = true)}
			onmouseleave={() => (isHovered = false)}
		></div>

		<!-- Bottom circle with right chevron -->
		<div
			class="absolute left-1/2 -translate-x-1/2 w-6 h-6 bg-primary rounded-full shadow-lg flex items-center justify-center transition-opacity"
			style="top: {mouseY + 15}px;"
			role="presentation"
		>
			<svg
				class="w-3 h-3 text-white"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="3"
					d="M9 5l7 7-7 7"
				/>
			</svg>
		</div>
	{/if}
</div>
