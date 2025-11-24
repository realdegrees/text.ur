import type { Translation } from '../i18n-types';

const de = {
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
	emailVerified: 'E-Mail erfolgreich bestätigt! Ihr Konto ist jetzt aktiviert.',
	myGroups: 'Meine Gruppen',
	dashboard: {
		welcome: 'Willkommen bei text.ur!',
		noGroupsDescription: 'Gruppen sind der Ort, an dem Sie gemeinsam mit anderen an Dokumenten arbeiten. Erstellen Sie Ihre erste Gruppe, um zu beginnen.',
		selectGroup: 'Gruppe auswählen',
		selectGroupDescription: 'Wählen Sie eine Gruppe aus der Seitenleiste, um deren Dokumente anzuzeigen und mit der Zusammenarbeit zu beginnen.',
		selectFromSidebar: 'Wählen Sie eine Gruppe aus der Seitenleiste',
		createGroup: 'Erste Gruppe erstellen',
		orAcceptInvite: 'Oder akzeptieren Sie eine ausstehende Einladung aus der Seitenleiste',
		step1: 'Erstellen Sie eine Gruppe und geben Sie ihr einen Namen',
		step2: 'Laden Sie PDF-Dokumente zum Annotieren hoch',
		step3: 'Laden Sie Teammitglieder zur Zusammenarbeit ein'
	},
	group: {
		documents: 'Dokumente',
		members: 'Mitglieder',
		settings: 'Einstellungen',
		memberships: {
			owner: 'Ersteller',
			label: 'Mitgliedschaften',
			accepted: 'Mitglied',
			invited: 'Eingeladen',
		}
	},
	memberships: {
		kick: 'Kicken',
		actions: 'Aktionen',
		leave: 'Gruppe verlassen'
	},
	permissionGroups: {
		administration: 'Administration',
		comments: 'Kommentare',
		documents: 'Dokumente',
		members: 'Mitglieder',
		reactions: 'Reaktionen',
		shareLinks: 'Freigabelinks'
	},
	permissions: {
		label: 'Berechtigungen',
		administrator: 'Voller Administratorzugriff',
		add_comments: 'Kommentare hinzufügen',
		remove_comments: 'Kommentare entfernen',
		view_restricted_comments: 'Eingeschränkte Kommentare anzeigen',
		add_members: 'Mitglieder hinzufügen',
		remove_members: 'Mitglieder entfernen',
		manage_permissions: 'Berechtigungen verwalten',
		upload_documents: 'Dokumente hochladen',
		view_restricted_documents: 'Eingeschränkte Dokumente anzeigen',
		delete_documents: 'Dokumente löschen',
		remove_reactions: 'Reaktionen entfernen',
		add_reactions: 'Reaktionen hinzufügen',
		manage_share_links: 'Freigabelinks verwalten'
	},
	visibility: {
		public: {
			label: 'Öffentlich',
			description: 'Jeder in der Gruppe kann dieses Dokument sehen'
		},
		restricted: {
			label: 'Eingeschränkt',
			description: 'Nur Mitglieder mit der Berechtigung VIEW_RESTRICTED_DOCUMENTS können es sehen'
		},
		private: {
			label: 'Privat',
			description: 'Nur Sie können dieses Dokument sehen'
		}
	},
	user: 'Benutzer',
	status: 'Status',
	add: 'Hinzufügen',
	remove: 'Entfernen',
	errors: {
		unknown_error: 'Ein unbekannter Fehler ist aufgetreten',
		validation_error: 'Validierungsfehler',
		invalid_input: 'Ungültige Eingabe',
		database_unavailable: 'Datenbank ist derzeit nicht verfügbar',
		invalid_token: 'Ihr Sitzungstoken ist ungültig oder abgelaufen',
		not_authenticated: 'Sie müssen angemeldet sein, um diese Aktion durchzuführen',
		not_authorized: 'Sie haben keine Berechtigung für diese Aktion',
		invalid_credentials: 'Ungültiger Benutzername oder Passwort',
		not_in_group: 'Sie sind kein Mitglied dieser Gruppe',
		email_not_verified: 'Bitte bestätigen Sie Ihre E-Mail-Adresse, bevor Sie fortfahren',
		membership_not_found: 'Mitgliedschaft nicht gefunden',
		owner_cannot_leave_group: 'Der Gruppeninhaber kann die Gruppe nicht verlassen'
	},
	invitations: 'Einladungen'
} satisfies Translation;

export default de;
