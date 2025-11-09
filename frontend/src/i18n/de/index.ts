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
	groupOwnerLabel: 'Ersteller',
	groupDocuments: 'Dokumente',
	groupMembers: 'Mitglieder',
	groupSettings: 'Einstellungen',
	permissionGroups: {
		administration: 'Administration',
		comments: 'Kommentare',
		documents: 'Dokumente',
		members: 'Mitglieder',
		reactions: 'Reaktionen',
		shareLinks: 'Freigabelinks'
	},
	permissions: {
		administrator: 'Voller Administratorzugriff',
		add_comments: 'Kommentare hinzufügen',
		remove_comments: 'Kommentare entfernen',
		view_public_comments: 'Öffentliche Kommentare anzeigen',
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
	}
} satisfies Translation;

export default de;
