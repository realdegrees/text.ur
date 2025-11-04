/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

/**
 * Visibility levels for comments.
 */
export type Visibility = "private" | "restricted" | "public";
/**
 * Types of reactions users can give to comments.
 */
export type ReactionType = "like" | "dislike" | "laugh" | "confused" | "fire";
/**
 * Visibility levels for comments.
 */
export type Visibility1 = "private" | "restricted" | "public";
/**
 * Document view mode settings.
 */
export type ViewMode = "private" | "anonymous" | "public";
/**
 * Available permissions for group members.
 */
export type Permission =
  | "administrator"
  | "add_comments"
  | "remove_comments"
  | "view_public_comments"
  | "view_restricted_comments"
  | "add_members"
  | "remove_members"
  | "manage_permissions"
  | "upload_documents"
  | "view_restricted_documents"
  | "delete_documents"
  | "remove_reactions"
  | "add_reactions"
  | "manage_share_links";

/**
 * Comment entity for annotations and discussions.
 */
export interface Comment {
  created_at?: string;
  updated_at?: string;
  id?: number;
  visibility: Visibility;
  document_id: number;
  user_id: number;
  parent_id?: number | null;
  content?: string | null;
  annotation?: {
    [k: string]: unknown;
  };
}
export interface CommentCreate {
  visibility: Visibility;
  document_id: number;
  parent_id?: number | null;
  content?: string | null;
  annotation?: {
    [k: string]: unknown;
  } | null;
}
export interface CommentFilter {
  visibility: Visibility;
}
export interface CommentRead {
  created_at?: string;
  updated_at?: string;
  id: number;
  visibility: Visibility;
  user: UserRead | null;
  annotation: {
    [k: string]: unknown;
  };
  content: string | null;
  replies: CommentRead[];
  reactions: ReactionRead[];
}
export interface UserRead {
  created_at?: string;
  updated_at?: string;
  id: number;
  username: string;
  first_name?: string | null;
  last_name?: string | null;
}
export interface ReactionRead {
  type: ReactionType;
  user: UserRead;
  comment_id: number;
}
export interface CommentUpdate {
  visibility?: Visibility | null;
  content?: string | null;
  annotation?: {
    [k: string]: unknown;
  } | null;
}
/**
 * Document entity representing uploaded files.
 */
export interface Document {
  created_at?: string;
  updated_at?: string;
  id?: number;
  s3_key: string;
  size_bytes?: number;
  visibility?: Visibility1;
  view_mode?: ViewMode;
  secret?: string;
  group_id: number;
}
export interface DocumentCreate {
  visibility: Visibility;
  group_id: number;
}
export interface DocumentFilter {
  size_bytes: number;
  group_id: number;
}
export interface DocumentRead {
  created_at?: string;
  updated_at?: string;
  id: number;
  s3_key: string;
  group_id: number;
  visibility: Visibility;
}
export interface DocumentTransfer {
  group_id: number;
}
/**
 * The payload of a client facing JWT, signed with the global secret.
 */
export interface GlobalJWTPayload {
  sub: string;
  type?: ("access" | "refresh") | null;
  exp?: string | null;
  iat?: string | null;
  inner?: string | null;
}
/**
 * Group entity for shared document management.
 */
export interface Group {
  created_at?: string;
  updated_at?: string;
  id?: number;
  name: string;
  secret?: string;
  default_permissions?: Permission[];
}
export interface GroupCreate {
  name: string;
  default_permissions: Permission[];
}
/**
 * Declarative filter model for Group with filter metadata.
 */
export interface GroupFilter {
  name: string;
  member_count: number;
}
export interface GroupMembershipFilter {
  user_id: number;
}
export interface GroupMembershipRead {
  permissions: Permission[];
  user: UserRead;
  is_owner: boolean;
  accepted: boolean;
  group_id: number;
}
export interface GroupRead {
  created_at?: string;
  updated_at?: string;
  id: number;
  name: string;
  member_count: number;
  owner: UserRead | null;
}
export interface GroupUpdate {
  name?: string | null;
  default_permissions?: Permission[] | null;
}
/**
 * Association table for user-group relationships with permissions.
 */
export interface Membership {
  created_at?: string;
  updated_at?: string;
  user_id: number;
  group_id: number;
  permissions?: Permission[];
  is_owner?: boolean;
  accepted?: boolean;
}
export interface PaginatedBase {
  data: unknown[];
  total: number;
  offset: number;
  limit: number;
  filters?: Filter[];
  order_by?: string[];
}
export interface Filter {
  field: string;
  operator: "==" | ">=" | "<=" | ">" | "<" | "ilike" | "like" | "exists" | "!=";
  value: string;
  [k: string]: unknown;
}
export interface ReactionCreate {
  type: ReactionType;
}
export interface ShareLinkCreate {
  permissions: Permission[];
  expires_at?: string | null;
  label?: string | null;
}
export interface ShareLinkRead {
  id: number;
  permissions: Permission[];
  expires_at?: string | null;
  label?: string | null;
  token: string;
}
export interface ShareLinkUpdate {
  permissions?: Permission[] | null;
  expires_at?: string | null;
  label?: string | null;
  rotate_token?: boolean | null;
}
/**
 * A token object that contains the access and refresh tokens.
 */
export interface Token {
  access_token: string;
  refresh_token?: string | null;
  token_type: string;
}
export interface User {
  created_at?: string;
  updated_at?: string;
  id?: number;
  username: string;
  first_name?: string | null;
  last_name?: string | null;
  password: string;
  email: string;
  verified?: boolean;
  secret?: string;
}
export interface UserCreate {
  username: string;
  password: string;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
}
export interface UserFilter {
  username: string;
  first_name: string;
  last_name: string;
}
/**
 * The inner payload of a JWT, signed with the user's secret.
 */
export interface UserJWTPayload {
  sub: string;
  exp?: string | null;
  iat?: string | null;
}
export interface UserMembershipRead {
  permissions: Permission[];
  group: GroupRead;
  is_owner: boolean;
  accepted: boolean;
  user_id: number;
}
export interface UserPrivate {
  created_at?: string;
  updated_at?: string;
  id: number;
  username: string;
  first_name?: string | null;
  last_name?: string | null;
  email: string;
}
export interface UserUpdate {
  username?: string | null;
  new_password?: string | null;
  old_password?: string | null;
  email?: string | null;
  first_name?: string | null;
  last_name?: string | null;
}
