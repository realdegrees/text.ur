import type { ExclusionMaps, GetFilterModel, FilterTypeToName } from "./maps.generated";
import type { Filter } from "./types";

/**
 * Typed filter wrapper that constrains field names to those in the filter model.
 */
export type TypedFilter<TFilter> = {
	field: keyof TFilter;
	operator: Filter["operator"];
	value: string;
};

/**
 * Get the exclusion map for a specific filter model.
 */
type GetExclusionMap<TFilter> = FilterTypeToName<TFilter> extends keyof ExclusionMaps
	? ExclusionMaps[FilterTypeToName<TFilter>]
	: Record<string, never>;

/**
 * Extract field names from filters that use the equality operator (==).
 * Only these filters should trigger field exclusions.
 */
type ExtractEqualityFilterFields<Filters extends readonly any[]> = Filters extends readonly [
	infer First,
	...infer Rest
]
	? (First extends { field: infer F; operator: "==" } ? F : never) | ExtractEqualityFilterFields<Rest>
	: never;

/**
 * Map filter fields to their excluded response fields using the exclusion map.
 */
type MapToExcludedFields<Fields extends PropertyKey, ExclusionMap> =
	Fields extends keyof ExclusionMap ? ExclusionMap[Fields] : never;

/**
 * Compute which response fields should be excluded based on active equality filters.
 * Only filters with operator "==" will trigger field exclusions.
 */
export type ComputeExclusions<TFilter, Filters extends readonly any[]> = MapToExcludedFields<
	ExtractEqualityFilterFields<Filters>,
	GetExclusionMap<TFilter>
>;

export type { GetFilterModel };
