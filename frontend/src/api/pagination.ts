import type { PaginatedBase } from './types';

/**
 * Generic paginated type with support for field exclusions.
 * 
 * @template T - The item type
 * @template ExcludedFields - Fields to exclude from T (computed from filters)
 */
export type Paginated<T, ExcludedFields extends PropertyKey = never> = Omit<
	PaginatedBase,
	'data'
> & {
	data: Omit<T, ExcludedFields & keyof T>[];
};
