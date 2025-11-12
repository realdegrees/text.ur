import type { Paginated } from '$api/pagination';
import { onMount } from 'svelte';

export function infiniteScroll<T>(
	initialData: Paginated<T>,
	loadMore: (offset: number, limit: number) => Promise<Paginated<T>>,
	step: number,
	autoLoad: boolean
) {
	let data = $state(initialData);
	let loadingMore = $state(false);
	let sentinel = $state<HTMLDivElement>();
	let scrollContainer = $state<HTMLElement>();
	let observer: IntersectionObserver | null = null;

	const items = $derived(data.data);
	const hasMore = $derived(data.data.length < data.total);

	async function handleLoadMore(reset = false) {
		if (loadingMore || (!reset && !hasMore)) return;

		loadingMore = true;

		if (reset) {
			data = {
				data: [],
				limit: step,
				offset: 0,
				total: data.total
			};
		}
		try {
			const block = await loadMore(
				data.offset + data.limit,
				Math.min(step, data.total - data.offset)
			);
			data = {
				data: [...data.data, ...block.data],
				limit: block.limit,
				offset: block.offset,
				total: block.total
			};
		} finally {
			loadingMore = false;
		}
	}

	function createObserver() {
		if (!autoLoad) return;
		if (observer) observer.disconnect();
		observer = new IntersectionObserver(
			(entries) => {
				for (const e of entries) {
					if (e.isIntersecting) handleLoadMore();
				}
			},
			{ root: scrollContainer || null, rootMargin: '0px 0px 100px 0px', threshold: 0.1 }
		);
		if (sentinel) observer.observe(sentinel);
	}

	onMount(() => {
		createObserver();
		if (items.length === 0) handleLoadMore();
		return () => {
			if (observer) observer.disconnect();
		};
	});

	return {
		get items() {
			return items;
		},
		get hasMore() {
			return hasMore;
		},
		get loadingMore() {
			return loadingMore;
		},
		get data() {
			return data;
		},
		set data(value: Paginated<T>) {
			data = value;
		},
		handleLoadMore,
		sentinel: {
			get node() {
				return sentinel;
			},
			set node(value: HTMLDivElement | undefined) {
				sentinel = value;
				createObserver();
			}
		},
		scrollContainer: {
			get node() {
				return scrollContainer;
			},
			set node(value: HTMLElement | undefined) {
				scrollContainer = value;
				createObserver();
			}
		}
	};
}
