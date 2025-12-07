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
  | "sharelink_invalid"
  | "sharelink_expired"
  | "membership_not_found"
  | "owner_cannot_leave_group"
  | "cannot_remove_permission_reason_default_group"
  | "cannot_remove_permission_reason_sharelink"
  | "username_taken"
  | "email_taken"
  | "sharelink_anonymous_disabled";
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
  | "manage_tags";

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
  tags: TagRead[];
}
export interface UserRead {
  created_at?: string;
  updated_at?: string;
  id: number;
  username: string;
  first_name?: string | null;
  last_name?: string | null;
  is_guest?: boolean;
}
export interface ReactionRead {
  type: ReactionType;
  user: UserRead;
  comment_id: number;
}
/**
 * Model for reading tag data.
 */
export interface TagRead {
  created_at?: string;
  updated_at?: string;
  id: number;
  document_id: string;
  label: string;
  description: string | null;
  color: string;
}
export interface CommentFilter {
  visibility: Visibility;
  user_id: number;
  document_id: string;
  parent_id: number;
  annotation: {
    [k: string]: unknown;
  };
  id: number;
}
/**
 * Model for bulk updating comment tags with explicit ordering.
 */
export interface CommentTagsUpdate {
  /**
   * Ordered list of tag IDs to associate with the comment
   */
  tag_ids: number[];
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
  description?: string | null;
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
  description?: string | null;
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
  description: string | null;
  view_mode: ViewMode;
  tags: TagRead[];
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
  scopes?: string[] | null;
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
  document_count: number;
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
  sharelink_id?: number | null;
  accepted?: boolean;
}
export interface MembershipCreate {
  user_id: number;
}
export interface MembershipFilter {
  user_id: number;
  group_id: string;
  accepted: boolean;
  sharelink_id: string;
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
  share_link: ShareLinkReadNoToken | null;
}
export interface ShareLinkReadNoToken {
  id: number;
  permissions: Permission[];
  expires_at?: string | null;
  allow_anonymous_access: boolean;
  created_at: string;
  updated_at: string;
  group_id: string;
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
  operator: "==" | ">=" | "<=" | ">" | "<" | "ilike" | "like" | "exists" | "!=" | "in" | "notin";
  value: string;
  [k: string]: unknown;
}
export interface ReactionCreate {
  type: ReactionType;
}
export interface ShareLinkCreate {
  permissions: Permission[];
  allow_anonymous_access?: boolean;
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
  allow_anonymous_access: boolean;
  created_at: string;
  updated_at: string;
  label?: string | null;
  token: string;
  author: UserRead | null;
  group_id: string;
  num_memberships: number;
}
/**
 * Read model for share link fetched via token, includes group info and the token itself.
 */
export interface ShareLinkReadFromToken {
  id: number;
  permissions: Permission[];
  expires_at?: string | null;
  allow_anonymous_access: boolean;
  created_at: string;
  updated_at: string;
  group: GroupRead;
  token: string;
}
export interface ShareLinkUpdate {
  permissions?: Permission[] | null;
  expires_at?: string | null;
  allow_anonymous_access?: boolean | null;
  label?: string | null;
  rotate_token?: boolean | null;
}
export interface Sort {
  field: string;
  direction: "asc" | "desc";
}
/**
 * Model for creating a new tag.
 */
export interface TagCreate {
  label: string;
  description?: string | null;
  color: string;
}
/**
 * Model for updating an existing tag.
 */
export interface TagUpdate {
  label?: string | null;
  description?: string | null;
  color?: string | null;
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
  password?: string | null;
  email?: string | null;
  verified?: boolean;
  is_guest?: boolean;
  secret?: string;
}
export interface UserCreate {
  token?: string | null;
  username: string;
  password?: string | null;
  email?: string | null;
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
  is_guest?: boolean;
  email?: string | null;
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
