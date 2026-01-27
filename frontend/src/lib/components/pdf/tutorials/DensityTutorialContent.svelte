<script lang="ts">
	import EyeIcon from '~icons/mdi/eye';
	import PinIcon from '~icons/mdi/pin';
</script>

<div class="grid gap-6 sm:grid-cols-2">
	<div>
		<h4 class="mb-2 flex items-center gap-2 font-medium text-primary">
			<EyeIcon class="h-4 w-4" />
			Visibility
		</h4>
		<ul class="ml-1 space-y-1.5 text-sm text-text/80">
			<li class="flex items-start gap-2">
				<span class="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-text/40"></span>
				<span>Click <strong>once</strong> to show only selected comments.</span>
			</li>
			<li class="flex items-start gap-2">
				<span class="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-text/40"></span>
				<span>Click <strong>again</strong> to hide them completely.</span>
			</li>
		</ul>
	</div>

	<div>
		<h4 class="mb-2 flex items-center gap-2 font-medium text-primary">
			<PinIcon class="h-4 w-4" />
			Pinning
		</h4>
		<ul class="ml-1 space-y-1.5 text-sm text-text/80">
			<li class="flex items-start gap-2">
				<span class="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-text/40"></span>
				<span
					>Pin specific <strong>users</strong> or <strong>tags</strong> to keep their threads open.</span
				>
			</li>
			<li class="flex items-start gap-2">
				<span class="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-text/40"></span>
				<span>Combine with visibility filters for custom views.</span>
			</li>
		</ul>
	</div>
</div>

<p class="mt-6 border-t border-text/10 pt-4 text-xs text-text/60">
	<strong>Tip:</strong> You can select multiple users and tags simultaneously to create a customized
	view of the document activity.
</p>
