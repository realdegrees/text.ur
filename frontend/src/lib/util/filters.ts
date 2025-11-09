import type { Filter } from '$api/types';

export const filterToSearchParams = (...filters: Filter[]): URLSearchParams => {
	const searchParams = new URLSearchParams();
	for (const filter of filters) {
		searchParams.append(`filter[[${filter.field}][${filter.operator}]]`, filter.value);
	}
	return searchParams;
};
