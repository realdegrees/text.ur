import type { Translation } from '../i18n-types';

const de = {
	// Common / reusable
	login: 'Anmelden',
	logout: 'Abmelden',
	contact: 'Kontakt',
	imprint: 'Impressum',
	register: 'Registrieren',
	username: 'Benutzername',
	email: 'E-Mail',
	password: 'Passwort',
	firstName: 'Vorname',
	lastName: 'Nachname',
	confirmPassword: 'Passwort bestätigen',
	usernameOrEmail: 'Benutzername oder E-Mail',
	alreadyHaveAccount: 'Haben Sie bereits ein Konto? Anmelden',
	needAccount: 'Haben Sie kein Konto? Registrieren',
	emailVerified:
		'E-Mail erfolgreich bestätigt! Ihr Konto ist jetzt aktiviert.',
	myGroups: 'Meine Gruppen',
	user: 'Benutzer',
	status: 'Status',
	add: 'Hinzufügen',
	remove: 'Entfernen',
	invitations: 'Einladungen',
	continue: 'Weiter',
	save: 'Speichern',
	cancel: 'Abbrechen',
	edit: 'Bearbeiten',
	delete: 'Löschen',
	confirm: 'Bestätigen',
	create: 'Erstellen',
	back: 'Zurück',
	close: 'Schließen',
	search: 'Suchen',
	actions: 'Aktionen',
	loading: 'Laden...',
	saving: 'Speichern...',
	uploading: 'Hochladen...',
	creating: 'Erstellen...',
	score: 'Punktzahl',
	anonymous: 'Anonym',
	guest: 'Gast',
	new: 'Neu',
	unknown: 'Unbekannt',
	reply: 'Antworten',
	collapse: 'Einklappen',
	points: 'Pkt.',
	builtWith: 'Erstellt mit',
	saveChanges: 'Änderungen speichern',

	// Dashboard
	dashboard: {
		title: 'Dashboard',
		welcome: 'Willkommen bei text.ur!',
		noGroupsDescription:
			'Gruppen sind der Ort, an dem Sie gemeinsam mit anderen an Dokumenten arbeiten. Erstellen Sie Ihre erste Gruppe, um zu beginnen.',
		selectGroup: 'Gruppe auswählen',
		selectGroupDescription:
			'Wählen Sie eine Gruppe aus der Seitenleiste, um deren Dokumente anzuzeigen und mit der Zusammenarbeit zu beginnen.',
		selectFromSidebar:
			'Wählen Sie eine Gruppe aus der Seitenleiste',
		createGroup: 'Erste Gruppe erstellen',
		orAcceptInvite:
			'Oder akzeptieren Sie eine ausstehende Einladung aus der Seitenleiste',
		step1: 'Erstellen Sie eine Gruppe und geben Sie ihr einen Namen',
		step2: 'Laden Sie PDF-Dokumente zum Annotieren hoch',
		step3: 'Laden Sie Teammitglieder zur Zusammenarbeit ein'
	},

	// Group navigation
	group: {
		documents: 'Dokumente',
		members: 'Mitglieder',
		settings: 'Einstellungen',
		sharing: 'Freigabe',
		memberships: {
			owner: 'Ersteller',
			label: 'Mitgliedschaften',
			accepted: 'Mitglied',
			invited: 'Eingeladen'
		}
	},

	// Memberships actions
	memberships: {
		kick: 'Entfernen',
		actions: 'Aktionen',
		leave: 'Gruppe verlassen',
		invite: 'Einladen',
		inviteSuccess: 'Benutzer erfolgreich eingeladen!',
		searchPlaceholder: 'Benutzername suchen...',
		selected: '{count}/{total} Ausgewählt:',
		addPermission: 'Berechtigung hinzufügen',
		removePermission: 'Berechtigung entfernen',
		default: 'Standard',
		sharelinkLabel: 'Freigabelink',
		unknownUser: 'Unbekannter Benutzer',
		promoteSuccess: 'Mitglied erfolgreich befördert.',
		promoteConfirm:
			'Zu einem dauerhaften Mitglied befördern?',
		promoteAriaLabel:
			'Gast {username} zu einem dauerhaften Mitglied befördern',
		leftGroup: 'Sie haben die Gruppe verlassen.',
		removedFromGroup:
			'{username} wurde aus der Gruppe entfernt.',
		leaveConfirm: 'Die Gruppe verlassen?',
		removeConfirm:
			'{username} aus der Gruppe entfernen?',
		leaveAriaLabel: 'Die Gruppe verlassen',
		kickAriaLabel:
			'{username} aus der Gruppe entfernen',
		invitationAccepted: 'Einladung angenommen',
		invitationRejected: 'Einladung abgelehnt',
		rejectConfirm:
			'Sind Sie sicher, dass Sie diese Einladung ablehnen möchten? Sie können nur durch eine erneute Einladung wieder beitreten.',
		createNewGroup: 'Neue Gruppe erstellen',
		memberCount: '{count} Mitglied{{er}}',
		documentCount: '{count} Dokument{{e}}',
		youOwnThisGroup: 'Sie besitzen diese Gruppe',
		acceptInvitation: 'Einladung annehmen',
		rejectInvitation: 'Einladung ablehnen',
		notMemberOfGroup:
			'Sie sind kein Mitglied dieser Gruppe.',
		notMemberOfDocumentGroup:
			'Sie sind kein Mitglied der Gruppe, der dieses Dokument gehört.'
	},

	// Permission groups
	permissionGroups: {
		administration: 'Administration',
		comments: 'Kommentare',
		documents: 'Dokumente',
		members: 'Mitglieder',
		reactions: 'Reaktionen',
		shareLinks: 'Freigabelinks'
	},

	// Individual permissions
	permissions: {
		label: 'Berechtigungen',
		administrator: 'Voller Administratorzugriff',
		add_comments: 'Kommentare hinzufügen',
		view_restricted_comments:
			'Eingeschränkte Kommentare anzeigen',
		add_reactions: 'Reaktionen hinzufügen'
	},

	// Visibility levels
	visibility: {
		label: 'Sichtbarkeit',
		settings: 'Sichtbarkeitseinstellungen',
		chooseHint:
			'Wählen Sie, wer dieses Dokument sehen kann',
		updated: 'Sichtbarkeit aktualisiert',
		public: {
			label: 'Öffentlich',
			description:
				'Jeder in der Gruppe kann dieses Dokument sehen'
		},
		restricted: {
			label: 'Eingeschränkt',
			description:
				'Nur Mitglieder mit der Berechtigung VIEW_RESTRICTED_COMMENTS können es sehen'
		},
		private: {
			label: 'Privat',
			description:
				'Nur Administratoren können dieses Dokument sehen'
		}
	},

	// Backend error codes
	errors: {
		unknown_error: 'Ein unbekannter Fehler ist aufgetreten',
		validation_error: 'Validierungsfehler',
		invalid_input: 'Ungültige Eingabe',
		database_unavailable:
			'Datenbank ist derzeit nicht verfügbar',
		invalid_token:
			'Ihr Sitzungstoken ist ungültig oder abgelaufen',
		not_authenticated:
			'Sie müssen angemeldet sein, um diese Aktion durchzuführen',
		not_authorized:
			'Sie haben keine Berechtigung für diese Aktion',
		invalid_credentials:
			'Ungültiger Benutzername oder Passwort',
		not_in_group:
			'Sie sind kein Mitglied dieser Gruppe',
		email_not_verified:
			'Bitte bestätigen Sie Ihre E-Mail-Adresse, bevor Sie fortfahren',
		membership_not_found: 'Mitgliedschaft nicht gefunden',
		owner_cannot_leave_group:
			'Der Gruppeninhaber kann die Gruppe nicht verlassen',
		rate_limited:
			'Zu viele Anfragen. Bitte versuchen Sie es in Kürze erneut.',
		sharelink_invalid:
			'Dieser Freigabelink ist ungültig',
		sharelink_expired:
			'Dieser Freigabelink ist abgelaufen',
		cannot_remove_permission_reason_default_group:
			'Diese Berechtigung kann nicht entfernt werden, da sie in den Standardberechtigungen der Gruppe enthalten ist',
		cannot_remove_permission_reason_sharelink:
			'Diese Berechtigung kann nicht entfernt werden, da sie durch einen Freigabelink gewährt wird',
		not_found:
			'Die angeforderte Ressource wurde nicht gefunden',
		self_reaction:
			'Sie können nicht auf Ihren eigenen Kommentar reagieren',
		reply_reaction:
			'Reaktionen können nur zu Kommentaren der obersten Ebene hinzugefügt werden',
		username_taken:
			'Dieser Benutzername ist bereits vergeben',
		email_taken:
			'Diese E-Mail-Adresse ist bereits registriert',
		sharelink_anonymous_disabled:
			'Dieser Freigabelink erlaubt keinen anonymen Zugang'
	},

	// Sharelink join page
	sharelink: {
		title: 'Gruppe beitreten',
		description:
			'Sie wurden eingeladen, "{name}" beizutreten.',
		alreadyHaveAccount:
			'Haben Sie bereits ein Konto? Anmelden',
		errors: {
			usernameRequired:
				'Bitte geben Sie einen Benutzernamen ein',
			registerFailed:
				'Registrierung fehlgeschlagen. Bitte versuchen Sie es erneut.'
		},
		members: 'Mitglieder: {count}',
		owner: 'Ersteller: {username}',
		created: 'Erstellt: {date}',
		membershipWarning:
			'Ihre Mitgliedschaft ist an diesen Einladungslink gebunden. Wenn er widerrufen wird oder abläuft, werden Sie aus der Gruppe entfernt.',
		details: 'Details zum Freigabelink',
		expiresAt: 'Läuft ab am: {date}',
		permissionsReceived:
			'Sie erhalten automatisch folgende Berechtigungen:',
		permissionsNote:
			'Berechtigungen des Einladungslinks werden kontinuierlich mit Ihren Mitgliedschaftsberechtigungen synchronisiert.',
		accountRequired:
			'Dieser Einladungslink erfordert ein Konto.',
		joinButton: 'Beitreten',
		noAccountRegister:
			'Wenn Sie kein Konto haben, können Sie sich hier registrieren und diesen Link erneut besuchen.'
	},

	// User settings
	userSettings: {
		title: 'Kontoeinstellungen',
		guestWarning: {
			title: 'Gastkonto-Warnung',
			description:
				'Ihr Konto ist temporär und an diesen Browser gebunden. Wenn Sie Ihre Cookies löschen, verlieren Sie dauerhaft den Zugriff auf dieses Konto.',
			upgradeButton:
				'Auf dauerhaftes Konto upgraden \u{2192}',
			cancelButton: 'Upgrade abbrechen'
		},
		upgradeAccount: {
			title: 'Konto upgraden',
			description:
				'Verknüpfen Sie Ihr Gastkonto mit einer E-Mail-Adresse, um es dauerhaft zu machen. Sie müssen Ihre E-Mail verifizieren, bevor das Upgrade abgeschlossen ist.',
			emailLabel: 'E-Mail-Adresse',
			passwordLabel: 'Passwort',
			confirmPasswordLabel: 'Passwort bestätigen',
			submitButton: 'Konto upgraden',
			success:
				'Konto erfolgreich upgegradet! Bitte überprüfen Sie Ihre E-Mail, um Ihr Konto zu verifizieren.',
			errors: {
				required:
					'E-Mail und Passwort sind erforderlich',
				passwordMismatch:
					'Passwörter stimmen nicht überein'
			}
		},
		profile: {
			title: 'Profilinformationen',
			usernameLabel: 'Benutzername',
			firstNameLabel: 'Vorname',
			lastNameLabel: 'Nachname',
			emailLabel: 'E-Mail',
			saveButton: 'Änderungen speichern',
			success: 'Profil erfolgreich aktualisiert'
		},
		changePassword: {
			title: 'Passwort ändern',
			currentPasswordLabel: 'Aktuelles Passwort',
			newPasswordLabel: 'Neues Passwort',
			confirmPasswordLabel:
				'Neues Passwort bestätigen',
			errors: {
				mismatch:
					'Neue Passwörter stimmen nicht überein'
			}
		},
		logoutAllDevices: 'Von allen Geräten abmelden',
		logoutGuestSession: 'Gastsitzung beenden',
		logoutConfirm: 'Bestätigen',
		deleteGuestWarning:
			'Dies wird Ihr Gastkonto löschen!',
		logoutSuccess:
			'Erfolgreich von allen Geräten abgemeldet'
	},

	// Group settings
	groupSettings: {
		groupName: 'Gruppenname',
		groupId: 'Gruppen-ID',
		defaultPermissions: 'Standardberechtigungen',
		defaultPermissionsDescription:
			'Diese Berechtigungen werden neuen Mitgliedern automatisch gewährt, wenn sie der Gruppe beitreten.',
		settingsUpdated:
			'Gruppeneinstellungen erfolgreich aktualisiert',
		scoring: {
			title: 'Punktekonfiguration',
			description:
				'Konfigurieren Sie, wie viele Punkte Mitglieder für verschiedene Aktionen erhalten. Änderungen wirken sich retroaktiv auf bereits erzielte Punkte aus.',
			actionPoints: 'Aktionspunkte',
			action: 'Aktion',
			pointsHeader: 'Punkte',
			createHighlight: 'Markierung erstellen',
			writeComment: 'Kommentar schreiben',
			addTag: 'Tag hinzufügen',
			savePoints: 'Punkte speichern',
			savingPoints: 'Speichern...',
			updated:
				'Punktekonfiguration aktualisiert',
			emojiReactions: 'Emoji-Reaktionen',
			emoji: 'Emoji',
			received: 'Erhalten',
			fromAdmin: 'Von Admin',
			giver: 'Geber',
			addReaction: 'Reaktion hinzufügen',
			selectEmoji:
				'Emoji auswählen ({count} verfügbar)',
			reactionAdded:
				'Reaktion {emoji} hinzugefügt',
			reactionRemoved: 'Reaktion entfernt',
			reactionUpdated: 'Reaktion aktualisiert',
			deleteExistingWarning:
				'Löscht alle bestehenden Reaktionen',
			removeNote:
				'Das Entfernen einer Reaktion löscht alle bestehenden Reaktionen dieses Typs.'
		},
		transfer: {
			title: 'Eigentum übertragen',
			description:
				'Übertragen Sie das Eigentum dieser Gruppe an ein anderes Mitglied. Sie verlieren Ihre Eigentümerrechte.',
			searchPlaceholder: 'Mitglied suchen...',
			button: 'Übertragen',
			confirmTitle: 'Übertragung bestätigen',
			confirmMessage:
				'Sind Sie sicher, dass Sie das Eigentum an {username} übertragen möchten? Diese Aktion kann nicht rückgängig gemacht werden.',
			confirmButton: 'Übertragung bestätigen',
			success:
				'Gruppeneigentum erfolgreich übertragen',
			selectUser:
				'Bitte wählen Sie einen Benutzer aus, an den das Eigentum übertragen werden soll'
		},
		danger: {
			title: 'Gefahrenzone',
			description:
				'Sobald Sie eine Gruppe löschen, gibt es kein Zurück. Bitte seien Sie sicher.',
			deleteButton: 'Gruppe löschen',
			confirmTitle: 'Löschung bestätigen',
			confirmMessage:
				'Geben Sie den Gruppennamen {name} ein, um die Löschung zu bestätigen:',
			nameDoesNotMatch:
				'Gruppenname stimmt nicht überein',
			deleteSuccess: 'Gruppe erfolgreich gelöscht'
		}
	},

	// Group creation
	groupCreate: {
		title: 'Neue Gruppe erstellen',
		groupDetails: 'Gruppendetails',
		groupNameLabel: 'Gruppenname *',
		groupNamePlaceholder: 'Gruppenname eingeben',
		groupNameRequired: 'Gruppenname ist erforderlich',
		defaultPermissions: {
			title: 'Standard-Mitgliedsberechtigungen',
			description:
				'Wählen Sie die Standardberechtigungen, die neue Mitglieder beim Beitritt zu dieser Gruppe erhalten. Sie können diese jederzeit in den Gruppeneinstellungen ändern.'
		},
		scoring: {
			title: 'Punktekonfiguration',
			description:
				'Neue Gruppen werden mit den folgenden Standard-Punktwerten erstellt. Sie können diese jederzeit in den Gruppeneinstellungen ändern.'
		},
		createButton: 'Gruppe erstellen',
		createFailed:
			'Fehler beim Erstellen der Gruppe: Keine Daten zurückgegeben'
	},

	// Documents
	documents: {
		title: 'Dokumente',
		uploadDocument: 'Dokument hochladen',
		documentName: 'Dokumentname',
		documentNamePlaceholder: 'Dokumentname eingeben',
		documentDescription:
			'Dokumentbeschreibung (Optional)',
		documentDescriptionPlaceholder:
			'Beschreibung für dieses Dokument hinzufügen (unterstützt Markdown-Formatierung)',
		documentDescriptionHint:
			'Beschreiben Sie den Zweck dieses Dokuments, welches Feedback Sie suchen oder anderen Kontext.',
		documentFile: 'Dokumentdatei',
		documentFileHint:
			'PDF-Datei hochladen (max. {size}MB)',
		dragDrop:
			'PDF-Datei hierher ziehen und ablegen',
		orClickBrowse: 'oder klicken zum Durchsuchen',
		maxFileSize: 'Maximale Dateigröße: {size}MB',
		selectFile:
			'Bitte wählen Sie eine Datei zum Hochladen aus',
		invalidFileType:
			'Ungültiger Dateityp. Nur PDF-Dateien sind erlaubt.',
		fileTooLarge:
			'Dateigröße überschreitet das Maximum von {max}MB. Ihre Datei ist {actual}MB.',
		uploadSuccess: 'Dokument erfolgreich hochgeladen',
		uploadFailed:
			'Fehler beim Hochladen des Dokuments: Keine Daten zurückgegeben',
		deleteSuccess: 'Dokument erfolgreich gelöscht',
		notFound: 'Dokument nicht gefunden.',
		created: 'Erstellt',
		updated: 'Aktualisiert: {date}',
		editSettings: 'Dokumenteinstellungen bearbeiten',
		deleteConfirm: 'Löschen?',
		tagInfo: {
			title: 'Dokument-Tags',
			description:
				'Nach dem Hochladen Ihres Dokuments können Sie benutzerdefinierte Tags erstellen und verwalten, um Kommentare zu kategorisieren. Tags helfen bei der Organisation von Feedback und erleichtern das Filtern und Finden bestimmter Arten von Anmerkungen.',
			hint: 'Sie können Tags jederzeit über die Dokumenteinstellungsseite hinzufügen.'
		}
	},

	// Document settings
	documentSettings: {
		title: 'Dokumenteinstellungen',
		backToDocuments: 'Zurück zu Dokumenten',
		nameRequired: 'Dokumentname ist erforderlich',
		updateSuccess:
			'Dokument erfolgreich aktualisiert',
		savingButton: 'Speichern...',
		publicDescription:
			'Alle Gruppenmitglieder können dieses Dokument sehen',
		privateDescription:
			'Nur Administratoren können dieses Dokument sehen',
		danger: {
			title: 'Gefahrenzone',
			description:
				'Alle Kommentare und Anmerkungen dieses Dokuments dauerhaft löschen. Diese Aktion kann nicht rückgängig gemacht werden.',
			clearButton: 'Alle Kommentare löschen',
			clearing: 'Lösche...',
			confirmClear: 'Löschung bestätigen',
			clearSuccess:
				'Alle Kommentare erfolgreich gelöscht'
		}
	},

	// Share links
	sharelinks: {
		title: 'Freigabe',
		createLink: 'Link erstellen',
		editLink: 'Link bearbeiten',
		newShareLink: 'Neuer Freigabelink',
		created: 'Freigabelink erfolgreich erstellt',
		updated: 'Freigabelink erfolgreich aktualisiert',
		rotated:
			'Token erfolgreich erneuert. Der alte Link ist jetzt ungültig.',
		deleted: 'Freigabelink erfolgreich gelöscht',
		linkCopied: 'Link in Zwischenablage kopiert',
		copyFailed: 'Fehler beim Kopieren des Links',
		deleteConfirm:
			'Sind Sie sicher, dass Sie diesen Freigabelink löschen möchten?',
		noLinksYet:
			'Noch keine Freigabelinks. Erstellen Sie einen, um zu beginnen.',
		labelPlaceholder: 'Bezeichnung (optional)',
		allowAnonymous: 'Anonymen Zugang erlauben',
		untitledLink: 'Unbenannter Link',
		anonymousBadge: 'Anonym',
		anonymousTitle:
			'Erlaubt Zugang ohne Konto',
		createdBy:
			'erstellt von {username} am {date}',
		lastUpdatedBy:
			'zuletzt aktualisiert von {username} am {date}',
		deletedUser: 'Gelöschter Benutzer',
		expires: 'Läuft ab: {date}',
		users: '{count} Benutzer',
		usersTitle:
			'Mitglieder mit diesem Link: {count}',
		rotateConfirm:
			'Dies entfernt {count} Mitglied{{er}} aus der Gruppe. Sind Sie sicher?',
		copyLink: 'Link kopieren',
		rotateToken: 'Token erneuern'
	},

	// Tags
	tags: {
		title: 'Tags',
		addTag: 'Tag hinzufügen',
		createTag: 'Tag erstellen',
		editTag: 'Tag bearbeiten',
		newTag: 'Neuer Tag',
		label: 'Bezeichnung *',
		color: 'Farbe *',
		description: 'Beschreibung',
		tagLabelPlaceholder: 'Tag-Bezeichnung',
		tagLabelEditPlaceholder: 'z.B. Fehler, Frage',
		descriptionPlaceholder:
			'Optionale Beschreibung für diesen Tag',
		labelRequired:
			'Tag-Bezeichnung ist erforderlich',
		createSuccess: 'Tag erfolgreich erstellt',
		updateSuccess: 'Tag erfolgreich aktualisiert',
		deleteSuccess: 'Tag erfolgreich gelöscht',
		noTags: 'Noch keine Tags erstellt',
		editAriaLabel: 'Tag bearbeiten',
		deleteConfirm: 'Löschen?',
		chooseColor: 'Farbe für Tag auswählen',
		chooseColorNew: 'Farbe für neuen Tag auswählen'
	},

	// Password reset
	passwordReset: {
		requestTitle: 'Passwort zurücksetzen',
		requestDescription:
			'Geben Sie Ihre E-Mail-Adresse ein und wir senden Ihnen einen Link zum Zurücksetzen Ihres Passworts.',
		emailLabel: 'E-Mail',
		sendResetLink: 'Link zum Zurücksetzen senden',
		resetSent:
			'E-Mail zum Zurücksetzen des Passworts gesendet! Bitte überprüfen Sie Ihren Posteingang für weitere Anweisungen.',
		resetFailed:
			'Fehler beim Senden der E-Mail zum Zurücksetzen',
		setNewPassword: 'Neues Passwort festlegen',
		setNewPasswordDescription:
			'Geben Sie unten Ihr neues Passwort ein.',
		newPasswordLabel: 'Neues Passwort',
		confirmPasswordLabel: 'Passwort bestätigen',
		resetButton: 'Passwort zurücksetzen',
		passwordsDoNotMatch:
			'Passwörter stimmen nicht überein',
		passwordMinLength:
			'Passwort muss mindestens 8 Zeichen lang sein',
		resetFailedExpired:
			'Passwort konnte nicht zurückgesetzt werden. Der Link ist möglicherweise abgelaufen oder ungültig.',
		backToLogin: 'Zurück zum Anmelden',
		resetSuccess:
			'Passwort erfolgreich zurückgesetzt! Sie können sich jetzt mit Ihrem neuen Passwort anmelden.'
	},

	// Login page
	loginPage: {
		loginTab: 'Anmelden',
		registerTab: 'Registrieren'
	},

	// PDF viewer / comments
	comments: {
		selectTextHint:
			'Wählen Sie Text im PDF aus, um einen Kommentar hinzuzufügen',
		editPlaceholder: 'Kommentar bearbeiten...',
		replyPlaceholder: 'Antwort schreiben...',
		sending: 'Senden...',
		deleteConfirm: 'Löschen?',
		confirmDelete: 'Löschen bestätigen',
		addReaction: 'Reaktion hinzufügen',
		removeReaction: 'Reaktion entfernen',
		nReplies: '{count} Antwort{{en}}',
		nMoreReplies: '{count} weitere Antwort{{en}}',
		nPoints: '{count} Punkt{{e}}',
		visibility: {
			select: 'Kommentar-Sichtbarkeit wählen',
			current: 'Kommentar-Sichtbarkeit: {level}',
			public: {
				label: 'Öffentlich - Alle',
				description:
					'Alle Mitglieder, die das Dokument sehen können, können diesen Kommentar sehen'
			},
			restricted: {
				label: 'Eingeschränkt - Gruppenmanager',
				description:
					'Nur Sie und Gruppenmanager können diesen Kommentar sehen'
			},
			private: {
				label: 'Privat - Nur Sie',
				description:
					'Nur Sie können diesen Kommentar sehen'
			}
		}
	},

	// PDF controls
	pdf: {
		zoomIn: 'Vergrößern',
		zoomOut: 'Verkleinern',
		fitHeight: 'Höhe anpassen',
		previousPage: 'Vorherige Seite',
		nextPage: 'Nächste Seite',
		expand: 'Ausklappen',
		shareCursor: 'Meinen Cursor teilen',
		showOtherCursors: 'Andere Cursor anzeigen',
		filtersAndPins: 'Filter & Pins',
		clearAllFilters: 'Alle Filter löschen',
		pinAllComments: 'Alle Kommentare anheften',
		unpinAllComments: 'Alle Kommentare lösen',
		activeUsers: 'Aktive Benutzer',
		offlineUsers: 'Offline-Benutzer',
		noOtherUsers: 'Keine anderen Benutzer online',
		you: '(Sie)',
		viewMode: {
			label: 'Ansichtsmodus',
			tooltip:
				'Im eingeschränkten Modus sehen Mitglieder ohne Berechtigung keine anderen Kommentare und die Cursorfreigabe ist deaktiviert. Im öffentlichen Modus sind Kommentare basierend auf ihren individuellen Sichtbarkeitseinstellungen sichtbar.',
			restricted: 'Eingeschränkt',
			restrictedDescription:
				'Eingeschränkt – Eigentümer, Admins und Benutzer mit Berechtigung sehen Kommentare',
			public: 'Öffentlich',
			publicDescription:
				'Öffentlich – Kommentare basierend auf ihren Sichtbarkeitseinstellungen sichtbar'
		},
		documentInfo: 'Dokumentinformationen',
		pinned: 'Angeheftet',
		all: 'Alle',
		noPinnedComments: 'Keine angehefteten Kommentare',
		noComments: 'Keine Kommentare',
		expandComments: 'Kommentare ausklappen',
		collapseComments: 'Kommentare einklappen'
	},

	// Score / member detail page
	memberScore: {
		backToMembers: 'Zurück zu Mitgliedern',
		owner: 'Ersteller',
		admin: 'Admin',
		scoreTitle: 'Punktzahl',
		updatedAgo: 'Aktualisiert {time}',
		allDocuments: 'Alle Dokumente',
		showPointSystem: 'Punktesystem anzeigen',
		hidePointSystem: 'Punktesystem ausblenden',
		howPointsEarned: 'Wie Punkte verdient werden',
		totalScore: 'Gesamtpunktzahl',
		acrossDocuments:
			'über {count} Dokument{{e}}',
		highlights: 'Markierungen',
		reactions: 'Reaktionen',
		received: '{count} erhalten',
		given: '{count} gegeben',
		justNow: 'gerade eben',
		oneMinAgo: 'vor 1 Min.',
		nMinAgo: 'vor {count} Min.'
	},

	// Relative time
	relativeTime: {
		never: 'Nie',
		justNow: 'Gerade eben',
		nMinutesAgo: 'vor {count} Minute{{n}}',
		nHoursAgo: 'vor {count} Stunde{{n}}',
		nDaysAgo: 'vor {count} Tag{{en}}'
	},

	// Footer
	footer: {
		enableDarkMode: 'Dunkelmodus aktivieren',
		enableLightMode: 'Hellmodus aktivieren',
		changeLanguage: 'Sprache ändern'
	}
} satisfies Translation;

export default de;
