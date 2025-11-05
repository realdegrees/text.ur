<script lang="ts">
	import { notificationStore } from '$lib/stores/notificationStore';
	import { sineInOut } from 'svelte/easing';
	import { fly } from 'svelte/transition';
</script>

<div class="fixed top-24 right-0 z-50 space-y-4">
	{#each $notificationStore as notification (notification.id)}
		{@const borderClass =
			notification.color === 'green'
				? 'border-green-500'
				: notification.color === 'orange'
					? 'border-orange-500'
					: 'border-red-500'}
		{@const textClass =
			notification.color === 'green'
				? 'text-green-500'
				: notification.color === 'orange'
					? 'text-orange-500'
					: 'text-red-500'}
		<div
			class="relative -mr-40 flex cursor-pointer items-center transition-all"
			in:fly={{ x: 80, duration: 200, easing: sineInOut }}
			out:fly={{ x: 80, duration: 200, easing: sineInOut }}
			role="button"
			tabindex="0"
			on:click={() =>
				notificationStore.update((n) => n.filter((item) => item.id !== notification.id))}
			on:keydown={(e) =>
				e.key === 'Enter' || e.key === ' '
					? notificationStore.update((n) => n.filter((item) => item.id !== notification.id))
					: null}
		>
			<div
				class="absolute inset-0 border-2 {borderClass} rounded-l border-r-0"
				aria-hidden="true"
			></div>
			<div
				class="max-w-200 overflow-hidden rounded-l bg-inset p-3 pr-48 text-ellipsis shadow-inner-sym-2"
			>
				<div class="flex items-center">
					<notification.Icon class="aspect-square h-auto w-6 {textClass} mr-2" />
					<p class="font-semibold">{notification.message}</p>
				</div>
			</div>
		</div>
	{/each}
</div>
