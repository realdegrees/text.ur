import type { BaseTranslation } from '../i18n-types';

const en = {
	// Common / reusable
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
	user: 'User',
	status: 'Status',
	add: 'Add',
	remove: 'Remove',
	invitations: 'Invitations',
	continue: 'Continue',
	save: 'Save',
	cancel: 'Cancel',
	edit: 'Edit',
	delete: 'Delete',
	confirm: 'Confirm',
	create: 'Create',
	back: 'Back',
	close: 'Close',
	search: 'Search',
	actions: 'Actions',
	loading: 'Loading...',
	saving: 'Saving...',
	uploading: 'Uploading...',
	creating: 'Creating...',
	score: 'Score',
	anonymous: 'Anonymous',
	guest: 'Guest',
	new: 'New',
	unknown: 'Unknown',
	reply: 'Reply',
	collapse: 'Collapse',
	points: 'pts',
	builtWith: 'Built with',
	saveChanges: 'Save Changes',

	// Dashboard
	dashboard: {
		title: 'Dashboard',
		welcome: 'Welcome to text.ur!',
		noGroupsDescription:
			'Groups are where you collaborate on documents with others. Create your first group to get started.',
		selectGroup: 'Select a Group',
		selectGroupDescription:
			'Choose a group from the sidebar to view its documents and start collaborating.',
		selectFromSidebar: 'Select a group from the sidebar',
		createGroup: 'Create Your First Group',
		orAcceptInvite: 'Or accept a pending invitation from the sidebar',
		step1: 'Create a group and give it a name',
		step2: 'Upload PDF documents to annotate',
		step3: 'Invite team members to collaborate'
	},

	// Group navigation
	group: {
		documents: 'Documents',
		members: 'Members',
		settings: 'Settings',
		sharing: 'Sharing',
		memberships: {
			owner: 'Owner',
			label: 'Memberships',
			accepted: 'Member',
			invited: 'Invited'
		}
	},

	// Memberships actions
	memberships: {
		kick: 'Kick',
		actions: 'Actions',
		leave: 'Leave Group',
		invite: 'Invite',
		inviteSuccess: 'User invited successfully!',
		searchPlaceholder: 'Search username...',
		selected: '{count:number}/{total:number} Selected:',
		addPermission: 'Add Permission',
		removePermission: 'Remove Permission',
		default: 'Default',
		sharelinkLabel: 'Sharelink',
		unknownUser: 'Unknown User',
		promoteSuccess: 'Member promoted successfully.',
		promoteConfirm: 'Promote to a permanent member?',
		promoteAriaLabel: 'Promote guest {username:string} to a permanent member',
		leftGroup: 'You have left the group.',
		removedFromGroup: 'Removed {username:string} from the group.',
		leaveConfirm: 'Leave the group?',
		removeConfirm: 'Remove {username:string} from the group?',
		leaveAriaLabel: 'Leave the group',
		kickAriaLabel: 'Kick {username:string} from the group',
		invitationAccepted: 'Invitation accepted',
		invitationRejected: 'Invitation rejected',
		rejectConfirm:
			'Are you sure you want to reject this invitation? You will not be able to rejoin unless invited again.',
		createNewGroup: 'Create new group',
		memberCount: '{count:number} member{{s}}',
		documentCount: '{count:number} document{{s}}',
		youOwnThisGroup: 'You own this group',
		acceptInvitation: 'Accept invitation',
		rejectInvitation: 'Reject invitation',
		notMemberOfGroup: 'You are not a member of this group.',
		notMemberOfDocumentGroup:
			'You are not a member of the group that owns this document.'
	},

	// Permission groups
	permissionGroups: {
		administration: 'Administration',
		comments: 'Comments',
		documents: 'Documents',
		members: 'Members',
		reactions: 'Reactions',
		shareLinks: 'Share Links'
	},

	// Individual permissions
	permissions: {
		label: 'Permissions',
		administrator: 'Full administrative access',
		add_comments: 'Add comments',
		view_restricted_comments: 'View restricted comments',
		add_reactions: 'Add reactions'
	},

	// Visibility levels
	visibility: {
		label: 'Visibility',
		settings: 'Visibility Settings',
		chooseHint: 'Choose who can view this document',
		updated: 'Visibility updated',
		public: {
			label: 'Public',
			description: 'Anyone in the group can view this document'
		},
		restricted: {
			label: 'Restricted',
			description:
				'Only members with VIEW_RESTRICTED_COMMENTS permission can view'
		},
		private: {
			label: 'Private',
			description: 'Only administrators can view this document'
		}
	},

	// Backend error codes
	errors: {
		unknown_error: 'An unknown error occurred',
		validation_error: 'Validation error',
		invalid_input: 'Invalid input provided',
		database_unavailable: 'Database is currently unavailable',
		invalid_token: 'Your session token is invalid or expired',
		not_authenticated:
			'You must be logged in to perform this action',
		not_authorized:
			'You do not have permission to perform this action',
		invalid_credentials: 'Invalid username or password',
		not_in_group: 'You are not a member of this group',
		email_not_verified:
			'Please verify your email address before continuing',
		membership_not_found: 'Membership not found',
		owner_cannot_leave_group:
			'Group owner cannot leave the group',
		rate_limited: 'Too many requests. Please try again shortly.',
		sharelink_invalid: 'This share link is invalid',
		sharelink_expired: 'This share link has expired',
		cannot_remove_permission_reason_default_group:
			"Cannot remove this permission because it is included in the group's default permissions",
		cannot_remove_permission_reason_sharelink:
			'Cannot remove this permission because it is granted by a share link',
		not_found: 'The requested resource was not found',
		self_reaction: 'You cannot react to your own comment',
		reply_reaction:
			'Reactions can only be added to top-level comments',
		username_taken: 'This username is already taken',
		email_taken: 'This email address is already registered',
		sharelink_anonymous_disabled:
			'This share link does not allow anonymous access'
	},

	// Sharelink join page
	sharelink: {
		title: 'Join Group',
		description:
			'You\'ve been invited to join "{name:string}"',
		alreadyHaveAccount: 'Already have an account? Log in',
		errors: {
			usernameRequired: 'Please enter a username',
			registerFailed:
				'Failed to register. Please try again.'
		},
		members: 'Members: {count:number}',
		owner: 'Owner: {username:string}',
		created: 'Created: {date:string}',
		membershipWarning:
			'Your membership will be bound to this invite link. If it is revoked or expires you will be removed from the group.',
		details: 'Sharelink Details',
		expiresAt: 'Expires At: {date:string}',
		permissionsReceived:
			'You will automatically receive these permissions:',
		permissionsNote:
			'Invite link permissions are continuously synced with your membership permissions.',
		accountRequired: 'This invite link requires an account.',
		joinButton: 'Join',
		noAccountRegister:
			'If you do not have an account you can register here and then visit this link again.'
	},

	// User settings
	userSettings: {
		title: 'Account Settings',
		guestWarning: {
			title: 'Guest Account Warning',
			description:
				'Your account is temporary and bound to this browser. If you clear your cookies, you will lose access to this account permanently.',
			upgradeButton: 'Upgrade to Permanent Account \u{2192}',
			cancelButton: 'Cancel Upgrade'
		},
		upgradeAccount: {
			title: 'Upgrade Account',
			description:
				"Link your guest account to an email address to make it permanent. You'll need to verify your email before the upgrade is complete.",
			emailLabel: 'Email Address',
			passwordLabel: 'Password',
			confirmPasswordLabel: 'Confirm Password',
			submitButton: 'Upgrade Account',
			success:
				'Account upgraded! Please check your email to verify your account.',
			errors: {
				required: 'Email and password are required',
				passwordMismatch: 'Passwords do not match'
			}
		},
		profile: {
			title: 'Profile Information',
			usernameLabel: 'Username',
			firstNameLabel: 'First Name',
			lastNameLabel: 'Last Name',
			emailLabel: 'Email',
			saveButton: 'Save Changes',
			success: 'Profile updated successfully'
		},
		changePassword: {
			title: 'Change Password',
			currentPasswordLabel: 'Current Password',
			newPasswordLabel: 'New Password',
			confirmPasswordLabel: 'Confirm New Password',
			errors: {
				mismatch: 'New passwords do not match'
			}
		},
		logoutAllDevices: 'Logout All Devices',
		logoutGuestSession: 'Logout Guest Session',
		logoutConfirm: 'Confirm',
		deleteGuestWarning: 'This will delete your guest account!',
		logoutSuccess: 'Logged out from all devices successfully'
	},

	// Group settings
	groupSettings: {
		groupName: 'Group Name',
		groupId: 'Group ID',
		defaultPermissions: 'Default Permissions',
		defaultPermissionsDescription:
			'These permissions are automatically granted to new members when they join the group.',
		settingsUpdated: 'Group settings updated successfully',
		scoring: {
			title: 'Scoring Configuration',
			description:
				'Configure how many points members earn for different actions. Changes retroactively apply to all existing points.',
			actionPoints: 'Action Points',
			action: 'Action',
			pointsHeader: 'Points',
			createHighlight: 'Create a highlight',
			writeComment: 'Write a comment',
			addTag: 'Add a tag',
			savePoints: 'Save Points',
			savingPoints: 'Saving...',
			updated: 'Scoring configuration updated',
			emojiReactions: 'Emoji Reactions',
			emoji: 'Emoji',
			received: 'Received',
			fromAdmin: 'From admin',
			giver: 'Giver',
			addReaction: 'Add Reaction',
			selectEmoji:
				'Select an emoji ({count:number} available)',
			reactionAdded: 'Added {emoji:string} reaction',
			reactionRemoved: 'Reaction removed',
			reactionUpdated: 'Reaction updated',
			deleteExistingWarning:
				'Deletes all existing reactions',
			removeNote:
				'Removing a reaction deletes all existing reactions of that type.'
		},
		transfer: {
			title: 'Transfer Ownership',
			description:
				'Transfer ownership of this group to another member. You will lose owner privileges.',
			searchPlaceholder: 'Search member...',
			button: 'Transfer',
			confirmTitle: 'Confirm Transfer',
			confirmMessage:
				'Are you sure you want to transfer ownership to {username:string}? This action cannot be undone.',
			confirmButton: 'Confirm Transfer',
			success: 'Group ownership transferred successfully',
			selectUser:
				'Please select a user to transfer ownership to'
		},
		danger: {
			title: 'Danger Zone',
			description:
				'Once you delete a group, there is no going back. Please be certain.',
			deleteButton: 'Delete Group',
			confirmTitle: 'Confirm Deletion',
			confirmMessage:
				'Type the group name {name:string} to confirm deletion:',
			nameDoesNotMatch: 'Group name does not match',
			deleteSuccess: 'Group deleted successfully'
		}
	},

	// Group creation
	groupCreate: {
		title: 'Create New Group',
		groupDetails: 'Group Details',
		groupNameLabel: 'Group Name *',
		groupNamePlaceholder: 'Enter group name',
		groupNameRequired: 'Group name is required',
		defaultPermissions: {
			title: 'Default Member Permissions',
			description:
				'Select the default permissions that new members will have when joining this group. You can change these at any time in the group settings.'
		},
		scoring: {
			title: 'Scoring Configuration',
			description:
				'New groups are created with the following default point values. You can change these at any time in the group settings.'
		},
		createButton: 'Create Group',
		createFailed: 'Failed to create group: No data returned'
	},

	// Documents
	documents: {
		title: 'Documents',
		uploadDocument: 'Upload Document',
		documentName: 'Document Name',
		documentNamePlaceholder: 'Enter document name',
		documentDescription: 'Document Description (Optional)',
		documentDescriptionPlaceholder:
			'Add a description for this document (supports Markdown formatting)',
		documentDescriptionHint:
			"Describe the purpose of this document, what feedback you're looking for, or any other context.",
		documentFile: 'Document File',
		documentFileHint: 'Upload a PDF file (max {size:number}MB)',
		dragDrop: 'Drag and drop your PDF file here',
		orClickBrowse: 'or click to browse',
		maxFileSize: 'Maximum file size: {size:number}MB',
		selectFile: 'Please select a file to upload',
		invalidFileType:
			'Invalid file type. Only PDF files are allowed.',
		fileTooLarge:
			'File size exceeds maximum of {max:number}MB. Your file is {actual:string}MB.',
		uploadSuccess: 'Document uploaded successfully',
		uploadFailed:
			'Failed to upload document: No data returned',
		deleteSuccess: 'Document deleted successfully',
		notFound: 'Document not found.',
		created: 'Created',
		updated: 'Updated: {date:string}',
		editSettings: 'Edit document settings',
		deleteConfirm: 'Delete?',
		tagInfo: {
			title: 'Document Tags',
			description:
				'After uploading your document, you can create and manage custom tags to categorize comments. Tags help organize feedback and make it easier to filter and find specific types of annotations.',
			hint: 'You can add tags anytime from the document settings page.'
		}
	},

	// Document settings
	documentSettings: {
		title: 'Document Settings',
		backToDocuments: 'Back to documents',
		nameRequired: 'Document name is required',
		updateSuccess: 'Document updated successfully',
		savingButton: 'Saving...',
		publicDescription:
			'All group members can view this document',
		privateDescription:
			'Only administrators can view this document',
		danger: {
			title: 'Danger Zone',
			description:
				'Permanently delete all comments and annotations from this document. This action cannot be undone.',
			clearButton: 'Clear All Comments',
			clearing: 'Clearing...',
			confirmClear: 'Confirm Clear',
			clearSuccess: 'All comments cleared successfully'
		}
	},

	// Share links
	sharelinks: {
		title: 'Sharing',
		createLink: 'Create Link',
		editLink: 'Edit Link',
		newShareLink: 'New Share Link',
		created: 'Share link created successfully',
		updated: 'Share link updated successfully',
		rotated:
			'Token rotated successfully. The old link is now invalid.',
		deleted: 'Share link deleted successfully',
		linkCopied: 'Link copied to clipboard',
		copyFailed: 'Failed to copy link',
		deleteConfirm:
			'Are you sure you want to delete this share link?',
		noLinksYet:
			'No share links yet. Create one to get started.',
		labelPlaceholder: 'Label (optional)',
		allowAnonymous: 'Allow anonymous access',
		untitledLink: 'Untitled Link',
		anonymousBadge: 'Anonymous',
		anonymousTitle: 'Allows access without an account',
		createdBy:
			'created by {username:string} at {date:string}',
		lastUpdatedBy:
			'last updated by {username:string} at {date:string}',
		deletedUser: 'Deleted User',
		expires: 'Expires: {date:string}',
		expired: 'Expired',
		expiredDate: 'Expired: {date:string}',
		changeExpiryHint: 'Edit to change expiry',
		users: '{count:number} User{{s}}',
		usersTitle:
			'Members using this link: {count:number}',
		rotateConfirm:
			'This will remove {count:number} member{{s}} from the group. Are you sure?',
		copyLink: 'Copy Link',
		rotateToken: 'Rotate Token'
	},

	// Tags
	tags: {
		title: 'Tags',
		addTag: 'Add Tag',
		createTag: 'Create Tag',
		editTag: 'Edit Tag',
		newTag: 'New Tag',
		label: 'Label *',
		color: 'Color *',
		description: 'Description',
		tagLabelPlaceholder: 'Tag label',
		tagLabelEditPlaceholder: 'e.g., Bug, Question',
		descriptionPlaceholder: 'Optional description for this tag',
		labelRequired: 'Tag label is required',
		createSuccess: 'Tag created successfully',
		updateSuccess: 'Tag updated successfully',
		deleteSuccess: 'Tag deleted successfully',
		noTags: 'No tags created yet',
		editAriaLabel: 'Edit tag',
		deleteConfirm: 'Delete?',
		chooseColor: 'Choose color for tag',
		chooseColorNew: 'Choose color for new tag'
	},

	// Password reset
	passwordReset: {
		requestTitle: 'Reset Password',
		requestDescription:
			"Enter your email address and we'll send you a link to reset your password.",
		emailLabel: 'Email',
		sendResetLink: 'Send Reset Link',
		resetSent:
			'Password reset email sent! Please check your inbox for further instructions.',
		resetFailed: 'Failed to send reset email',
		setNewPassword: 'Set New Password',
		setNewPasswordDescription:
			'Enter your new password below.',
		newPasswordLabel: 'New Password',
		confirmPasswordLabel: 'Confirm Password',
		resetButton: 'Reset Password',
		passwordsDoNotMatch: 'Passwords do not match',
		passwordMinLength:
			'Password must be at least 8 characters',
		resetFailedExpired:
			'Failed to reset password. The link may be expired or invalid.',
		backToLogin: 'Back to Login',
		resetSuccess:
			'Password reset successful! You can now log in with your new password.'
	},

	// Login page
	loginPage: {
		loginTab: 'Login',
		registerTab: 'Register'
	},

	// PDF viewer / comments
	comments: {
		selectTextHint:
			'Select text in the PDF to add a comment',
		editPlaceholder: 'Edit your comment...',
		replyPlaceholder: 'Write a reply...',
		sending: 'Sending...',
		deleteConfirm: 'Delete?',
		confirmDelete: 'Confirm Delete',
		addReaction: 'Add reaction',
		removeReaction: 'Remove reaction',
		nReplies: '{count:number} repl{{y|ies}}',
		nMoreReplies: '{count:number} more repl{{y|ies}}',
		nPoints: '{count:number} point{{s}}',
		visibility: {
			select: 'Select comment visibility',
			current: 'Comment visibility: {level:string}',
			public: {
				label: 'Public - Everyone',
				description:
					'All members that can view the document can see this comment'
			},
			restricted: {
				label: 'Restricted - Group Managers',
				description:
					'Only you and group managers can see this comment'
			},
			private: {
				label: 'Private - Only you',
				description: 'Only you can see this comment'
			}
		}
	},

	// PDF controls
	pdf: {
		zoomIn: 'Zoom In',
		zoomOut: 'Zoom Out',
		fitHeight: 'Fit Height',
		previousPage: 'Previous Page',
		nextPage: 'Next Page',
		expand: 'Expand',
		shareCursor: 'Share My Cursor',
		showOtherCursors: 'Show Other Cursors',
		filtersAndPins: 'Filters & Pins',
		clearAllFilters: 'Clear All Filters',
		pinAllComments: 'Pin all comments',
		unpinAllComments: 'Unpin all comments',
		activeUsers: 'Active Users',
		offlineUsers: 'Offline Users',
		noOtherUsers: 'No other users viewing',
		you: '(You)',
		viewMode: {
			label: 'View Mode',
			tooltip:
				'In Restricted Mode members without permission will not see other comments and cursor sharing is disabled. In Public Mode comments are visible based on their individual visibility settings.',
			restricted: 'Restricted',
			restrictedDescription:
				'Restricted - Owner, admins & users with permission see comments',
			public: 'Public',
			publicDescription:
				'Public - Comments visible based on their visibility settings'
		},
		documentInfo: 'Document Information',
		pinned: 'Pinned',
		all: 'All',
		noPinnedComments: 'No pinned comments',
		noComments: 'No comments',
		expandComments: 'Expand comments',
		collapseComments: 'Collapse comments'
	},

	// Score / member detail page
	memberScore: {
		backToMembers: 'Back to Members',
		owner: 'Owner',
		admin: 'Admin',
		scoreTitle: 'Score',
		updatedAgo: 'Updated {time:string}',
		allDocuments: 'All Documents',
		showPointSystem: 'Show point system',
		hidePointSystem: 'Hide point system',
		howPointsEarned: 'How points are earned',
		totalScore: 'Total Score',
		acrossDocuments:
			'across {count:number} document{{s}}',
		highlights: 'Highlights',
		reactions: 'Reactions',
		received: '{count:number} received',
		given: '{count:number} given',
		justNow: 'just now',
		oneMinAgo: '1 min ago',
		nMinAgo: '{count:number} min ago'
	},

	// Relative time
	relativeTime: {
		never: 'Never',
		justNow: 'Just now',
		nMinutesAgo: '{count:number} minute{{s}} ago',
		nHoursAgo: '{count:number} hour{{s}} ago',
		nDaysAgo: '{count:number} day{{s}} ago'
	},

	// Footer
	footer: {
		enableDarkMode: 'Enable Dark Mode',
		enableLightMode: 'Enable Light Mode',
		changeLanguage: 'Change Language'
	}
} satisfies BaseTranslation;

export default en;
