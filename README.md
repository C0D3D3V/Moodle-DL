# Moodle Downloader 2

> Because manually downloading all the course files every few days is just ~~way too easy~~ inefficient.


### Features
- Watch your Moodle account for any added or changed files in your enrolled courses.
- Optionally get notified via mail or [Telegram](https://telegram.org/apps) about these changes.
- Save yourself precious time through all these nice features.
- Do not miss any files, if files are deleted online, they are still available offline.


### Setup
1. You can take the [latest release from here](https://github.com/C0D3D3V/Moodle-Downloader-2/releases) or clone the master branch directly (be warned that the master branch is less stable than the releases).
2. Install [Python](https://www.python.org/) >=3.6
3. Verify that `python --version` shows a version equal to or higher then 3.6
    Otherwise use [pyenv](https://github.com/pyenv/pyenv#installation) to install the newest version
4. `pip install -r requirements.txt` (Linux users should first check if the requirements are available via there package manager)
5. run `python main.py --init`  

On some operating systems the program has to run with `python3` instead of `python`, try it yourself. The same applies to `pip3`.
If you run this program in mintty (MINGW or something similar), try running Python like this `winpty python`.

### Usage
- `python main.py`
    - Fetches the current state of your Moodle Account, saves it and detects any changes.
    - If configured, it also sends out a mail-notification.
    - It prints the current status into the console 
	- It writes a more detailed log into `MoodleDownloader.log` for debug purpose.
- `python main.py --init`
    - Guides you trough the configuration of the software, including the activation of mail-notifications and obtainment of a login-token for your Moodle-Account.
    - After the necessary configuration, further additional configurations can be made. 
	- It does not fetch the current state of your Moodle-Account.
    - If you have to log in with Single Sign On (SSO), you can set the option `--sso` additionally.
- `python main.py --config`
    - Guides you through the additional configuration of the software.
    - This includes the selection of the courses to be downloaded and various configuration options for these courses.
    - You can rename each course individually and decide if a folder structure should be created.
    - You can set whether submissions (files uploaded to Assignments by yourself or a teacher) should be downloaded.
    - You can choose to download descriptions of Moodle courses. 
    - It does not fetch the current state of your Moodle-Account.
- `python main.py --new-token`
    - Overrides the login-token with a newly obtained one.
    - It does not fetch the current state of your Moodle-Account.
    - Use it if at any point in time, for whatever reason, the saved token gets rejected by Moodle.
    - It does not affect the rest of the config.
    - It prints all information into the console.
- `python main.py --change-notification-mail`
    - Activate/deactivate/change the settings for receiving notifications via e-mail.
    - It does not affect the rest of the config.
    - It prints all information into the console.
- `python main.py --change-notification-telegram`
    - Activate/deactivate/change the settings for receiving notifications via Telegram.
    - It does not affect the rest of the config.
    - It prints all information into the console.
    - Help with setting up Notifications via Telegram will be here soon
- `python main.py --manage-database`
    - To manage the offline database.
    - It allows you to delete entries from the database that are no longer available locally so that they can be downloaded again.


### Options
Options can be combined with all the actions mentioned above.
- `--path PATH`
    - This option can be useful if you want to save the downloaded files in a directory other than the current working directory (the directory where you run the script). 
    - Sets the location of the configuration, logs and downloaded files. 
    - `PATH` must be an existing directory in which you have read and write access.
    - Default: current working directory

- `--skip-cert-verify`
    - This flag is used to skip the certification verification while sending requests to Moodle.
    - Warning: This might lead to security flaws and should only be used in non-production environments.
    - Default: False

- `--without-downloading-files`
    - This flag is used to skip the downloading of files.
    - This allows the local database to be updated to the latest version of Moodle without having to download all files.

- `--sso`
    - This flag is used to indicate that a Single Sign On (SSO) login to your Moodle is required. 
    - Can be combined with `--init` and `--new-token`.




### Notes
- Use a separate E-Mail - Account for sending out the notifications, as its login data is saved in cleartext.
- The Login-Information for your Moodle-Account is secure, it isn't saved in any way. Only a Login-Token is saved.


---


### Contributing
I'm open for all forks, feedback and Pull Requests ;)


### License
This project is licensed under the terms of the *GNU General Public License v3.0*. For further information, please look [here](http://choosealicense.com/licenses/gpl-3.0/) or [here<sup>(DE)</sup>](http://www.gnu.org/licenses/gpl-3.0.de.html).

To mention here is, that this project is based on a project from [LucaVazz](https://github.com/LucaVazz/DualisWatcher). He did a very great job creating a "DualisWatcher".  
