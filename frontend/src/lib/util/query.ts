import type { Filter, Sort } from '$api/types';

export const filterToSearchParam = (
	filter: Filter
): {
	key: string;
	value: string;
} => {
	return {
		key: `filter[[${filter.field}][${filter.operator}]]`,
		value: filter.value
	};
};
export const sortToSearchParam = (
	sort: Sort
): {
	key: string;
	value: string;
} => {
	return {
		key: 'sort',
		value: `${sort.direction === 'desc' ? '-' : ''}${sort.field}`
	};
};
