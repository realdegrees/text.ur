<script lang="ts">
	let {
		highlightColor = $bindable('#FFFF00'),
		commentsCount
	}: {
		highlightColor?: string;
		commentsCount: number;
	} = $props();
</script>

<div class="flex flex-col gap-4 rounded-lg border border-gray-200 bg-white p-4">
	<!-- Color picker -->
	<div class="flex flex-col gap-2">
		<label for="highlight-color" class="text-sm font-semibold text-gray-700">
			Highlight Color
		</label>
		<input
			id="highlight-color"
			type="color"
			bind:value={highlightColor}
			class="h-10 w-full cursor-pointer rounded border border-gray-300"
			aria-label="Highlight color"
		/>
	</div>

	<!-- Annotations count -->
	<div class="flex flex-col gap-1 border-t border-gray-200 pt-4">
		<span class="text-xs font-medium text-gray-500">HIGHLIGHTS</span>
		<span class="text-2xl font-bold text-gray-900">{commentsCount}</span>
	</div>
</div>
