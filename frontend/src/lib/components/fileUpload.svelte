<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		value = $bindable<File[]>([]),
		children
	}: {
		value: File[];
		children?: Snippet<[]>;
	} = $props();
</script>

<div
	role="form"
	ondrop={(e) => {
		e.preventDefault();
		if (e.dataTransfer?.items) {
			value = [...e.dataTransfer.items].map((item) => item.getAsFile()).filter((file) => !!file);
		}
	}}
	ondragover={(e) => {
		e.preventDefault();
	}}
	class="bg-opacity-5 group flex h-full w-full flex-row items-center
    justify-center rounded border-[.22rem] border-dashed border-text bg-accent
    hover:animate-pulse hover:border-solid"
>
	<label class="h-full w-full group-hover:cursor-pointer">
		<div
			class="flex h-full flex-row items-center justify-center gap-2 transition-all group-hover:scale-[98%]"
		>
			{@render children?.()}
		</div>
		<input
			type="file"
			multiple
			class="absolute top-0 left-0 h-0 w-0 opacity-0"
			onchange={({ currentTarget }) => {
				const files: File[] = [];
				if (!currentTarget.files?.length) return;

				for (let i = 0; i < currentTarget.files.length; i++) {
					const file = currentTarget.files.item(i);
					if (file) files.push(file);
				}
				value = files;
			}}
		/>
	</label>
</div>
