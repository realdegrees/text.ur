<script lang="ts">
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';

	interface Props {
		content: string;
		class?: string;
	}

	let { content, class: className = '' }: Props = $props();

	// Configure marked for basic rendering
	marked.setOptions({
		breaks: true, // Convert \n to <br>
		gfm: true // GitHub Flavored Markdown
	});

	// Parse and sanitize markdown
	let html = $derived.by(() => {
		if (!content) return '';
		const rawHtml = marked.parse(content, { async: false }) as string;
		return DOMPurify.sanitize(rawHtml, {
			ALLOWED_TAGS: [
				'p',
				'br',
				'strong',
				'em',
				'u',
				'del',
				's',
				'ul',
				'ol',
				'li',
				'a',
				'code',
				'pre',
				'blockquote',
				'h1',
				'h2',
				'h3',
				'h4',
				'h5',
				'h6'
			],
			ALLOWED_ATTR: ['href', 'target', 'rel']
		});
	});
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div
	class="markdown-content {className}"
	onclick={(e) => {
		// Open links in new tab
		const target = e.target as HTMLElement;
		if (target.tagName === 'A') {
			e.preventDefault();
			const href = (target as HTMLAnchorElement).href;
			if (href) window.open(href, '_blank', 'noopener,noreferrer');
		}
	}}
>
	{@html html}
</div>

<style>
	.markdown-content :global(p) {
		margin-bottom: 0.5em;
	}

	.markdown-content :global(p:last-child) {
		margin-bottom: 0;
	}

	.markdown-content :global(strong) {
		font-weight: 600;
	}

	.markdown-content :global(em) {
		font-style: italic;
	}

	.markdown-content :global(u) {
		text-decoration: underline;
	}

	.markdown-content :global(del),
	.markdown-content :global(s) {
		text-decoration: line-through;
	}

	.markdown-content :global(ul),
	.markdown-content :global(ol) {
		margin-left: 1.5em;
		margin-bottom: 0.5em;
	}

	.markdown-content :global(ul) {
		list-style-type: disc;
	}

	.markdown-content :global(ol) {
		list-style-type: decimal;
	}

	.markdown-content :global(li) {
		margin-bottom: 0.25em;
	}

	.markdown-content :global(code) {
		background-color: rgba(var(--color-text-rgb), 0.1);
		padding: 0.125em 0.25em;
		border-radius: 0.25em;
		font-family: 'Courier New', monospace;
		font-size: 0.9em;
	}

	.markdown-content :global(pre) {
		background-color: rgba(var(--color-text-rgb), 0.05);
		padding: 0.75em;
		border-radius: 0.375em;
		overflow-x: auto;
		margin-bottom: 0.5em;
	}

	.markdown-content :global(pre code) {
		background-color: transparent;
		padding: 0;
	}

	.markdown-content :global(blockquote) {
		border-left: 3px solid rgba(var(--color-primary-rgb), 0.5);
		padding-left: 0.75em;
		margin-left: 0;
		margin-bottom: 0.5em;
		color: rgba(var(--color-text-rgb), 0.7);
	}

	.markdown-content :global(a) {
		color: rgb(var(--color-primary-rgb));
		text-decoration: underline;
	}

	.markdown-content :global(a:hover) {
		opacity: 0.8;
	}

	.markdown-content :global(h1),
	.markdown-content :global(h2),
	.markdown-content :global(h3),
	.markdown-content :global(h4),
	.markdown-content :global(h5),
	.markdown-content :global(h6) {
		font-weight: 600;
		margin-bottom: 0.5em;
	}

	.markdown-content :global(h1) {
		font-size: 1.5em;
	}
	.markdown-content :global(h2) {
		font-size: 1.3em;
	}
	.markdown-content :global(h3) {
		font-size: 1.1em;
	}
</style>
