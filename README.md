<div align="center">
    <br>
    <h2>Moodle-DL</h2>
    Because manually downloading all the course files every few days is just <del>way too easy</del> inefficient.
    <br>
    Built with ❤︎
</div>

---


`moodle-dl` is a console application that can download all the files from your Moodle courses that are necessary for your daily study routine. Furthermore, moodle-dl can notify you about various activities on your Moodle server. Notifications can be sent to Telegram, XMPP and Mail. The current implementation includes: 

- Download files, assignments including submissions, forums, workshops, lessons, quizzes, descriptions, as well as external links (OpenCast, Youtube, Sciebo, Owncloud, Kaltura, Helixmedia, Google drive,... videos/files).
- Notifications about all downloaded files
- Text from your Moodle courses (like pages, descriptions or forum posts) will be directly attached to the notifications, so you can read them directly in your messaging app.
- A configuration wizard is also included, allowing all settings to be made very easily.
- Running moodle-dl again will only download files that have not been downloaded yet. Do not miss any files, if files are deleted online, they are still available offline.
- It is possible to download Moodle courses you are enrolled in, as well as courses that are publicly visible to you.

Discussions about the development take place mainly on [Github](https://github.com/C0D3D3V/Moodle-DL/issues), but also on [Discord](https://discord.gg/HNg7CsqEnZ).

## 🚀 Setup
[![Deploy with Docker](https://img.shields.io/badge/deploy%20with-docker-0db7ed)](https://github.com/C0D3D3V/Moodle-DL/wiki/Run-with-Docker)
[![latest packaged version(s)](https://repology.org/badge/latest-versions/moodle-dl.svg)](https://repology.org/project/moodle-dl/versions)
[![Packaging status](https://repology.org/badge/tiny-repos/moodle-dl.svg)](https://repology.org/project/moodle-dl/versions)
[![Discord Shield](https://discordapp.com/api/guilds/969140782655242281/widget.png?style=shield)](https://discord.gg/HNg7CsqEnZ)

1. Install [Python](https://www.python.org/) >=3.7
2. Install [ffmpeg](https://github.com/C0D3D3V/Moodle-DL/wiki/Installing-ffmpeg)
3. Run `pip install moodle-dl` as administrator. </br>
    <sup>(To upgrade from an older Version use `pip install -U moodle-dl` instead)</sup>
4. **[Windows only]** 
<details>
<summary markdown="span">If step 3 failed, you may need to do additional steps. Click here to see the additional Instructions</summary>


You may need to install [Visual C++ compiler for Python](https://wiki.python.org/moin/WindowsCompilers#Microsoft_Visual_C.2B-.2B-_14.2_standalone:_Build_Tools_for_Visual_Studio_2019_.28x86.2C_x64.2C_ARM.2C_ARM64.29) to build all the dependencies successfully: 

  - Download and Install Microsoft [Build Tools for Visual Studio 2019 from here](https://aka.ms/vs/16/release/vs_buildtools.exe)
  - In Build tools, install C++ build tools and ensure the latest versions of MSVCv142 - VS 2019 C++ x64/x86 build tools and Windows 10 SDK are checked.
  - In some very edge cases, you may also need [Visual C++ 14.0 Redistrubution Packages](https://aka.ms/vs/17/release/vc_redist.x64.exe)
</details>

If you run the program on **Windows**, please use [Powershell or CMD](https://www.isunshare.com/windows-10/5-ways-to-open-windows-powershell-in-windows-10.html). Please do not use a mintty like MINGW or similar.

5. Run `moodle-dl --help` to see all available options.

 

### Usage
Moodle-dl uses the Moodle mobile API. If your Moodle does not allow access via [the Moodle app](https://download.moodle.org/mobile/), Moodle-dl will not be able to connect to your Moodle.

If you don't want moodle-dl to use the current working directory, then you should set the `--path` option on all commands.

- `moodle-dl --init`
    - Create an initial configuration. A CLI configuration wizard will lead you through the initial configuration.
    - If you have to log in with Single Sign On (SSO, something like Shibboleth or OAuth2), you can set the option `--sso` additionally.
    - If at any point in time, the saved token gets rejected by Moodle use `moodle-dl --new-token` instead
    - To automate the login you can use the additional options `--username` and `--password` or `--token`.

- `moodle-dl`
    - After configuring moodle-dl, this command is sufficient to download all files from your Moodle account and notify you about the result.

- `moodle-dl --config`
    - A CLI configuration wizard will lead you through the additional configuration of moodle-dl.
    - You can start the wizard after the initial configuration if you want to change any of the settings.
    - The wizard allows you to change nearly all settings of moodle-dl
      - select the courses that will be downloaded
      - rename each course individually
      - decide if subfolders should be created inside a course folder
      - set whether submissions (files uploaded to assignments by yourself or a teacher), descriptions, links inside descriptions, databases, quizzes, lessons, workshops and forum discussions should be downloaded
      - set if external files should be downloaded (files like Youtube videos)
      - set if files on moodle that require a cookie should be downloaded
      - to add extra courses to your download list which you can see but you are not enrolled in, check out [this wiki entry](https://github.com/C0D3D3V/Moodle-DL/wiki/Download-public-courses)
    - Not all moodle-dl settings are available in the CLI configuration wizard for configuration, see [the wiki](https://github.com/C0D3D3V/Moodle-DL/wiki/Config.json) for more available options.

By default a private token is stored in the initial configuration, this is only needed for special Moodle modules that cannot be queried via the Moodle API. If no such module is available in your Moodle you are welcome to delete this token.

If you need help configuring telegram notifications [click here](https://github.com/C0D3D3V/Moodle-DL/wiki/Telegram-Notification)



### Notes
- Use a separate E-Mail/XMPP - Account for sending out the notifications, as its login data is saved in cleartext.
- The Login-Information for your Moodle-Account is secure, it isn't saved in any way. Only a Login-Token is saved.
- Your Moodle token is stored in the configuration file (`config.json`). Be careful that no unauthorized person reads this file, especially the token must not be given to an unauthorized person, this can cause a lot of trouble.
- The `privatetoken` can be used to create a cookie for your Moodle account. A Cookie is what is used to tell Moodle that you are logged in. The `cookie.txt` always keeps a valid cookie for you, take great care of this file, if it falls into the wrong hands someone can take over your entire Moodle account. This feature is only important for Moodles with plugins installed that are not supported by the Moodle app. If you do not want to generate cookies, remove the `privatetoken` from the `config.json`.


### Alternativ downloader

[webeep-sync](https://github.com/toto04/webeep-sync#english-version)
- Written with node.js
- Has a nice GUI that allows you to sync your courses easily
- Is only built for the moodle of the Polytechnic University of Milan 

[syncMyMoodle](https://github.com/Romern/syncMyMoodle)
- Has pretty much the same goals as moodle-dl
- Is only built for the moodle of the Rhenish-Westphalian Technical University (RWTH) Aachen

[edu-sync](https://github.com/mkroening/edu-sync)
- Is built in Rust and therefore quite fast

[moodle-buddy](https://github.com/marcelreppi/moodle-buddy)
- Plugin for Firefox and Chrome
- Mass file download and notification functionality for the Moodle

[moodle-downloader](https://github.com/harsilspatel/moodle-downloader)
- A chrome extension for batch downloading Moodle resources

[discord-moodle-bot](https://github.com/tjarbo/discord-moodle-bot)
- Discord Notification Service for your moodle courses

If someone wants to link another downloader here, which offers e.g. functions that moodle-dl does not offer, feel free to open an issue. 


---




## 🏆 Contributing
You would like to become a maintainer of this project? Then contact me!

Do you have a great new feature idea or just want to be part of the project? Awesome! Every contribution is welcome! If you want to find out more about how to contribute to the project, please check out our [CONTRIBUTING.md](CONTRIBUTING.md)!


## ⚖️ License
This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details