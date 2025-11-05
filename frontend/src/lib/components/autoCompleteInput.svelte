<script lang="ts" generics="Option extends unknown">
	import { onMount, tick, type Component } from 'svelte';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import Submit from '~icons/material-symbols/filter-arrow-right';
	import Search from '~icons/material-symbols/search-rounded';
	import type { SVGAttributes } from 'svelte/elements';

	const defaults = {
		placeholder: 'Search...',
		noResultsHint: ' ❌ No results found',
		fullMatchHint: ' ✅'
	};

	let {
		debounceMs = 500,
		fetchOptions,
		stringifyOption,
		config,
		value = $bindable<string>(''),
		selected = $bindable<Option | undefined>(),
		onSubmit,
		hideHintsOnBlur: hideOnBlur = false,
		hideIcon = false,
		hideSubmit = false,
		Icon = Search
	}: {
		debounceMs?: number;
		fetchOptions?: (search: string) => Promise<Option[]>;
		selected?: Option;
		value?: string;
		hideIcon?: boolean;
		hideSubmit?: boolean;
		hideHintsOnBlur?: boolean;
		config?: {
			placeholder?: string;
			noResultsHint?: string;
			fullMatchHint?: string;
		};
		Icon?: Component<SVGAttributes<SVGElement>>;
		stringifyOption?: Option extends string ? never : (item: Option) => string;
		onSubmit?: (query: string, option: Option | undefined) => void;
	} = $props();

	type OptionTransformMap = { value: Option; text: string }[];

	let options = $state<OptionTransformMap>([]);
	let selectedIndex = $state(0);
	let focused = $state(false);
	let debouncing = $state(false);
	let debounceTimeout: NodeJS.Timeout;
	let searchElement: HTMLDivElement;
	let { prefix, suffix } = $derived(
		(() => {
			const placeholder = config?.placeholder ?? defaults.placeholder;
			const noResultsHint = config?.noResultsHint ?? defaults.noResultsHint;
			const fullMatchHint = config?.fullMatchHint ?? defaults.fullMatchHint;
			const selectedOptionText: string | undefined = options[selectedIndex]?.text;

			if (hideOnBlur && !focused) return { prefix: '', suffix: value.length ? '' : placeholder };
			if (!value.length) return { prefix: '', suffix: placeholder };
			if (selectedOptionText?.toLowerCase() === value.toLowerCase())
				return { prefix: '', suffix: fullMatchHint };
			if (options[selectedIndex]) {
				const split = selectedOptionText.toLowerCase().split(value.toLocaleLowerCase());
				const prefix = split.length > 1 ? selectedOptionText.slice(0, split[0].length) : '';
				const suffix = selectedOptionText.slice(prefix.length + value.length);

				return {
					prefix,
					suffix: suffix + ` ⇥ Select${options.length > 1 ? ' - ⇅ Cycle' : ''}`
				};
			}
			return debouncing ? { prefix: '', suffix: '' } : { prefix: '', suffix: noResultsHint };
		})()
	);

	$effect(() => {
		const option = options[selectedIndex] ? options[selectedIndex] : undefined;
		if (!option || (option && option.text !== value)) {
			selected = undefined;
			return;
		}
		selected = option.value;
	});

	function onInput() {
		clearTimeout(debounceTimeout);
		debouncing = !!fetchOptions;
		selectedIndex = 0;

		debounceTimeout = setTimeout(
			async () => {
				if (!value.length) {
					debouncing = false;
					return;
				}

				options =
					value.length && fetchOptions
						? ((await fetchOptions(value.replace(/\u00A0/g, ' '))) as Option[])?.map((o) => ({
								value: o,
								text: stringifyOption?.(o) ?? (o as unknown as string)
							}))
						: [];
				debouncing = false;
			},
			fetchOptions ? debounceMs : 0
		);
	}

	async function navigate(event: KeyboardEvent) {
		if (!focused) return;

		switch (event.key) {
			case 'ArrowDown':
				event.preventDefault();
				if (!options.length) break;

				selectedIndex = selectedIndex + 1;
				if (selectedIndex >= options.length) selectedIndex = 0;
				break;
			case 'ArrowUp':
				event.preventDefault();
				if (!options.length) break;

				selectedIndex = selectedIndex - 1;
				if (selectedIndex < 0) selectedIndex = options.length - 1;
				break;
			case 'Enter':
				event.preventDefault();
				selectedIndex = options.findIndex((o) => o.text === value);
				onSubmit?.(value, selected);
				break;
		}
	}

	async function doComplete() {
		value = options[selectedIndex]?.text ?? value;

		await tick();
		const range = document.createRange();
		const selection = window.getSelection();
		range.selectNodeContents(searchElement);
		range.collapse(false);
		selection?.removeAllRanges();
		selection?.addRange(range);
		searchElement.focus();
	}

	onMount(() => {
		if (fetchOptions) {
			onInput();
		}
	});
</script>

<svelte:window on:keydown={navigate} />
<div class="text-md card-black flex w-full flex-row items-center justify-start bg-accent p-1!">
	{#if !hideIcon}
		<div class="mr-2">
			{#if debouncing}
				<Loading class="m-auto" />
			{:else}
				<Icon class="m-auto" />
			{/if}
		</div>
	{/if}

	<div
		role="textbox"
		aria-multiline="false"
		tabindex="-1"
		spellcheck="false"
		data-suffix={suffix}
		data-affix={prefix}
		class:after:animate-pulse={!focused && options[selectedIndex]}
		class:before:animate-pulse={!focused && options[selectedIndex]}
		class="h-full w-full whitespace-pre before:pointer-events-none
			before:opacity-50 before:content-[attr(data-affix)] after:pointer-events-none
			after:opacity-50 after:content-[attr(data-suffix)] focus:outline-none"
		contenteditable="true"
		bind:innerText={value}
		bind:this={searchElement}
		onfocus={() => (focused = true)}
		onblur={() => (focused = false)}
		onsubmit={() => onSubmit?.(value, selected)}
		onkeydown={(event) => {
			if (
				event.key === 'Tab' ||
				event.key === 'ArrowRight' ||
				(!onSubmit && event.key === 'Enter')
			) {
				event.preventDefault();
				doComplete();
			}
		}}
		onchange={onInput}
		oninput={async ({ currentTarget }) => {
			if (currentTarget.innerHTML.includes('<br>')) {
				currentTarget.innerHTML = currentTarget.innerHTML.replace('<br>', '');
				value = currentTarget.innerText;
			}
			onInput();
		}}
	>
		<!--LEAVE EMPTY-->
	</div>
	{#if !hideSubmit}
		<button
			type="button"
			class="confirm w-fit"
			onclick={(e) => {
				e.preventDefault();
				onSubmit?.(value, selected);
			}}
		>
			<Submit class="m-auto" />
		</button>
	{/if}
</div>
