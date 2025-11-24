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
	dashboard: {
		welcome: 'Welcome to text.ur!',
		noGroupsDescription: 'Groups are where you collaborate on documents with others. Create your first group to get started.',
		selectGroup: 'Select a Group',
		selectGroupDescription: 'Choose a group from the sidebar to view its documents and start collaborating.',
		selectFromSidebar: 'Select a group from the sidebar',
		createGroup: 'Create Your First Group',
		orAcceptInvite: 'Or accept a pending invitation from the sidebar',
		step1: 'Create a group and give it a name',
		step2: 'Upload PDF documents to annotate',
		step3: 'Invite team members to collaborate'
	},
	group: {
		documents: 'Documents',
		members: 'Members',
		settings: 'Settings',
		memberships: {
			owner: 'Owner',
			label: 'Memberships',
			accepted: 'Member',
			invited: 'Invited',
		}
	},
	memberships: {
		kick: 'Kick',
		actions: 'Actions',
		leave: 'Leave Group'
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
	visibility: {
		public: {
			label: 'Public',
			description: 'Anyone in the group can view this document'
		},
		restricted: {
			label: 'Restricted',
			description: 'Only members with VIEW_RESTRICTED_DOCUMENTS permission can view'
		},
		private: {
			label: 'Private',
			description: 'Only you can view this document'
		}
	},
	user: 'User',
	status: 'Status',
	add: 'Add',
	remove: 'Remove',
	errors: {
		unknown_error: 'An unknown error occurred',
		validation_error: 'Validation error',
		invalid_input: 'Invalid input provided',
		database_unavailable: 'Database is currently unavailable',
		invalid_token: 'Your session token is invalid or expired',
		not_authenticated: 'You must be logged in to perform this action',
		not_authorized: 'You do not have permission to perform this action',
		invalid_credentials: 'Invalid username or password',
		not_in_group: 'You are not a member of this group',
		email_not_verified: 'Please verify your email address before continuing',
		membership_not_found: 'Membership not found',
		owner_cannot_leave_group: 'Group owner cannot leave the group'
	},
	invitations: 'Invitations'
} satisfies BaseTranslation;

export default en;
