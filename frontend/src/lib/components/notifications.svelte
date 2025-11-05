<script lang="ts">
	import { notificationStore } from '$lib/stores/notificationStore';
	import { sineInOut } from 'svelte/easing';
	import { fly } from 'svelte/transition';

	interface ErrorType {
		id: number;
		code: number;
		message: string;
	}
</script>

<div class="fixed z-50 top-24 right-0 space-y-4">
	{#each $notificationStore as notification (notification.id)}
		{@const borderClass = notification.color === 'green' ? 'border-green-500' : notification.color === 'orange' ? 'border-orange-500' : 'border-red-500'}
		{@const textClass = notification.color === 'green' ? 'text-green-500' : notification.color === 'orange' ? 'text-orange-500' : 'text-red-500'}
		<div
			class="relative flex items-center -mr-40 transition-all cursor-pointer"
			in:fly={{ x: 80, duration: 200, easing: sineInOut }}
			out:fly={{ x: 80, duration: 200, easing: sineInOut }}
			role="button"
			tabindex="0"
			on:click={() => notificationStore.update(n => n.filter(item => item.id !== notification.id))}
			on:keydown={(e) => e.key === "Enter" || e.key === " " ? notificationStore.update(n => n.filter(item => item.id !== notification.id)) : null}
		>
			<div
				class="absolute inset-0 border-2 {borderClass} rounded-l border-r-0"
				aria-hidden="true"
			></div>
			<div
				class="bg-inset p-3 rounded-l shadow-inner-sym-2 overflow-hidden text-ellipsis pr-48 max-w-200"
			>
				<div class="flex items-center">
					<notification.Icon class="h-auto w-6 aspect-square {textClass} mr-2" />
					<p class="font-semibold">{notification.message}</p>
				</div>
			</div>
		</div>
	{/each}
</div>
