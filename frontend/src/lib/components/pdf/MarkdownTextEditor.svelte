<script lang="ts">
	import { onMount } from 'svelte';
	import DOMPurify from 'dompurify';
	import MarkdownRenderer from '$lib/components/MarkdownRenderer.svelte';
	import HelpIcon from '~icons/material-symbols/help-outline';

	interface Props {
		value: string;
		placeholder?: string;
		rows?: number;
		disabled?: boolean;
		autofocus?: boolean;
		maxCommentLength?: number;
		onchange?: (value: string) => void;
		onkeydown?: (e: KeyboardEvent) => void;
		onblur?: (e: FocusEvent) => void;
	}

	let {
		value = $bindable(''),
		placeholder = 'Write something...',
		rows = 3,
		disabled = false,
		autofocus = false,
		maxCommentLength = 2000,
		onchange,
		onkeydown,
		onblur
	}: Props = $props();

	let textareaRef: HTMLTextAreaElement | null = $state(null);
	let mode = $state<'write' | 'preview'>('write');
	let showHelpTooltip = $state(false);

	// Size classes
	let sizeClasses = $derived({
		text: 'text-sm',
		padding: 'p-2',
		iconSize: 'h-3.5 w-3.5',
		buttonPadding: 'p-1'
	});

	// Current number of characters in the editor
	let charCount: number = $state(0);

	const handleInput = (e: Event): void => {
		const target = e.target as HTMLTextAreaElement;
		// Allow markdown syntax but sanitize any HTML
		const sanitized = DOMPurify.sanitize(target.value, {
			ALLOWED_TAGS: [], // Strip all HTML tags, keep plain text with markdown
			ALLOWED_ATTR: []
		});
		value = sanitized;
		onchange?.(sanitized);
		// Update character count for the UI
		charCount = sanitized.length;
	};

	const handleKeydown = (e: KeyboardEvent): void => {
		e.stopPropagation(); // Prevent parent handlers from capturing
		onkeydown?.(e);
	};

	onMount(() => {
		if (autofocus && textareaRef) {
			textareaRef.focus();
		}
	});

	// Re-focus when autofocus prop changes to true
	$effect(() => {
		if (autofocus && textareaRef) {
			textareaRef.focus();
		}
	});

	// Auto-resize textarea based on content
	$effect(() => {
		// Depend on value to trigger resize when content changes
		void value;
		charCount = value ? value.length : 0;
		if (textareaRef && mode === 'write') {
			// Reset height to auto to get the correct scrollHeight
			textareaRef.style.height = 'auto';
			// Set height to scrollHeight (constrained by max-height in CSS)
			textareaRef.style.height = `${textareaRef.scrollHeight}px`;
		}
	});
</script>

<div
	class="relative flex flex-col rounded border border-text/20 bg-inset focus-within:border-primary"
>
	<!-- Mode Toggle + Toolbar -->
	<div class="flex items-center justify-between gap-2 border-b border-text/10 px-2 py-1">
		<!-- Mode Toggle -->
		<div class="flex gap-0.5 rounded bg-background p-0.5">
			<button
				type="button"
				class="rounded px-2 py-0.5 text-xs transition-colors {mode === 'write'
					? 'bg-primary/20 text-primary'
					: 'text-text/50 hover:text-text/70'}"
				onclick={() => (mode = 'write')}
				{disabled}
			>
				Write
			</button>
			<button
				type="button"
				class="rounded px-2 py-0.5 text-xs transition-colors {mode === 'preview'
					? 'bg-primary/20 text-primary'
					: 'text-text/50 hover:text-text/70'}"
				onclick={() => (mode = 'preview')}
				{disabled}
			>
				Preview
			</button>
		</div>

		<!-- Help Icon -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="relative"
			onmouseenter={() => (showHelpTooltip = true)}
			onmouseleave={() => (showHelpTooltip = false)}
		>
			<button
				type="button"
				class="rounded {sizeClasses.buttonPadding} text-text/40 transition-colors hover:text-text/70"
				onclick={(e) => e.stopPropagation()}
				{disabled}
			>
				<HelpIcon class={sizeClasses.iconSize} />
			</button>

			{#if showHelpTooltip}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="absolute top-1/2 right-0 z-50 w-64 -translate-y-1/2 rounded border border-text/20 bg-background p-2 text-xs shadow-lg"
					onmouseenter={() => (showHelpTooltip = true)}
					onmouseleave={() => (showHelpTooltip = false)}
					onmousedown={(e) => e.preventDefault()}
				>
					<p class="mb-1 text-text/80">
						This editor supports <span class="font-medium text-text">Markdown formatting</span>.
					</p>
					<a
						href="https://www.markdownguide.org/cheat-sheet/"
						target="_blank"
						rel="noopener noreferrer"
						class="text-primary underline hover:text-primary/80"
					>
						View Markdown cheat sheet →
					</a>
				</div>
			{/if}
		</div>
	</div>

	<!-- Content Area -->
	{#if mode === 'write'}
		<!-- Textarea -->
		<textarea
			bind:this={textareaRef}
			class="w-full resize-none overflow-y-auto bg-transparent {sizeClasses.padding} {sizeClasses.text} text-text placeholder:text-text/40 focus:outline-none"
			style="min-height: {rows * 1.5}em; max-height: 18em;"
			{placeholder}
			{disabled}
			{value}
			oninput={handleInput}
			onkeydown={handleKeydown}
			onclick={(e) => e.stopPropagation()}
			{onblur}
		></textarea>

		<!-- Character counter -->
		<div class="absolute right-2 bottom-1 text-[8px]" aria-live="polite" aria-atomic="true">
			<span class={charCount > maxCommentLength ? 'text-red-600' : 'text-text/50'}>
				{charCount} / {maxCommentLength}
			</span>
		</div>
	{:else}
		<!-- Preview -->
		<div
			class="w-full bg-transparent {sizeClasses.padding} {sizeClasses.text}"
			style="min-height: {rows * 1.5}em"
		>
			{#if value.trim()}
				<MarkdownRenderer content={value} class="text-text/80" />
			{:else}
				<p class="text-text/40 italic">{placeholder}</p>
			{/if}
		</div>
	{/if}
</div>
