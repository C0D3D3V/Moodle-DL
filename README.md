# Moodle-Downloader

> Because manually downloading all the course files every few days is just ~~way too easy~~ inefficient.


### Disclaimer
*This software is provided "as is" and any expressed or implied warranties, including, but not limited to, the implied warranties of merchantability and fitness for a particular purpose are disclaimed. In no event shall the author or additional contributors be liable for any direct, indirect, incidental, special, exemplary, or consequential damages (including, but not limited to, procurement of substitute goods or services; loss of use, data, or profits; or business interruption).*


### Features
- Watch your Moodle account for any added or changed files in your enrolled courses.
- Optionally get notified via mail about these changes.
- Save yourself precious time through all these nice features.


### Setup
1. Install [Python](https://www.python.org/) >=3.5.3 `apt-get install python3 && apt-get install python3-pip`
2. Verify that `python --version` shows a version equal to or higher then 3.5.3
    Otherwise use [pyenv](https://github.com/pyenv/pyenv#installation) to install version 3.5.3
3. `pip3 install -r requirements.txt` (Linux users should first check if the requirements are available via there package manager)
4. run `python3 main.py --init`  

On some operating systems the program has to run with `python` instead of `python3`, try it yourself. The same applies to `pip3`.
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
    - You can set whether submissions (files uploaded to Assignments by yourself or a teacher) should be downloaded.
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

- `--without_downloading_files`
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
