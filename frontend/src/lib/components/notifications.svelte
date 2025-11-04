<script lang="ts">
	import { notificationStore } from '$lib/notificationStore';
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
		<div
			class="relative flex items-center -mr-40 transition-all"
			in:fly={{ x: 80, duration: 200, easing: sineInOut }}
			out:fly={{ x: 80, duration: 200, easing: sineInOut }}
		>
			<div
				class="absolute inset-0 border-2 border-{notification.color}-500 rounded-l border-r-0"
				aria-hidden="true"
			></div>
			<div
				class="bg-accent p-3 rounded-l shadow-inner-sym-2 overflow-hidden text-ellipsis pr-48 max-w-200"
			>
				<div class="flex items-center">
					<notification.Icon class="h-auto w-6 aspect-square text-{notification.color}-500 mr-2" />
					<p class="font-semibold">{notification.message}</p>
				</div>
			</div>
		</div>
	{/each}
</div>
