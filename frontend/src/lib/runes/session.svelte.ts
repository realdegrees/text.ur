import { redirect } from '@sveltejs/kit';
import type { MembershipRead, Permission, UserRead } from '$api/types';

/**
 * Session store for current user data and permission validation.
 * Avoids prop drilling user info deep into component trees.
 * Initialize from page data in +page.svelte.
 */
const createSessionStore = () => {
	let currentUser = $state<UserRead | null>(null);
	let currentMembership = $state<MembershipRead | null>(null);

	/**
	 * Validates if a membership has the required permissions.
	 * Supports logical combinations (AND/OR) of permissions.
	 * Admin and owner always pass validation.
	 */
	const validatePermissions = (
		membership: Partial<MembershipRead> & Pick<MembershipRead, 'permissions'>,
		requiredPermissions: Permission[] | { and?: Permission[]; or?: Permission[] },
		redirectUrl?: string | URL
	): boolean => {
		// Admin override
		if (membership.permissions.includes('administrator') || membership.is_owner) {
			return true;
		}

		// Handle logical combinations of permissions
		if (Array.isArray(requiredPermissions)) {
			// Default behavior: all permissions must be present (AND logic)
			if (!requiredPermissions.every((permission) => membership.permissions.includes(permission))) {
				if (redirectUrl) {
					redirect(303, redirectUrl);
				}
				return false;
			}
		} else {
			const { and, or } = requiredPermissions;

			// Check AND conditions
			if (and && !and.every((permission) => membership.permissions.includes(permission))) {
				if (redirectUrl) {
					redirect(303, redirectUrl);
				}
				return false;
			}

			// Check OR conditions
			if (or && !or.some((permission) => membership.permissions.includes(permission))) {
				if (redirectUrl) {
					redirect(303, redirectUrl);
				}
				return false;
			}
		}

		return true;
	};

	/**
	 * Checks if the current user can perform an action on a comment.
	 * User can delete their own comments or if they have remove_comments permission.
	 */
	const canModifyComment = (commentUserId: number | null): boolean => {
		if (!currentUser || !currentMembership) return false;

		// User owns the comment
		if (commentUserId === currentUser.id) return true;

		// User has permission to remove comments
		return validatePermissions(currentMembership, ['remove_comments']);
	};

	return {
		get currentUser() {
			return currentUser;
		},
		set currentUser(user: UserRead | null) {
			currentUser = user;
		},
		get currentUserId() {
			return currentUser?.id ?? null;
		},
		get currentMembership() {
			return currentMembership;
		},
		set currentMembership(membership: MembershipRead | null) {
			currentMembership = membership;
		},
		validatePermissions,
		canModifyComment
	};
};

export const sessionStore = createSessionStore();
