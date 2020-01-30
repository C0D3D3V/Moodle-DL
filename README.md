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
3. `pip3 install -r requirements.txt`
4. run `python3 main.py --init`


### Usage
- `python main.py`
    - Fetches the current state of your Moodle Account, saves it and detects any changes.
    - If configured, it also sends out a mail-notification.
    - It prints the current status into the console 
	- It writes a more detailed log into `MoodleDownloader.log` for debug purpose.
- `python main.py --init`
    - Guides you trough the configuration of the software, including the activation of mail-notifications and obtainment of a login-token for your Moodle-Account.
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


**I do not want to download all courses I am enrolled in.**

To avoid downloading all the Moodle courses you are enrolled in, you can add the attribute `dont_download_course_ids` to config.json.
First you have to find out the id of the course you no longer want to download.
The id is usually located at the end of the course URL, as with this one: http://moodle.uni.com/course/view.php?id=12122

Then you can open the automatically generated config.json with a text editor. For example, to prevent courses `12122` and `42` from being downloaded, add the attribute as in this example.
```
{
    ...,
    "moodle_path": "/",
    "dont_download_course_ids": [42, 12122]
}
```


**I also want to download the submissions and the feedback files.**

Moodle does not provide an interface to download information from all submissions of a course at once. Therefore it can be slow to monitor changes of submissions. For this reason the option to download submissions and feedback files is optional.

For me it takes about 10 seconds for 30 assignments to download all information of the submissions.

__Warning!__ If this option is deactivated after activation, the submission entries of the database are set to `Deleted`. This means that the downloader forgets the files and if this option is activated again, all files will be downloaded again. 

To download submissions and feedback files you have to set the variable `download_submissions` to `true` in the configuration, as in the following example:
```
{
    ...,
    "moodle_path": "/",
    "download_submissions": true
}
```







### Notes
- Use a separate E-Mail - Account for sending out the notifications, as its login data is saved in cleartext.
- The Login-Information for your Moodle-Account is secure, it isn't saved in any way. Only a Login-Token is saved.


---


### Contributing
I'm open for all forks, feedback and Pull Requests ;)


### License
This project is licensed under the terms of the *GNU General Public License v3.0*. For further information, please look [here](http://choosealicense.com/licenses/gpl-3.0/) or [here<sup>(DE)</sup>](http://www.gnu.org/licenses/gpl-3.0.de.html).

To mention here is, that this project is based on a project from [LucaVazz](https://github.com/LucaVazz/DualisWatcher). He did a very great job creating a "DualisWatcher".  
