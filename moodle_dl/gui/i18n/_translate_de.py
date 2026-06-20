"""One-off helper: fill German translations into moodledl_de.ts.

Run from the repo root:  python moodle_dl/gui/i18n/_translate_de.py
Then compile:            lrelease6 moodle_dl/gui/i18n/moodledl_de.ts

Keys must match the tr() source strings exactly (including placeholders and
newlines). Re-run after `lupdate6` to translate any newly added strings; any
source string missing from DE below is reported and left unfinished.
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

TS_PATH = Path(__file__).with_name('moodledl_de.ts')

DE = {
    # --- ConfigPage ---
    'Courses': 'Kurse',
    'Fetch Courses': 'Kurse abrufen',
    'Select All': 'Alle auswählen',
    'Deselect All': 'Auswahl aufheben',
    'Download selected courses': 'Ausgewählte Kurse herunterladen',
    'Download all except selected': 'Alle außer den ausgewählten herunterladen',
    'Click "Fetch Courses" to load your course list.': 'Auf „Kurse abrufen“ klicken, um die Kursliste zu laden.',
    'Filter courses…': 'Kurse filtern…',
    'Double-click a course to set custom name and options.':
        'Doppelklick auf einen Kurs, um Namen und Optionen festzulegen.',
    'Download Options': 'Download-Optionen',
    'Download Submissions': 'Abgaben herunterladen',
    'Download student assignment submissions.': 'Abgaben von Aufgaben der Studierenden herunterladen.',
    'Download Descriptions': 'Beschreibungen herunterladen',
    'Download activity and resource descriptions as HTML files.':
        'Beschreibungen von Aktivitäten und Materialien als HTML-Dateien herunterladen.',
    'Download Links in Descriptions': 'Links in Beschreibungen herunterladen',
    'Download files linked within activity descriptions.':
        'In Aktivitätsbeschreibungen verlinkte Dateien herunterladen.',
    'Download Databases': 'Datenbanken herunterladen',
    'Download Moodle database activity entries.': 'Einträge der Moodle-Datenbank-Aktivität herunterladen.',
    'Download Forums': 'Foren herunterladen',
    'Download forum posts and attachments.': 'Forenbeiträge und Anhänge herunterladen.',
    'Download Quizzes': 'Tests herunterladen',
    'Download quiz attempts and results.': 'Testversuche und Ergebnisse herunterladen.',
    'Download Lessons': 'Lektionen herunterladen',
    'Download lesson activity content.': 'Inhalte der Lektions-Aktivität herunterladen.',
    'Download Workshops': 'Workshops herunterladen',
    'Download workshop submissions and assessments.': 'Workshop-Abgaben und -Bewertungen herunterladen.',
    'Download Books': 'Bücher herunterladen',
    'Download book resource content as HTML.': 'Inhalte des Buch-Materials als HTML herunterladen.',
    'Download Calendars': 'Kalender herunterladen',
    'Download course calendar events.': 'Kalendertermine des Kurses herunterladen.',
    'Download Linked Files': 'Verlinkte Dateien herunterladen',
    'Download externally linked files referenced in courses.':
        'Extern verlinkte Dateien herunterladen, die in Kursen referenziert werden.',
    'Download Files Requiring Cookie': 'Dateien herunterladen, die Cookies erfordern',
    'Also download files that require browser cookies for access.':
        'Auch Dateien herunterladen, die für den Zugriff Browser-Cookies benötigen.',
    'Save Configuration': 'Konfiguration speichern',
    'Fetching…': 'Wird abgerufen…',
    'Fetching courses…': 'Kurse werden abgerufen…',
    'Found {} courses.': '{} Kurse gefunden.',
    '{} (ID: {})': '{} (ID: {})',
    'Error: {}': 'Fehler: {}',
    'No courses selected': 'Keine Kurse ausgewählt',
    'Please select at least one course.': 'Bitte mindestens einen Kurs auswählen.',
    'Saved': 'Gespeichert',
    'Configuration saved successfully.': 'Konfiguration erfolgreich gespeichert.',

    # --- CourseOptionsDialog ---
    'Options for: {}': 'Optionen für: {}',
    'Override the course folder name. Leave empty to use the default.':
        'Den Kursordnernamen überschreiben. Leer lassen, um den Standard zu verwenden.',
    'Custom Name:': 'Eigener Name:',
    'Create Directory Structure': 'Verzeichnisstruktur erstellen',
    'Create subdirectories matching the Moodle course section structure.':
        'Unterverzeichnisse passend zur Abschnittsstruktur des Moodle-Kurses erstellen.',
    'Section Exclusion': 'Abschnitte ausschließen',
    'Uncheck sections to exclude them from downloads.':
        'Abschnitte abwählen, um sie vom Download auszuschließen.',
    'Load Sections': 'Abschnitte laden',
    'Fetch available sections from Moodle.': 'Verfügbare Abschnitte von Moodle abrufen.',
    'Fetching sections…': 'Abschnitte werden abgerufen…',
    'Found {} sections.': '{} Abschnitte gefunden.',
    'Section {}': 'Abschnitt {}',

    # --- DatabaseManagementDialog ---
    'Missing Files': 'Fehlende Dateien',
    'These files are tracked in the database but no longer exist on disk. Remove entries here to '
    're-download them on the next scan.':
        'Diese Dateien sind in der Datenbank erfasst, existieren aber nicht mehr auf der Festplatte. '
        'Einträge hier entfernen, um sie beim nächsten Scan erneut herunterzuladen.',
    'Name': 'Name',
    'Section': 'Abschnitt',
    'Path': 'Pfad',
    'Refresh': 'Aktualisieren',
    'Delete Selected from DB': 'Ausgewählte aus DB löschen',
    'Close': 'Schließen',
    'Loading stored files…': 'Gespeicherte Dateien werden geladen…',
    'No missing files found in the database.': 'Keine fehlenden Dateien in der Datenbank gefunden.',
    '{} missing file(s) found.': '{} fehlende Datei(en) gefunden.',
    'Delete from Database': 'Aus Datenbank löschen',
    'Delete {} file entry(ies) from the database?\nThese files will be re-downloaded on the next scan.':
        '{} Dateieintrag/-einträge aus der Datenbank löschen?\n'
        'Diese Dateien werden beim nächsten Scan erneut heruntergeladen.',
    'Deleted {} entry(ies). Refreshing…': '{} Eintrag/Einträge gelöscht. Wird aktualisiert…',

    # --- DownloadPage ---
    'Scan Moodle': 'Moodle scannen',
    'Start Download': 'Download starten',
    'Cancel All': 'Alle abbrechen',
    'Skip Selected': 'Ausgewählte überspringen',
    'Always Skip Selected': 'Ausgewählte immer überspringen',
    'Overall Progress': 'Gesamtfortschritt',
    'Ready. Navigate here to scan for changes.': 'Bereit. Hierher navigieren, um nach Änderungen zu scannen.',
    'Scanning Moodle for changes…': 'Moodle wird nach Änderungen durchsucht…',
    'Error': 'Fehler',
    'No configuration found. Please log in first.': 'Keine Konfiguration gefunden. Bitte zuerst anmelden.',
    'No new or changed files found.': 'Keine neuen oder geänderten Dateien gefunden.',
    'Found {} file(s) to download. Review and click Start Download.':
        '{} Datei(en) zum Herunterladen gefunden. Prüfen und „Download starten“ klicken.',
    'Scan Error': 'Scan-Fehler',
    'Nothing to Download': 'Nichts herunterzuladen',
    'All files have been skipped.': 'Alle Dateien wurden übersprungen.',
    'Downloading…': 'Wird heruntergeladen…',
    'Starting download…': 'Download wird gestartet…',
    'Downloading {} files…': '{} Dateien werden heruntergeladen…',
    'Download complete. {} succeeded, {} failed.': 'Download abgeschlossen. {} erfolgreich, {} fehlgeschlagen.',
    '\n... and {} more': '\n… und {} weitere',
    'Some Downloads Failed': 'Einige Downloads fehlgeschlagen',
    '{} file(s) failed to download:\n\n{}': '{} Datei(en) konnten nicht heruntergeladen werden:\n\n{}',
    'Download Error': 'Download-Fehler',
    '{} / {} | Done: {} / {} | Failed: {}': '{} / {} | Fertig: {} / {} | Fehlgeschlagen: {}',
    'Skip ({})': 'Überspringen ({})',
    'Skip': 'Überspringen',
    'Always Skip ({})': 'Immer überspringen ({})',
    'Always Skip': 'Immer überspringen',
    'Remove Always Skip ({})': '„Immer überspringen“ entfernen ({})',
    'Remove Always Skip': '„Immer überspringen“ entfernen',
    'All files skipped. Click Scan to re-check.':
        'Alle Dateien übersprungen. Auf „Scannen“ klicken, um erneut zu prüfen.',
    '{} file(s) remaining. Review and click Start Download.':
        '{} Datei(en) verbleibend. Prüfen und „Download starten“ klicken.',
    'Cancel All Downloads': 'Alle Downloads abbrechen',
    'Are you sure you want to cancel all running downloads?':
        'Sollen wirklich alle laufenden Downloads abgebrochen werden?',
    'Cancelling…': 'Wird abgebrochen…',

    # --- LoginPage ---
    'Moodle Login': 'Moodle-Anmeldung',
    'Moodle URL:': 'Moodle-URL:',
    'your.username': 'dein.benutzername',
    'Username:': 'Benutzername:',
    'your password': 'dein Passwort',
    'Password:': 'Passwort:',
    'Login': 'Anmelden',
    'Normal Login': 'Normale Anmeldung',
    'Open SSO Login in Browser': 'SSO-Anmeldung im Browser öffnen',
    'Enter your Moodle URL and click the button to start SSO login.\n'
    'The login page will open below (requires PySide6-WebEngine).':
        'Moodle-URL eingeben und auf die Schaltfläche klicken, um die SSO-Anmeldung zu starten.\n'
        'Die Anmeldeseite öffnet sich unten (erfordert PySide6-WebEngine).',
    'SSO Login': 'SSO-Anmeldung',
    'Token Login': 'Token-Anmeldung',
    'Paste your Moodle token here': 'Moodle-Token hier einfügen',
    'Token:': 'Token:',
    'Optional': 'Optional',
    'Private Token:': 'Privater Token:',
    'Save Token': 'Token speichern',
    'Please enter a Moodle URL.': 'Bitte eine Moodle-URL eingeben.',
    'Invalid Moodle URL.': 'Ungültige Moodle-URL.',
    'Please enter both username and password.': 'Bitte Benutzername und Passwort eingeben.',
    'Logging in…': 'Anmeldung läuft…',
    'Login successful!': 'Anmeldung erfolgreich!',
    'Login failed: {}': 'Anmeldung fehlgeschlagen: {}',
    'Please enter a token.': 'Bitte einen Token eingeben.',
    'Saving…': 'Wird gespeichert…',
    'Token saved successfully!': 'Token erfolgreich gespeichert!',
    'Failed to save token: {}': 'Token konnte nicht gespeichert werden: {}',
    'Enter your credentials below.': 'Zugangsdaten unten eingeben.',
    'Page load error. The SSO login page may still appear after redirects.':
        'Fehler beim Laden der Seite. Die SSO-Anmeldeseite erscheint möglicherweise nach Weiterleitungen.',
    'Opening…': 'Wird geöffnet…',
    'Loading SSO login page…': 'SSO-Anmeldeseite wird geladen…',
    'PySide6-WebEngine is not installed. Cannot open embedded browser.':
        'PySide6-WebEngine ist nicht installiert. Eingebetteter Browser kann nicht geöffnet werden.',
    'Token received, verifying…': 'Token empfangen, wird überprüft…',
    'SSO login successful!': 'SSO-Anmeldung erfolgreich!',
    'SSO login failed: {}': 'SSO-Anmeldung fehlgeschlagen: {}',

    # --- MainWindow ---
    'Navigation': 'Navigation',
    'Download': 'Download',
    'Settings': 'Einstellungen',
    'Notifications': 'Benachrichtigungen',
    'Find files tracked in the database but missing from disk. Remove entries to re-download them.':
        'Dateien finden, die in der Datenbank erfasst sind, aber auf der Festplatte fehlen. '
        'Einträge entfernen, um sie erneut herunterzuladen.',
    'Outdated Copies': 'Veraltete Kopien',
    'Find old file versions that have been replaced by newer ones. Delete them to free disk space.':
        'Alte Dateiversionen finden, die durch neuere ersetzt wurden. Löschen, um Speicherplatz freizugeben.',
    'Logout': 'Abmelden',
    'Log out and return to the login page.': 'Abmelden und zur Anmeldeseite zurückkehren.',
    'Please log in to your Moodle account.': 'Bitte bei deinem Moodle-Konto anmelden.',
    'Loaded existing configuration.': 'Vorhandene Konfiguration geladen.',
    'Login successful. Configure your courses.': 'Anmeldung erfolgreich. Konfiguriere deine Kurse.',
    'Login Failed': 'Anmeldung fehlgeschlagen',
    'Login failed.': 'Anmeldung fehlgeschlagen.',
    'Are you sure you want to log out? Any running downloads will be cancelled.':
        'Wirklich abmelden? Alle laufenden Downloads werden abgebrochen.',
    'Logged out. Please log in again.': 'Abgemeldet. Bitte erneut anmelden.',

    # --- NotificationsPage ---
    'Telegram Configuration': 'Telegram-Konfiguration',
    'Bot token from @BotFather.': 'Bot-Token von @BotFather.',
    'Bot Token:': 'Bot-Token:',
    'e.g. 123456789': 'z. B. 123456789',
    'Your Telegram chat ID. Send /start to @userinfobot to find it.':
        'Deine Telegram-Chat-ID. Sende /start an @userinfobot, um sie herauszufinden.',
    'Chat ID:': 'Chat-ID:',
    'Send Error Reports': 'Fehlerberichte senden',
    'Also send error notifications via Telegram.': 'Auch Fehlerbenachrichtigungen über Telegram senden.',
    'Test': 'Testen',
    'Save': 'Speichern',
    'Disable': 'Deaktivieren',
    'Telegram': 'Telegram',
    'Discord Configuration': 'Discord-Konfiguration',
    'Webhook URLs (one per line):': 'Webhook-URLs (eine pro Zeile):',
    'Enter one Discord webhook URL per line.': 'Eine Discord-Webhook-URL pro Zeile eingeben.',
    'Discord': 'Discord',
    'Email (SMTP) Configuration': 'E-Mail-Konfiguration (SMTP)',
    'Email address to send from.': 'Absende-E-Mail-Adresse.',
    'Sender:': 'Absender:',
    'SMTP server hostname.': 'Hostname des SMTP-Servers.',
    'SMTP Host:': 'SMTP-Host:',
    'SMTP server port (typically 587 for STARTTLS).': 'SMTP-Server-Port (typischerweise 587 für STARTTLS).',
    'SMTP Port:': 'SMTP-Port:',
    'SMTP authentication username.': 'Benutzername für die SMTP-Authentifizierung.',
    'SMTP authentication password.': 'Passwort für die SMTP-Authentifizierung.',
    'Recipient email address.': 'E-Mail-Adresse des Empfängers.',
    'Target:': 'Empfänger:',
    'Also send error notifications via email.': 'Auch Fehlerbenachrichtigungen per E-Mail senden.',
    'Email': 'E-Mail',
    'ntfy Configuration': 'ntfy-Konfiguration',
    'The ntfy topic to publish to.': 'Das ntfy-Thema, an das veröffentlicht wird.',
    'Topic:': 'Thema:',
    'Custom ntfy server URL. Leave empty to use the default (https://ntfy.sh/).':
        'Eigene ntfy-Server-URL. Leer lassen, um den Standard (https://ntfy.sh/) zu verwenden.',
    'Server URL:': 'Server-URL:',
    'ntfy': 'ntfy',
    'XMPP Configuration': 'XMPP-Konfiguration',
    'Sender JID (Jabber ID).': 'Absender-JID (Jabber-ID).',
    'Sender JID:': 'Absender-JID:',
    'XMPP account password.': 'Passwort des XMPP-Kontos.',
    'Target JID to receive notifications.': 'Ziel-JID für den Empfang von Benachrichtigungen.',
    'Target JID:': 'Ziel-JID:',
    'Also send error notifications via XMPP.': 'Auch Fehlerbenachrichtigungen über XMPP senden.',
    'XMPP': 'XMPP',
    'Please enter both Bot Token and Chat ID.': 'Bitte Bot-Token und Chat-ID eingeben.',
    'Sending…': 'Wird gesendet…',
    'Sending test message…': 'Testnachricht wird gesendet…',
    'Test message sent successfully!': 'Testnachricht erfolgreich gesendet!',
    'Test failed: {}': 'Test fehlgeschlagen: {}',
    'Telegram configuration saved.': 'Telegram-Konfiguration gespeichert.',
    'Telegram notifications disabled.': 'Telegram-Benachrichtigungen deaktiviert.',
    'Please enter at least one webhook URL.': 'Bitte mindestens eine Webhook-URL eingeben.',
    'Discord configuration saved.': 'Discord-Konfiguration gespeichert.',
    'Discord notifications disabled.': 'Discord-Benachrichtigungen deaktiviert.',
    'Please fill in all required fields.': 'Bitte alle erforderlichen Felder ausfüllen.',
    'Sending test email…': 'Test-E-Mail wird gesendet…',
    'Test email sent successfully!': 'Test-E-Mail erfolgreich gesendet!',
    'Please fill in sender, host, and target.': 'Bitte Absender, Host und Empfänger ausfüllen.',
    'Email configuration saved.': 'E-Mail-Konfiguration gespeichert.',
    'Email notifications disabled.': 'E-Mail-Benachrichtigungen deaktiviert.',
    'Please enter a topic.': 'Bitte ein Thema eingeben.',
    'Sending test notification…': 'Testbenachrichtigung wird gesendet…',
    'Test notification sent successfully!': 'Testbenachrichtigung erfolgreich gesendet!',
    'ntfy configuration saved.': 'ntfy-Konfiguration gespeichert.',
    'ntfy notifications disabled.': 'ntfy-Benachrichtigungen deaktiviert.',
    'Please fill in sender JID and target JID.': 'Bitte Absender-JID und Ziel-JID ausfüllen.',
    'XMPP configuration saved.': 'XMPP-Konfiguration gespeichert.',
    'XMPP notifications disabled.': 'XMPP-Benachrichtigungen deaktiviert.',

    # --- OldFilesDialog ---
    'These are older versions of files that have been replaced by newer ones but are still on disk. '
    'Select entries to delete them and free up disk space.':
        'Dies sind ältere Dateiversionen, die durch neuere ersetzt wurden, aber noch auf der Festplatte liegen. '
        'Einträge auswählen, um sie zu löschen und Speicherplatz freizugeben.',
    'Delete Selected': 'Ausgewählte löschen',
    'Loading old files…': 'Alte Dateien werden geladen…',
    'No old file copies found.': 'Keine alten Dateikopien gefunden.',
    '{} old file(s) found.': '{} alte Datei(en) gefunden.',
    'Delete Old Files': 'Alte Dateien löschen',
    'Delete {} old file(s) from disk and database?\nThis action cannot be undone.':
        '{} alte Datei(en) von Festplatte und aus der Datenbank löschen?\n'
        'Diese Aktion kann nicht rückgängig gemacht werden.',
    'Deleted {} file(s) from disk and {} DB entry(ies). Refreshing…':
        '{} Datei(en) von der Festplatte und {} DB-Eintrag/-Einträge gelöscht. Wird aktualisiert…',

    # --- Models (PreviewTableModel / TaskTableModel) ---
    'Filename': 'Dateiname',
    'Course': 'Kurs',
    'Size': 'Größe',
    'Status': 'Status',
    'Always Skipped': 'Immer übersprungen',
    'Modified': 'Geändert',
    'Moved': 'Verschoben',
    'New': 'Neu',
    'Progress': 'Fortschritt',
    'Skipped': 'Übersprungen',

    # --- SSOTokenWorker ---
    'Could not extract token from SSO response.':
        'Token konnte nicht aus der SSO-Antwort extrahiert werden.',

    # --- SettingsPage ---
    'Language': 'Sprache',
    'System default': 'Systemstandard',
    'Language of the interface. Changes apply after a restart.':
        'Sprache der Benutzeroberfläche. Änderungen werden nach einem Neustart wirksam.',
    'Interface Language:': 'Oberflächensprache:',
    'Paths': 'Pfade',
    'Browse...': 'Durchsuchen…',
    'Download Path:': 'Download-Pfad:',
    'Config/DB Path:': 'Konfig-/DB-Pfad:',
    'Performance': 'Leistung',
    'Maximum number of concurrent API requests to the Moodle server.':
        'Maximale Anzahl gleichzeitiger API-Anfragen an den Moodle-Server.',
    'Max Parallel API Calls:': 'Max. parallele API-Aufrufe:',
    'Maximum number of files to download simultaneously.':
        'Maximale Anzahl gleichzeitig herunterzuladender Dateien.',
    'Max Parallel Downloads:': 'Max. parallele Downloads:',
    'Maximum number of concurrent yt-dlp video downloads.':
        'Maximale Anzahl gleichzeitiger yt-dlp-Videodownloads.',
    'Max Parallel yt-dlp:': 'Max. parallele yt-dlp:',
    ' bytes': ' Bytes',
    'Size of each download chunk in bytes. Larger values may improve speed.':
        'Größe jedes Download-Blocks in Bytes. Größere Werte können die Geschwindigkeit erhöhen.',
    'Download Chunk Size:': 'Download-Blockgröße:',
    'Download Filters': 'Download-Filter',
    'Comma-separated list of file extensions to exclude from downloads.':
        'Kommagetrennte Liste von Dateiendungen, die vom Download ausgeschlossen werden.',
    'Exclude Extensions:': 'Endungen ausschließen:',
    ' MB': ' MB',
    'Maximum file size to download in MB. Set to 0 for unlimited.':
        'Maximale herunterzuladende Dateigröße in MB. 0 für unbegrenzt.',
    'Max File Size:': 'Max. Dateigröße:',
    'Domain Filtering': 'Domain-Filterung',
    'Download Domains Whitelist (one per line, leave empty to allow all):':
        'Domain-Whitelist für Downloads (eine pro Zeile, leer lassen, um alle zu erlauben):',
    'Only download files from these domains. Leave empty to allow all.':
        'Nur Dateien von diesen Domains herunterladen. Leer lassen, um alle zu erlauben.',
    'Download Domains Blacklist (one per line):': 'Domain-Blacklist für Downloads (eine pro Zeile):',
    'Never download files from these domains.': 'Niemals Dateien von diesen Domains herunterladen.',
    'SSL / Misc': 'SSL / Sonstiges',
    'Allow Insecure SSL': 'Unsicheres SSL erlauben',
    'Allow connections to unpatched servers with old SSL.':
        'Verbindungen zu ungepatchten Servern mit altem SSL erlauben.',
    'Use All Ciphers': 'Alle Verschlüsselungsverfahren verwenden',
    'Allow insecure ciphers for the connection.': 'Unsichere Verschlüsselungsverfahren für die Verbindung erlauben.',
    'Skip Certificate Verification': 'Zertifikatsprüfung überspringen',
    'Do not verify TLS certificates. Use only in non-production environments.':
        'TLS-Zertifikate nicht überprüfen. Nur in Nicht-Produktivumgebungen verwenden.',
    'Restrict Filenames (ASCII only)': 'Dateinamen einschränken (nur ASCII)',
    'Replace non-ASCII characters in filenames with ASCII equivalents.':
        'Nicht-ASCII-Zeichen in Dateinamen durch ASCII-Entsprechungen ersetzen.',
    'Verbose Logging': 'Ausführliche Protokollierung',
    'Enable debug-level logging for more detailed output.':
        'Protokollierung auf Debug-Ebene für ausführlichere Ausgaben aktivieren.',
    'Save Settings': 'Einstellungen speichern',
    'Select Download Directory': 'Download-Verzeichnis auswählen',
    'Select Config/Database Directory': 'Konfig-/Datenbankverzeichnis auswählen',
    'Settings saved successfully.\n\nRestart Moodle-DL to apply the new language.':
        'Einstellungen erfolgreich gespeichert.\n\nMoodle-DL neu starten, um die neue Sprache anzuwenden.',
    'Settings saved successfully.': 'Einstellungen erfolgreich gespeichert.',
}


def main() -> int:
    tree = ET.parse(TS_PATH)
    root = tree.getroot()
    translated = 0
    missing = []
    for ctx in root.findall('context'):
        for msg in ctx.findall('message'):
            source = msg.findtext('source')
            trans = msg.find('translation')
            if source in DE:
                trans.text = DE[source]
                if 'type' in trans.attrib:
                    del trans.attrib['type']  # mark as finished
                translated += 1
            else:
                missing.append((ctx.findtext('name'), source))

    tree.write(TS_PATH, encoding='utf-8', xml_declaration=True)
    print(f'Translated {translated} message(s).')
    if missing:
        print(f'WARNING: {len(missing)} source string(s) without a German translation:')
        for name, src in missing:
            print(f'  [{name}] {src!r}')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
