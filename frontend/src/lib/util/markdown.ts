import { marked } from 'marked';
import DOMPurify from 'dompurify';

// Configure marked to only allow markdown, no HTML
marked.setOptions({
	breaks: true,
	gfm: true
});

/**
 * Render markdown safely (sanitize HTML output)
 * Only allows markdown-generated tags, no raw HTML
 */
export function renderMarkdown(markdown: string): string {
	if (!markdown.trim()) return '';

	// Parse markdown
	const html = marked.parse(markdown) as string;

	// Sanitize to remove any HTML tags (only allow markdown-generated tags)
	return DOMPurify.sanitize(html, {
		ALLOWED_TAGS: [
			'p',
			'br',
			'strong',
			'em',
			'del',
			'ul',
			'ol',
			'li',
			'h1',
			'h2',
			'h3',
			'h4',
			'h5',
			'h6',
			'blockquote',
			'code',
			'pre',
			'hr',
			'a'
		],
		ALLOWED_ATTR: ['href'],
		ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?):|[^a-z]|[a-z+.-]+(?:[^a-z+.\-:]|$))/i
	});
}
