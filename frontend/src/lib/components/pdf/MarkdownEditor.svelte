<script lang="ts">
	import { browser } from '$app/environment';
	import { renderMarkdown } from '$lib/util/markdown';
	import FormatBoldIcon from '~icons/material-symbols/format-bold';
	import FormatItalicIcon from '~icons/material-symbols/format-italic';
	import FormatStrikethroughIcon from '~icons/material-symbols/strikethrough-s';
	import FormatListBulletedIcon from '~icons/material-symbols/format-list-bulleted';
	import FormatListNumberedIcon from '~icons/material-symbols/format-list-numbered';
	import FormatQuoteIcon from '~icons/material-symbols/format-quote';
	import CodeIcon from '~icons/material-symbols/code';
	import LinkIcon from '~icons/material-symbols/link';
	import ImageIcon from '~icons/material-symbols/image-outline';

	interface Props {
		value: string;
		placeholder?: string;
		minHeight?: string;
		disabled?: boolean;
	}

	let { value = $bindable(''), placeholder = 'Write...', minHeight = '12rem', disabled = false }: Props = $props();

	type Tab = 'write' | 'preview';
	let activeTab = $state<Tab>('write');
	let textareaRef: HTMLTextAreaElement | null = $state(null);

	// Render markdown safely using shared utility
	let renderedMarkdown = $derived.by(() => {
		if (!browser) return '';
		return renderMarkdown(value);
	});

	// Insert markdown syntax at cursor position
	function insertMarkdown(before: string, after: string = '', placeholder: string = '') {
		if (!textareaRef) return;

		const start = textareaRef.selectionStart;
		const end = textareaRef.selectionEnd;
		const selectedText = value.substring(start, end);
		const textToInsert = selectedText || placeholder;

		const newText = value.substring(0, start) + before + textToInsert + after + value.substring(end);
		value = newText;

		// Set cursor position after insertion
		setTimeout(() => {
			if (!textareaRef) return;
			const newCursorPos = start + before.length + textToInsert.length;
			textareaRef.focus();
			textareaRef.setSelectionRange(newCursorPos, newCursorPos);
		}, 0);
	}

	// Formatting actions
	function formatBold() {
		insertMarkdown('**', '**', 'bold text');
	}

	function formatItalic() {
		insertMarkdown('*', '*', 'italic text');
	}

	function formatStrikethrough() {
		insertMarkdown('~~', '~~', 'strikethrough text');
	}

	function formatCode() {
		insertMarkdown('`', '`', 'code');
	}

	function formatLink() {
		insertMarkdown('[', '](https://example.com)', 'link text');
	}

	function formatImage() {
		insertMarkdown('![', '](https://example.com/image.jpg)', 'alt text');
	}

	function formatBulletList() {
		if (!textareaRef) return;
		const start = textareaRef.selectionStart;
		const lineStart = value.lastIndexOf('\n', start - 1) + 1;
		const newText = value.substring(0, lineStart) + '- ' + value.substring(lineStart);
		value = newText;
		setTimeout(() => {
			if (!textareaRef) return;
			textareaRef.focus();
			textareaRef.setSelectionRange(start + 2, start + 2);
		}, 0);
	}

	function formatNumberedList() {
		if (!textareaRef) return;
		const start = textareaRef.selectionStart;
		const lineStart = value.lastIndexOf('\n', start - 1) + 1;
		const newText = value.substring(0, lineStart) + '1. ' + value.substring(lineStart);
		value = newText;
		setTimeout(() => {
			if (!textareaRef) return;
			textareaRef.focus();
			textareaRef.setSelectionRange(start + 3, start + 3);
		}, 0);
	}

	function formatQuote() {
		if (!textareaRef) return;
		const start = textareaRef.selectionStart;
		const lineStart = value.lastIndexOf('\n', start - 1) + 1;
		const newText = value.substring(0, lineStart) + '> ' + value.substring(lineStart);
		value = newText;
		setTimeout(() => {
			if (!textareaRef) return;
			textareaRef.focus();
			textareaRef.setSelectionRange(start + 2, start + 2);
		}, 0);
	}

	// Handle keyboard shortcuts
	function handleKeydown(e: KeyboardEvent) {
		if (!e.ctrlKey && !e.metaKey) return;

		switch (e.key.toLowerCase()) {
			case 'b':
				e.preventDefault();
				formatBold();
				break;
			case 'i':
				e.preventDefault();
				formatItalic();
				break;
			case 'k':
				e.preventDefault();
				formatLink();
				break;
		}
	}
