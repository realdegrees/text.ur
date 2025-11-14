/* tslint:disable */
/* eslint-disable */
/**
 * This file was automatically generated from backend filter models.
 * Do not modify it by hand - regenerate by running: pnpm run typegen
 */

import type * as Types from './types';

/**
 * Maps filter field names to the response fields they should exclude.
 * Only applies when using the '==' operator.
 */
export const ExclusionMaps = {
  CommentFilter: {
    user_id: 'user',
    document_id: 'document',
  },
  DocumentFilter: {
    group_id: 'group',
  },
  GroupFilter: {
    accepted: 'accepted',
  },
  MembershipFilter: {
    user_id: 'user',
    group_id: 'group',
  },
  ShareLinkFilter: {
    author_id: 'author',
  },
} as const;

export type ExclusionMaps = typeof ExclusionMaps;

/**
 * Get the filter model type for a given read model type.
 * Auto-generated mapping: XxxRead -> XxxFilter
 */
export type GetFilterModel<T> = 
	T extends Types.CommentRead ? Types.CommentFilter :
	T extends Types.DocumentRead ? Types.DocumentFilter :
	T extends Types.GroupRead ? Types.GroupFilter :
	T extends Types.MembershipRead ? Types.MembershipFilter :
	T extends Types.ShareLinkRead ? Types.ShareLinkFilter :
	T extends Types.UserRead ? Types.UserFilter :
	Types.Filter;

/**
 * Map from Filter types to their string names in ExclusionMaps.
 * Auto-generated from backend filter models.
 */
export type FilterTypeToName<T> = 
	T extends Types.CommentFilter ? 'CommentFilter' :
	T extends Types.DocumentFilter ? 'DocumentFilter' :
	T extends Types.GroupFilter ? 'GroupFilter' :
	T extends Types.MembershipFilter ? 'MembershipFilter' :
	T extends Types.ShareLinkFilter ? 'ShareLinkFilter' :
	T extends Types.UserFilter ? 'UserFilter' :
	never;
