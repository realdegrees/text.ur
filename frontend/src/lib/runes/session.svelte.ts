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
		requiredPermissions: Permission[] | { and?: Permission[]; or?: Permission[] },
		redirectUrl?: string | URL
	): boolean => {
		// Admin override
		if (currentMembership?.permissions.includes('administrator') || currentMembership?.is_owner) {
			return true;
		}

		// Handle logical combinations of permissions
		if (Array.isArray(requiredPermissions)) {
			// Default behavior: all permissions must be present (AND logic)
			if (
				!requiredPermissions.every((permission) =>
					currentMembership?.permissions.includes(permission)
				)
			) {
				if (redirectUrl) {
					redirect(303, redirectUrl);
				}
				return false;
			}
		} else {
			const { and, or } = requiredPermissions;

			// Check AND conditions
			if (and && !and.every((permission) => currentMembership?.permissions.includes(permission))) {
				if (redirectUrl) {
					redirect(303, redirectUrl);
				}
				return false;
			}

			// Check OR conditions
			if (or && !or.some((permission) => currentMembership?.permissions.includes(permission))) {
				if (redirectUrl) {
					redirect(303, redirectUrl);
				}
				return false;
			}
		}

		return true;
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
		validatePermissions
	};
};

export const sessionStore = createSessionStore();
