<script lang="ts">
	import SaveIcon from "~icons/material-symbols/save-outline";

	let { data } = $props();
	let group = $derived(data.selectedGroup);
	
	let groupName: string = $state("");
	
	$effect(() => {
		if (group) {
			groupName = group.name;
		}
	});

	async function handleSave(): Promise<void> {
		console.log("Saving settings:", { groupName });
	}
</script>

<div class="flex h-full w-full flex-col gap-4">
	<!-- Settings Form -->
	<div class="flex flex-col gap-6">
		<!-- Group Name -->
		<div class="flex flex-col gap-2">
			<label for="groupName" class="text-sm font-semibold text-text/70">Group Name</label>
			<input
				id="groupName"
				type="text"
				bind:value={groupName}
				class="rounded-md border border-text/20 bg-text/5 px-4 py-2 transition-colors focus:border-text/50 focus:outline-none"
			/>
		</div>

		<!-- Group ID (Read-only) -->
		<div class="flex flex-col gap-2">
			<label for="groupId" class="text-sm font-semibold text-text/70">Group ID</label>
			<input
				id="groupId"
				type="text"
				value={group?.id}
				readonly
				class="rounded-md border border-text/20 bg-text/10 px-4 py-2 font-mono text-sm text-text/70 cursor-not-allowed"
			/>
		</div>

		<!-- Owner (Read-only) -->
		<div class="flex flex-col gap-2">
			<label for="owner" class="text-sm font-semibold text-text/70">Owner</label>
			<input
				id="owner"
				type="text"
				value={group?.owner?.username || "Unknown"}
				readonly
				class="rounded-md border border-text/20 bg-text/10 px-4 py-2 text-text/70 cursor-not-allowed"
			/>
		</div>

		<!-- Save Button -->
		<div class="flex flex-row justify-end gap-2">
			<button
				onclick={handleSave}
				class="flex flex-row items-center gap-2 rounded-md bg-primary px-6 py-2 text-background transition-all hover:bg-primary/80"
			>
				<SaveIcon class="h-5 w-5" />
				<span>Save Changes</span>
			</button>
		</div>

		<!-- Info Message -->
		<div class="rounded-md bg-text/5 p-4">
			<p class="text-sm text-text/70">
				Note: Additional group settings such as permissions management and advanced options will be
				available here in the future.
			</p>
		</div>
	</div>
</div>
