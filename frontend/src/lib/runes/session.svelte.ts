import type { UserRead } from '$api/types';

/**
 * Session store for current user data.
 * Avoids prop drilling user info deep into component trees.
 * Initialize from page data in +page.svelte.
 */
const createSessionStore = () => {
	let currentUser = $state<UserRead | null>(null);

	return {
		get currentUser() {
			return currentUser;
		},
		set currentUser(user: UserRead | null) {
			currentUser = user;
		},
		get currentUserId() {
			return currentUser?.id ?? null;
		}
	};
};

export const sessionStore = createSessionStore();