</script>

<div class="markdown-editor flex flex-col rounded-lg border border-text/20 bg-inset shadow-sm overflow-hidden">
	<!-- Header with tabs and toolbar -->
	<div class="border-b border-text/10">
		<!-- Tab buttons -->
		<div class="flex bg-background/50">
			<button
				onclick={() => (activeTab = 'write')}
				class="px-4 py-2 text-sm font-medium transition-colors border-b-2 {activeTab === 'write' ? 'border-primary text-text bg-background' : 'border-transparent text-text/60 hover:text-text hover:bg-background/50'}"
				type="button"
			>
				Write
			</button>
			<button
				onclick={() => (activeTab = 'preview')}
				class="px-4 py-2 text-sm font-medium transition-colors border-b-2 {activeTab === 'preview' ? 'border-primary text-text bg-background' : 'border-transparent text-text/60 hover:text-text hover:bg-background/50'}"
				type="button"
			>
				Preview
			</button>
		</div>

		<!-- Formatting toolbar (only shown in write mode) -->
		{#if activeTab === 'write'}
			<div class="flex flex-wrap gap-1 px-2 py-1.5 bg-background border-t border-text/10">
				<button
					type="button"
					onclick={formatBold}
					disabled={disabled}
					class="rounded p-1.5 text-text/60 transition-all hover:bg-primary/10 hover:text-primary disabled:opacity-50 disabled:cursor-not-allowed"
					title="Bold (Ctrl+B)"
					aria-label="Bold"
				>
					<FormatBoldIcon class="h-4 w-4" />
				</button>
				<button
					type="button"
					onclick={formatItalic}
					disabled={disabled}
					class="rounded p-1.5 text-text/60 transition-all hover:bg-primary/10 hover:text-primary disabled:opacity-50 disabled:cursor-not-allowed"
					title="Italic (Ctrl+I)"
					aria-label="Italic"
				>
					<FormatItalicIcon class="h-4 w-4" />
				</button>
				<button
					type="button"
					onclick={formatStrikethrough}
					disabled={disabled}
					class="rounded p-1.5 text-text/60 transition-all hover:bg-primary/10 hover:text-primary disabled:opacity-50 disabled:cursor-not-allowed"
					title="Strikethrough"
					aria-label="Strikethrough"
				>
					<FormatStrikethroughIcon class="h-4 w-4" />
				</button>

				<div class="w-px bg-text/10 mx-1"></div>

				<button
					type="button"
					onclick={formatBulletList}
					disabled={disabled}
					class="rounded p-1.5 text-text/60 transition-all hover:bg-primary/10 hover:text-primary disabled:opacity-50 disabled:cursor-not-allowed"
					title="Bullet List"
					aria-label="Bullet List"
				>
					<FormatListBulletedIcon class="h-4 w-4" />
				</button>
				<button
					type="button"
					onclick={formatNumberedList}
					disabled={disabled}
					class="rounded p-1.5 text-text/60 transition-all hover:bg-primary/10 hover:text-primary disabled:opacity-50 disabled:cursor-not-allowed"
					title="Numbered List"
					aria-label="Numbered List"
				>
					<FormatListNumberedIcon class="h-4 w-4" />
				</button>
				<button
					type="button"
					onclick={formatQuote}
					disabled={disabled}
					class="rounded p-1.5 text-text/60 transition-all hover:bg-primary/10 hover:text-primary disabled:opacity-50 disabled:cursor-not-allowed"
					title="Quote"
					aria-label="Quote"
				>
					<FormatQuoteIcon class="h-4 w-4" />
				</button>

				<div class="w-px bg-text/10 mx-1"></div>

				<button
					type="button"
					onclick={formatCode}
					disabled={disabled}
					class="rounded p-1.5 text-text/60 transition-all hover:bg-primary/10 hover:text-primary disabled:opacity-50 disabled:cursor-not-allowed"
					title="Inline Code"
					aria-label="Inline Code"
				>
					<CodeIcon class="h-4 w-4" />
				</button>
				<button
					type="button"
					onclick={formatLink}
					disabled={disabled}
					class="rounded p-1.5 text-text/60 transition-all hover:bg-primary/10 hover:text-primary disabled:opacity-50 disabled:cursor-not-allowed"
					title="Link (Ctrl+K)"
					aria-label="Link"
				>
					<LinkIcon class="h-4 w-4" />
				</button>
				<button
					type="button"
					onclick={formatImage}
					disabled={disabled}
					class="rounded p-1.5 text-text/60 transition-all hover:bg-primary/10 hover:text-primary disabled:opacity-50 disabled:cursor-not-allowed"
					title="Image"
					aria-label="Image"
				>
					<ImageIcon class="h-4 w-4" />
				</button>
			</div>
		{/if}
	</div>

	<!-- Content area -->
	<div class="flex-1 bg-background" style:min-height={minHeight}>
		{#if activeTab === 'write'}
			<textarea
				bind:this={textareaRef}
				bind:value
				{placeholder}
				{disabled}
				onkeydown={handleKeydown}
				class="h-full w-full resize-none bg-background px-3 py-2.5 text-sm text-text placeholder-text/40 focus:outline-none custom-scrollbar"
				style:min-height={minHeight}
			></textarea>
		{:else}
			<div class="prose prose-sm h-full w-full max-w-none overflow-auto px-3 py-2.5 text-text custom-scrollbar">
				{#if value.trim()}
					<!-- eslint-disable-next-line svelte/no-at-html-tags -->
					{@html renderedMarkdown}
				{:else}
					<p class="text-text/40 italic">Nothing to preview</p>
				{/if}
			</div>
		{/if}
	</div>
</div>

<style>
	/* Markdown preview styles */
	:global(.prose) {
		color: var(--color-text);
	}

	:global(.prose p) {
		margin-bottom: 0.75em;
	}

	:global(.prose h1),
	:global(.prose h2),
	:global(.prose h3),
	:global(.prose h4),
	:global(.prose h5),
	:global(.prose h6) {
		font-weight: 600;
		margin-top: 1em;
		margin-bottom: 0.5em;
		color: var(--color-text);
	}

	:global(.prose h1) {
		font-size: 1.5em;
	}
	:global(.prose h2) {
		font-size: 1.3em;
	}
	:global(.prose h3) {
		font-size: 1.1em;
	}

	:global(.prose ul),
	:global(.prose ol) {
		padding-left: 1.5em;
		margin-bottom: 0.75em;
	}

	:global(.prose li) {
		margin-bottom: 0.25em;
	}

	:global(.prose strong) {
		font-weight: 600;
	}

	:global(.prose em) {
		font-style: italic;
	}

	:global(.prose del) {
		text-decoration: line-through;
	}

	:global(.prose code) {
		background-color: var(--color-inset);
		padding: 0.125em 0.25em;
		border-radius: 0.25em;
		font-family: monospace;
		font-size: 0.9em;
	}

	:global(.prose pre) {
		background-color: var(--color-inset);
		padding: 0.75em;
		border-radius: 0.375em;
		overflow-x: auto;
		margin-bottom: 0.75em;
	}

	:global(.prose pre code) {
		background-color: transparent;
		padding: 0;
	}

	:global(.prose blockquote) {
		border-left: 0.25em solid var(--color-primary);
		padding-left: 1em;
		margin-left: 0;
		color: color-mix(in srgb, var(--color-text) 80%, transparent);
		font-style: italic;
	}

	:global(.prose a) {
		color: var(--color-primary);
		text-decoration: underline;
	}

	:global(.prose a:hover) {
		color: var(--color-accent);
	}

	:global(.prose hr) {
		border: none;
		border-top: 1px solid var(--color-text);
		opacity: 0.2;
		margin: 1em 0;
	}
</style>
