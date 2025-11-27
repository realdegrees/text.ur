<script lang="ts" generics="Option extends unknown">
	import { onMount, tick, type Component } from 'svelte';
	import Loading from '~icons/svg-spinners/90-ring-with-bg';
	import Submit from '~icons/material-symbols/filter-arrow-right';
	import EyeOpen from '~icons/mdi/eye';
	import EyeClosed from '~icons/mdi/eye-off';
	import type { SVGAttributes } from 'svelte/elements';

	const defaults = {
		placeholder: '',
		noResultsHint: '❌ No results found',
		// eslint-disable-next-line @typescript-eslint/no-unused-vars
		fullMatchHint: (selected?: Option) => '✅'
	};

	let {
		debounceMs = 500,
		fetchOptions,
		stringify,
		config,
		value = $bindable<string>(''),
		selected = $bindable<Option | undefined>(),
		onSubmit,
		hideHintsOnBlur: hideOnBlur = false,
		showSubmitButton = false,
		hidden = false,
		Icon = undefined,
		name,
		label,
		required = false
	}: {
		debounceMs?: number;
		fetchOptions?: (search: string) => Promise<Option[]>;
		selected?: Option;
		value?: string;
		showSubmitButton?: boolean;
		hideHintsOnBlur?: boolean;
		hidden?: boolean;
		config?: {
			placeholder?: string;
			noResultsHint?: string;
		};
		Icon?: Component<SVGAttributes<SVGElement>>;
		stringify?: {
			option: Option extends string ? never : (item: Option) => string;
			hint?: Option extends string ? never : (item: Option) => string;
		};
		onSubmit?: (query: string, option: Option | undefined) => void;
		name?: string;
		label?: string;
		required?: boolean;
	} = $props();

	if (hidden && fetchOptions) {
		console.warn(
			`[autoCompleteInput] The 'hidden' prop is enabled, which disables autocomplete functionality. The 'fetchOptions' prop will be ignored.`
		);
	}

	type OptionTransformMap = { value: Option; text: string }[];

	let options = $state<OptionTransformMap>([]);
	let selectedIndex = $state(0);
	let focused = $state(false);
	let debouncing = $state(false);
	let debounceTimeout: NodeJS.Timeout;
	let searchElement = $state<HTMLDivElement | null>(null);
	let showPassword = $state(false);

	const effectiveFetchOptions = $derived(hidden ? undefined : fetchOptions);

	let { prefix, suffix } = $derived<{ prefix: string; suffix: string }>(
		(() => {
			const placeholder = config?.placeholder ?? defaults.placeholder;
			const noResultsHint = config?.noResultsHint ?? defaults.noResultsHint;
			const fullMatchHint = stringify?.hint?.(selected) ?? defaults.fullMatchHint?.(selected);
			const selectedOptionText: string | undefined = options[selectedIndex]?.text;

			if (!effectiveFetchOptions) return { prefix: '', suffix: '' };
			if (hideOnBlur && !focused) return { prefix: '', suffix: value.length ? '' : placeholder };
			if (!value.length) return { prefix: '', suffix: placeholder };
			if (
				typeof selectedOptionText === 'string' &&
				selectedOptionText.toLowerCase() === value.toLowerCase()
			) {
				return { prefix: '', suffix: fullMatchHint };
			}
			if (options[selectedIndex] && typeof selectedOptionText === 'string') {
				const split = selectedOptionText.toLowerCase().split(value.toLocaleLowerCase());
				const prefix = split.length > 1 ? selectedOptionText.slice(0, split[0].length) : '';
				const suffix =
					selectedOptionText.slice(prefix.length + value.length) +
					(stringify?.hint?.(options[selectedIndex]?.value) ?? '');
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

	// Sync value to contenteditable div when value changes from outside
	$effect(() => {
		if (searchElement && searchElement.textContent !== value) {
			searchElement.textContent = value;
		}
	});

	function onInput() {
		clearTimeout(debounceTimeout);
		debouncing = !!effectiveFetchOptions;
		selectedIndex = 0;

		if (!effectiveFetchOptions) return;

		debounceTimeout = setTimeout(async () => {
			if (!value.length) {
				debouncing = false;
				return;
			}

			options =
				value.length && effectiveFetchOptions
					? ((await effectiveFetchOptions(value.replace(/\u00A0/g, ' '))) as Option[])?.map(
							(o) => ({
								value: o,
								text: stringify?.option?.(o) ?? (o as unknown as string)
							})
						)
					: [];
			debouncing = false;
		}, debounceMs);
	}

	async function navigate(event: KeyboardEvent) {
		if (!focused) return;

		// Handle Enter key for all input types (including password fields without autocomplete)
		if (event.key === 'Enter') {
			event.preventDefault();

			// If autocomplete is active and there's a suggestion to complete, complete it first
			if (effectiveFetchOptions && options[selectedIndex] && !selected) {
				await doComplete();
				return;
			}

			// Otherwise, submit
			if (onSubmit) {
				onSubmit(value, selected);
			} else {
				// Submit the parent form if no onSubmit handler is provided
				const form = searchElement?.closest('form');
				if (form) {
					form.requestSubmit();
				}
			}
			return;
		}

		if (!effectiveFetchOptions) {
			return;
		}

		switch (event.key) {
			case 'ArrowDown':
				event.preventDefault();
				if (!options.length) break;
				selectedIndex = (selectedIndex + 1) % options.length;
				break;
			case 'ArrowUp':
				event.preventDefault();
				if (!options.length) break;
				selectedIndex = (selectedIndex - 1 + options.length) % options.length;
				break;
			case 'Tab':
				event.preventDefault();
				if (options[selectedIndex]) {
					doComplete();
				}
				break;
		}
	}

	async function doComplete() {
		value = options[selectedIndex]?.text ?? value;

		await tick();
		if (searchElement) {
			// TODO: this is just a hack, need to fix
			// eslint-disable-next-line svelte/no-dom-manipulating
			searchElement.textContent = value;
		}
		await tick();
		const range = document.createRange();
		const selection = window.getSelection();
		range.selectNodeContents(searchElement!);
		range.collapse(false);
		selection?.removeAllRanges();
		selection?.addRange(range);
		searchElement!.focus();
	}

	onMount(() => {
		if (effectiveFetchOptions) onInput();
	});
</script>

<svelte:window on:keydown={navigate} />

<div>
	{#if label}
		<label for={name} class="mb-2 block font-medium text-text">
			{label} <span class="text-red-600 dark:text-red-400">{required ? '*' : ''}</span>
		</label>
	{/if}
	<div
		class="flex w-full flex-row items-center gap-2 rounded border border-text/20 bg-background px-2 py-2.5 text-sm text-text focus-within:border-primary focus-within:ring-1 focus-within:ring-primary"
	>
		{#if Icon}
			<div class="text-muted">
				{#if debouncing}
					<Loading class="size-5 animate-spin" />
				{:else}
					<Icon class="size-5" />
				{/if}
			</div>
		{/if}

		<!-- hidden input to submit the value -->
		<input class="hidden" type="hidden" {name} bind:value />

		<div
			role="textbox"
			aria-multiline="false"
			tabindex="0"
			spellcheck="false"
			data-suffix={suffix}
			data-affix={prefix}
			class="w-full overflow-hidden whitespace-nowrap before:opacity-40 before:content-[attr(data-affix)] after:opacity-40 after:content-[attr(data-suffix)] focus:outline-none"
			style={hidden && !showPassword ? '-webkit-text-security: disc; text-security: disc;' : ''}
			contenteditable="true"
			bind:this={searchElement}
			onfocus={() => (focused = true)}
			onblur={() => (focused = false)}
			oninput={() => {
				if (searchElement) {
					const brElements = searchElement.querySelectorAll('br');
					if (brElements.length > 0) {
						brElements.forEach((br) => br.remove());
						if (searchElement.textContent === '') {
							value = '';
						}
					}
					value = searchElement.textContent || '';
				}
				onInput();
			}}
			onkeydown={(e) => {
				if (e.key === 'ArrowRight' && effectiveFetchOptions && options[selectedIndex]) {
					e.preventDefault();
					doComplete();
					return;
				}
			}}
		></div>

		{#if hidden}
			<button
				type="button"
				class="text-muted flex items-center justify-center transition hover:cursor-pointer hover:text-text"
				onclick={() => {
					showPassword = !showPassword;
					// focus the input
					searchElement?.focus();
				}}
				aria-label={showPassword ? 'Hide password' : 'Show password'}
				tabindex="-1"
			>
				{#if showPassword}
					<EyeOpen class="size-5" />
				{:else}
					<EyeClosed class="size-5" />
				{/if}
			</button>
		{/if}

		{#if showSubmitButton}
			<button
				type="button"
				class="text-primary-foreground ml-2 flex size-8 items-center justify-center rounded-md bg-primary transition hover:opacity-90"
				onclick={(e) => {
					e.preventDefault();
					onSubmit?.(value, selected);
				}}
			>
				<Submit class="size-5" />
			</button>
		{/if}
	</div>
</div>
