<div align="center">
    <br>
    <h2>Moodle Downloader 2</h2>
    <small>Because manually downloading all the course files every few days is just <del>way too easy</del> inefficient.</small> 
    <br>
    <small>Built with ❤︎</small>
</div>

---


`moodle-dl` is a console application that can download all the files from your Moodle courses that are necessary for your daily study routine. Furthermore, moodle-dl can notify you about various activities on your Moodle server. Notifications can be sent to Telegram, XMPP and Mail. The current implementation includes: 

- Download files, assignments including submissions, forums, workshops, lessons, quizzes, descriptions, as well as external links.
- Notifications about all downloaded files
- Text from your Moodle courses (like pages, descriptions or forum-posts) will be directly attached to the notifications, so you can read them directly in your messaging app.
- A configuration wizard is also included, allowing all settings to be made very easily.
- Running moodle-dl again will only download files that have not been downloaded yet. Do not miss any files, if files are deleted online, they are still available offline.
- It is possible to download Moodle courses you are enrolled in, as well as courses that are publicly visible to you.

Development discussions happen on [Discord in the developer channel](https://discord.gg/HNg7CsqEnZ).

## 🚀 Setup
[![Deploy with Docker](https://img.shields.io/badge/deploy%20with-docker-0db7ed)](https://github.com/C0D3D3V/Moodle-Downloader-2/wiki/Run-with-Docker)
[![latest packaged version(s)](https://repology.org/badge/latest-versions/moodle-dl.svg)](https://repology.org/project/moodle-dl/versions)
[![Packaging status](https://repology.org/badge/tiny-repos/moodle-dl.svg)](https://repology.org/project/moodle-dl/versions)
[![Discord Shield](https://discordapp.com/api/guilds/969140782655242281/widget.png?style=shield)](https://discord.gg/HNg7CsqEnZ)

1. Install [Python](https://www.python.org/) >=3.7
2. Install [ffmpeg](https://github.com/C0D3D3V/Moodle-Downloader-2/wiki/Installing-ffmpeg)
3. Run `pip install moodle-dl` as administrator. </br>
    <sup>(To upgrade from an older Version use `pip install -U moodle-dl` instead)</sup>
4. **[Windows only]** If step 3 failed, You may need to install [Visual C++ compiler for Python](https://wiki.python.org/moin/WindowsCompilers#Microsoft_Visual_C.2B-.2B-_14.2_standalone:_Build_Tools_for_Visual_Studio_2019_.28x86.2C_x64.2C_ARM.2C_ARM64.29) to build all the dependencies successfully: 
  - Download and Install Microsoft [Build Tools for Visual Studio 2019 from here](https://aka.ms/vs/16/release/vs_buildtools.exe)
  - In Build tools, install C++ build tools and ensure the latest versions of MSVCv142 - VS 2019 C++ x64/x86 build tools and Windows 10 SDK are checked.
  - In some very edge cases, you may also need [Visual C++ 14.0 Redistrubution Packages](https://aka.ms/vs/17/release/vc_redist.x64.exe)

If you run the program on **Windows**, please use [Powershell or CMD](https://www.isunshare.com/windows-10/5-ways-to-open-windows-powershell-in-windows-10.html). Please do not use a mintty like MINGW or similar.

5. Run `moodle-dl --init` in the desired download directory.
6. Run `moodle-dl --help` to see all options

 

### Usage
- `moodle-dl`
    - Fetches the current state of your Moodle Account, saves it and detects any changes.
    - If configured, it also sends out notifications.
    - It prints the changes into the console.
- `moodle-dl --init`
    - Guides you through the configuration of the software, including the activation of notifications and obtainment of a login-token for your Moodle-Account.
    - After the necessary configuration, further additional configurations can be made. 
    - If you have to log in with Single Sign On (SSO), you can set the option `--sso` additionally.
- `moodle-dl --config`
    - Guides you through the additional configuration of the software.
    - The guide allows you to
      - select the courses that will be downloaded.
      - rename each course individually.
      - decide if subfolders should be created inside a course folder.
      - set whether submissions (files uploaded to assignments by yourself or a teacher), descriptions, links inside descriptions, databases, quizzes, lessons, workshops and forum discussions should be downloaded.
      - set if external linked files should be downloaded (files like youtube videos).
      - set if files on moodle that require a cookie should be downloaded.
      - to add extra courses to your download list which you can see but you are not enrolled in, check out [this wiki entry](https://github.com/C0D3D3V/Moodle-Downloader-2/wiki/Download-public-courses).
- `moodle-dl --new-token`
    - Overrides the login-token with a newly obtained one.
    - The script will ask for credentials unless they are explicitly specify with the options `--username` and `--password`
    - Use it if at any point in time, for whatever reason, the saved token gets rejected by Moodle.
- `moodle-dl --change-notification-mail`
    - Activate/deactivate/change the settings for receiving notifications via e-mail.
- `moodle-dl --change-notification-telegram`
    - Activate/deactivate/change the settings for receiving notifications via Telegram.
    - Click [here for help](https://github.com/C0D3D3V/Moodle-Downloader-2/wiki/Telegram-Notification) in setting up telegram notifications
- `moodle-dl --change-notification-xmpp`
    - Activate/deactivate/change the settings for receiving notifications via XMPP.
- `moodle-dl --manage-database`
    - To manage the offline database.
    - It allows you to delete entries from the database that are no longer available locally so that they can be downloaded again.
- `moodle-dl --delete-old-files`
    - To delete old versions of updated files.
- `moodle-dl --add-all-visible-courses`
    - To add all courses visible to the moodle user to the configuration file.
- `moodle-dl --version`
    - Print program version and exit
- `moodle-dl --log-responses`
    - To generate a `responses.log` file, in which all JSON responses from Moodles are logged along with the requested URL
    - This is for development and debugging purposes only. The log file may contain private data.

### Options
Options can be combined with all the actions mentioned above.
- `--path PATH`
    - This option can be useful if you want to save the downloaded files in a directory other than the current working directory (the directory where you run the script). 
    - Sets the location of the configuration, logs and downloaded files. 
    - `PATH` must be an existing directory in which you have read and write access.
    - Default: current working directory
- `--threads INT`
    - Overwrites the number of download threads. (default: 5)
- `--verbose`
    - Print various debugging information into the `MoodleDownloader.log` file.
- `--username USERNAME`
    - Can be used to automate the `--new-token` process. 
    - Specify username to skip the query when creating a new token.
- `--password PASSWORD`
    - Can be used to automate the `--new-token` process. 
    - Specify password to skip the query when creating a new token.
    - If the password contains special characters like spaces you can enclose it in quotation marks
- `--max-path-length-workaround`
    - If this flag is set, all path are made absolute in order to work around the max_path limitation on Windows.
    - To use relative paths on Windows you should [disable the max_path limitation](https://docs.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation?tabs=cmd).
    - Default: False
- `--skip-cert-verify`
    - This flag is used to skip the certification verification while sending requests to Moodle and all other websites.
    - Warning: This might lead to security flaws and should only be used in non-production environments.
    - Default: False
- `--ignore-ytdl-errors`
    - If this option is set, errors that occur when downloading with the help of yt-dlp are ignored. Thus, no further attempt will be made to download the file using yt-dlp. 
    - By default, yt-dlp errors are critical, so the download of the corresponding file will be aborted and when you run moodle-dl again, the download will be repeated.  
    - You can use this option if a download using yt-dlp fails repeatedly.
- `--without-downloading-files`
    - This flag is used to skip the downloading of files.
    - This allows the local database to be updated to the latest version of Moodle without having to download all files.
    - This can also be used to ignore recurring errors by adding the files that produce the errors to the database. So these files are not downloaded again.
- `--sso`
    - This flag is used to indicate that a Single Sign On (SSO) login to your Moodle is required. 
    - Can be combined with `--init` and `--new-token`.




### Notes
- Use a separate E-Mail/XMPP - Account for sending out the notifications, as its login data is saved in cleartext.
- The Login-Information for your Moodle-Account is secure, it isn't saved in any way. Only a Login-Token is saved.
- Your Moodle token is stored in the configuration file (`config.json`). Be careful that no unauthorized person reads this file, especially the token must not be given to an unauthorized person, this can cause a lot of trouble.
- The `privatetoken` can be used to create a cookie for your Moodle account. A Cookie is what is used to tell Moodle that you are logged in. The `cookie.txt` always keeps a valid cookie for you, take great care of this file, if it falls into the wrong hands someone can take over your entire Moodle account. This feature is only important for Moodles with plugins installed that are not supported by the Moodle app. If you do not want to generate cookies, remove the `privatetoken` from the `config.json`.

---


## 🏆 Contributing

Do you have a great new feature idea or just want to be part of the project ? Awesome! Every contribution is welcome! If you want to find out more about how to contribute to the project, please checkout our [CONTRIBUTING.md](CONTRIBUTING.md)!


## ⚖️ License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details