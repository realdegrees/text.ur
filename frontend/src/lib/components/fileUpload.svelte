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
	class="w-full h-full rounded flex flex-row items-center justify-center
    bg-accent bg-opacity-5 border-dashed hover:animate-pulse border-[.22rem] border-text
    hover:border-solid group"
>
	<label class="w-full h-full group-hover:cursor-pointer">
		<div
			class="flex flex-row group-hover:scale-[98%] transition-all h-full items-center justify-center gap-2"
		>
			{@render children?.()}
		</div>
		<input
			type="file"
			multiple
			class="absolute top-0 left-0 w-0 h-0 opacity-0"
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
