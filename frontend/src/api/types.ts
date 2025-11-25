/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

/**
 * Types of custom application exceptions.
 */
export type AppErrorCode =
  | "unknown_error"
  | "validation_error"
  | "invalid_input"
  | "database_unavailable"
  | "invalid_token"
  | "not_authenticated"
  | "not_authorized"
  | "invalid_credentials"
  | "not_in_group"
  | "email_not_verified"
  | "membership_not_found"
  | "owner_cannot_leave_group";
/**
 * Visibility levels for comments.
 */
export type Visibility = "private" | "restricted" | "public";
/**
 * Types of reactions users can give to comments.
 */
export type ReactionType = "like" | "dislike" | "laugh" | "confused" | "fire";
/**
 * Document view mode settings.
 *
 * RESTRICTED: Only owner, admins, and users with VIEW_RESTRICTED_COMMENTS can see comments
 * PUBLIC: Comments visible based on individual comment visibility settings
 */
export type ViewMode = "restricted" | "public";
/**
 * Available permissions for group members.
 */
export type Permission =
  | "administrator"
  | "add_comments"
  | "remove_comments"
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
 * Base class for all custom exceptions in the application.
 */
export interface AppError {
  status_code: number;
  error_code: AppErrorCode;
  detail: string;
}
/**
 * Comment entity for annotations and discussions.
 */
export interface Comment {
  created_at?: string;
  updated_at?: string;
  id?: number;
  visibility: Visibility;
  document_id: string;
  user_id: number;
  parent_id?: number | null;
  content?: string | null;
  annotation?: {
    [k: string]: unknown;
  };
}
export interface CommentCreate {
  visibility: Visibility;
  document_id: string;
  parent_id?: number | null;
  content?: string | null;
  annotation?: {
    [k: string]: unknown;
  } | null;
}
/**
 * Comment WebSocket event - concrete type for frontend type generation.
 */
export interface CommentEvent {
  event_id: string;
  published_at?: string;
  payload: CommentRead | null;
  resource_id: number | null;
  resource: string | null;
  type: string;
  originating_connection_id?: string | null;
}
export interface CommentRead {
  created_at?: string;
  updated_at?: string;
  id: number;
  visibility: Visibility;
  user: UserRead | null;
  parent_id: number | null;
  annotation: {
    [k: string]: unknown;
  } | null;
  content: string | null;
  num_replies: number;
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
export interface CommentFilter {
  visibility: Visibility;
  user_id: number;
  document_id: string;
  parent_id: number;
  annotation: {
    [k: string]: unknown;
  };
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
  id?: string;
  name: string;
  s3_key: string;
  size_bytes?: number;
  visibility?: Visibility;
  view_mode?: ViewMode;
  secret?: string;
  group_id: string;
}
export interface DocumentCreate {
  visibility: Visibility;
  name: string;
  group_id: string;
}
export interface DocumentFilter {
  size_bytes: number;
  group_id: string;
}
export interface DocumentRead {
  created_at?: string;
  updated_at?: string;
  id: string;
  s3_key: string;
  name: string;
  group_id: string;
  visibility: Visibility;
  view_mode: ViewMode;
}
export interface DocumentTransfer {
  group_id: string;
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
  id?: string;
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
  accepted: boolean;
}
export interface GroupRead {
  created_at?: string;
  updated_at?: string;
  id: string;
  name: string;
  member_count: number;
  owner: UserRead | null;
  default_permissions: Permission[];
}
export interface GroupTransfer {
  user_id: number;
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
  group_id: string;
  permissions?: Permission[];
  is_owner?: boolean;
  accepted?: boolean;
}
export interface MembershipCreate {
  user_id: number;
}
export interface MembershipFilter {
  user_id: number;
  group_id: string;
  accepted: boolean;
}
export interface MembershipPermissionUpdate {
  permissions: Permission[];
}
export interface MembershipRead {
  permissions: Permission[];
  user: UserRead;
  group: GroupRead;
  is_owner: boolean;
  accepted: boolean;
}
/**
 * Event payload for mouse cursor position - broadcasted to WebSocket clients (with user info).
 */
export interface MousePositionEvent {
  user_id: number;
  username: string;
  x: number;
  y: number;
  page: number;
  visible?: boolean;
}
/**
 * Input model for mouse cursor position - sent from clients (without user info).
 */
export interface MousePositionInput {
  x: number;
  y: number;
  page: number;
  visible?: boolean;
}
export interface PaginatedBase {
  data: unknown[];
  total: number;
  offset: number;
  limit: number;
  filters?: Filter[];
  order_by?: string[];
  excluded_fields?: string[];
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
export interface ShareLinkFilter {
  label: string;
  expires_at: string;
  author_id: number;
}
export interface ShareLinkRead {
  id: number;
  permissions: Permission[];
  expires_at?: string | null;
  label?: string | null;
  token: string;
  author: UserRead;
  group_id: string;
}
export interface ShareLinkUpdate {
  permissions?: Permission[] | null;
  expires_at?: string | null;
  label?: string | null;
  rotate_token?: boolean | null;
}
export interface Sort {
  field: string;
  direction: "asc" | "desc";
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
  group_id: string;
}
/**
 * The inner payload of a JWT, signed with the user's secret.
 */
export interface UserJWTPayload {
  sub: string;
  exp?: string | null;
  iat?: string | null;
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
/**
 * Event payload for view_mode changes - sent to WebSocket clients.
 */
export interface ViewModeChangedEvent {
  document_id: string;
  view_mode: ViewMode;
}
