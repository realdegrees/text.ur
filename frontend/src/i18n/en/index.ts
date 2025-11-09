import type { BaseTranslation } from '../i18n-types';

const en = {
	login: 'Login',
	logout: 'Logout',
	contact: 'Contact',
	imprint: 'Imprint',
	register: 'Register',
	username: 'Username',
	email: 'Email',
	password: 'Password',
	firstName: 'First Name',
	lastName: 'Last Name',
	confirmPassword: 'Confirm Password',
	usernameOrEmail: 'Username or Email',
	alreadyHaveAccount: 'Already have an account? Login',
	needAccount: 'Need an account? Register',
	emailVerified: 'Email verified successfully! Your account is now activated.',
	myGroups: 'My Groups',
	group: {
		documents: 'Documents',
		members: 'Members',
		settings: 'Settings',
		memberships: {
			owner: 'Owner',
			label: 'Memberships',
			accepted: 'Accepted',
			invited: 'Invited',
		}
	},
	permissionGroups: {
		administration: 'Administration',
		comments: 'Comments',
		documents: 'Documents',
		members: 'Members',
		reactions: 'Reactions',
		shareLinks: 'Share Links'
	},
	permissions: {
		label: 'Permissions',
		administrator: 'Full administrative access',
		add_comments: 'Add comments',
		remove_comments: 'Remove comments',
		view_public_comments: 'View public comments',
		view_restricted_comments: 'View restricted comments',
		add_members: 'Add members',
		remove_members: 'Remove members',
		manage_permissions: 'Manage permissions',
		upload_documents: 'Upload documents',
		view_restricted_documents: 'View restricted documents',
		delete_documents: 'Delete documents',
		remove_reactions: 'Remove reactions',
		add_reactions: 'Add reactions',
		manage_share_links: 'Manage share links'
	},
	user: 'User',
	status: 'Status',
	add: 'Add',
	remove: 'Remove',
} satisfies BaseTranslation;

export default en;
