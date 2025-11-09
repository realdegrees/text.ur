import type { Paginated } from '$api/pagination';
import type { Filter } from '$api/types';
import { filterToSearchParams } from '$lib/util/filters';
import { onMount } from 'svelte';

export function infiniteScroll<T>(
	initialData: Paginated<T>,
	url: string,
	step: number,
	filters: Filter[],
	autoLoad: boolean
) {
	let data = $state(initialData);
	let loadingMore = $state(false);
	let sentinel = $state<HTMLDivElement>();
	let observer: IntersectionObserver | null = null;

	const items = $derived(data.data);
	const hasMore = $derived(data.data.length < data.total);
	const previousFilters = $state<Filter[]>(filters);

	$effect.pre(() => {
		if (JSON.stringify(previousFilters) !== JSON.stringify(filters)) {
			handleLoadMore(true);
		}
	});

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
			const searchParams = filterToSearchParams(...filters);
			searchParams.append('offset', String(Math.min(data.offset + data.limit, data.total)));
			searchParams.append('limit', String(Math.min(step, data.total - data.offset)));
			const res = await fetch(`${url}?${searchParams}`);
			const block = (await res.json()) as Paginated<T>;
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
			{ root: null, rootMargin: '200px', threshold: 0.1 }
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
		}
	};
}
