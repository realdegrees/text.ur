import type { PaginatedBase } from './types';

/**
 * Generic paginated type that replaces the data property with an array of T.
 */
export type Paginated<T> = Omit<PaginatedBase, 'data'> & {
  data: T[];
};
