<script lang="ts">
	import { onMount } from 'svelte';
	import DOMPurify from 'dompurify';
	import BoldIcon from '~icons/material-symbols/format-bold';
	import ItalicIcon from '~icons/material-symbols/format-italic';
	import UnderlineIcon from '~icons/material-symbols/format-underlined';
	import StrikethroughIcon from '~icons/material-symbols/strikethrough-s';
	import ListBulletIcon from '~icons/material-symbols/format-list-bulleted';
	import ListNumberIcon from '~icons/material-symbols/format-list-numbered';

	interface Props {
		value: string;
		placeholder?: string;
		rows?: number;
		disabled?: boolean;
		autofocus?: boolean;
		size?: 'sm' | 'md';
		onchange?: (value: string) => void;
		onkeydown?: (e: KeyboardEvent) => void;
	}

	let {
		value = $bindable(''),
		placeholder = 'Write something...',
		rows = 3,
		disabled = false,
		autofocus = false,
		size = 'md',
		onchange,
		onkeydown
	}: Props = $props();

	let textareaRef: HTMLTextAreaElement | null = $state(null);

	// Size classes
	let sizeClasses = $derived({
		text: size === 'sm' ? 'text-xs' : 'text-sm',
		padding: size === 'sm' ? 'p-1.5' : 'p-2',
		iconSize: size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5',
		buttonPadding: size === 'sm' ? 'p-0.5' : 'p-1'
	});

	// Sanitize input on change
	const handleInput = (e: Event) => {
		const target = e.target as HTMLTextAreaElement;
		// Allow markdown syntax but sanitize any HTML
		const sanitized = DOMPurify.sanitize(target.value, {
			ALLOWED_TAGS: [], // Strip all HTML tags, keep plain text with markdown
			ALLOWED_ATTR: []
		});
		value = sanitized;
		onchange?.(sanitized);
	};

	const handleKeydown = (e: KeyboardEvent) => {
		e.stopPropagation(); // Prevent parent handlers from capturing
		onkeydown?.(e);
	};

	// Insert markdown syntax around selection or at cursor
	const insertMarkdown = (prefix: string, suffix: string = prefix) => {
		if (!textareaRef) return;

		const start = textareaRef.selectionStart;
		const end = textareaRef.selectionEnd;
		const selectedText = value.substring(start, end);
		const before = value.substring(0, start);
		const after = value.substring(end);

		if (selectedText) {
			// Wrap selection
			value = before + prefix + selectedText + suffix + after;
			// Restore selection around the wrapped text
			setTimeout(() => {
				textareaRef?.setSelectionRange(start + prefix.length, end + prefix.length);
				textareaRef?.focus();
			}, 0);
		} else {
			// Insert at cursor
			value = before + prefix + suffix + after;
			// Place cursor between prefix and suffix
			setTimeout(() => {
				textareaRef?.setSelectionRange(start + prefix.length, start + prefix.length);
				textareaRef?.focus();
			}, 0);
		}
		onchange?.(value);
	};

	const insertList = (ordered: boolean) => {
		if (!textareaRef) return;

		const start = textareaRef.selectionStart;
		const end = textareaRef.selectionEnd;
		const selectedText = value.substring(start, end);
		const before = value.substring(0, start);
		const after = value.substring(end);

		// Add newline if not at start of line
		const needsNewline = before.length > 0 && !before.endsWith('\n');
		const prefix = needsNewline ? '\n' : '';

		if (selectedText) {
			// Convert selected lines to list items
			const lines = selectedText.split('\n');
			const listItems = lines
				.map((line, i) => (ordered ? `${i + 1}. ${line}` : `- ${line}`))
				.join('\n');
			value = before + prefix + listItems + after;
		} else {
			// Insert single list item
			const listPrefix = ordered ? '1. ' : '- ';
			value = before + prefix + listPrefix + after;
			setTimeout(() => {
				const cursorPos = start + prefix.length + listPrefix.length;
				textareaRef?.setSelectionRange(cursorPos, cursorPos);
				textareaRef?.focus();
			}, 0);
		}
		onchange?.(value);
	};

	const formatButtons = [
		{ icon: BoldIcon, action: () => insertMarkdown('**'), title: 'Bold (Ctrl+B)' },
		{ icon: ItalicIcon, action: () => insertMarkdown('*'), title: 'Italic (Ctrl+I)' },
		{
			icon: UnderlineIcon,
			action: () => insertMarkdown('<u>', '</u>'),
			title: 'Underline (Ctrl+U)'
		},
		{ icon: StrikethroughIcon, action: () => insertMarkdown('~~'), title: 'Strikethrough' },
		{ icon: ListBulletIcon, action: () => insertList(false), title: 'Bullet list' },
		{ icon: ListNumberIcon, action: () => insertList(true), title: 'Numbered list' }
	];

	// Handle keyboard shortcuts
	const handleShortcuts = (e: KeyboardEvent) => {
		if (!e.ctrlKey && !e.metaKey) return;

		switch (e.key.toLowerCase()) {
			case 'b':
				e.preventDefault();
				insertMarkdown('**');
				break;
			case 'i':
				e.preventDefault();
				insertMarkdown('*');
				break;
			case 'u':
				e.preventDefault();
				insertMarkdown('<u>', '</u>');
				break;
		}
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
</script>

<div class="flex flex-col rounded border border-text/20 bg-inset focus-within:border-primary">
	<!-- Toolbar -->
	<div class="flex items-center gap-0.5 border-b border-text/10 px-1 py-0.5">
		{#each formatButtons as btn (btn)}
			<button
				type="button"
				class="rounded {sizeClasses.buttonPadding} text-text/50 transition-colors hover:bg-text/10 hover:text-text/70 disabled:opacity-30"
				onclick={(e) => {
					e.stopPropagation();
					btn.action();
				}}
				title={btn.title}
				{disabled}
			>
				<btn.icon class={sizeClasses.iconSize} />
			</button>
		{/each}
	</div>

	<!-- Textarea -->
	<textarea
		bind:this={textareaRef}
		class="w-full resize-none bg-transparent {sizeClasses.padding} {sizeClasses.text} text-text placeholder:text-text/40 focus:outline-none"
		{placeholder}
		{rows}
		{disabled}
		{value}
		oninput={handleInput}
		onkeydown={(e) => {
			handleShortcuts(e);
			handleKeydown(e);
		}}
		onclick={(e) => e.stopPropagation()}
	></textarea>
</div>
