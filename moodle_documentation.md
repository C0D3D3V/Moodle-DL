# Moodle: Structural Documentation
 
 [Also check out the Wiki](https://github.com/C0D3D3V/Moodle-Downloader-2/wiki)

## Usage

1. core_webservice_get_site_info (since version 2.1)     
* get the userid (and all available functions)

2.	core_enrol_get_users_courses (since version 2.0) 	 
* get list of course ids that a user is enrolled in (if you are allowed to see that)

The result is an array of elements that looks like this:
 ```
{
	"id":23569,
	"shortname":"Short name",
	"fullname":"Normaly same as shortname",
	"enrolledusercount":430,
	"idnumber":" (141022-WiSe19\/20) (WiSe19\/20)",
	"visible":1,
	"summary":"<p><HTML Summary<\/p>",
	"summaryformat":1,
	"format":"topics",
	"showgrades":true,
	"lang":"",
	"enablecompletion":true,
	"category":246,
	"progress":100,
	"startdate":1569448800,
	"enddate":1600984800
}
```

3.	core_course_get_contents (since version 2.2)		
* get course content (modules + web service file URLs)	

```
[
    {
        "id":323648,
        "name":"Allgemeines",
        "url":"https:\/\/moodle.uni.de\/m\/mod\/url\/view.php?id=949522", // on froum und url, but mostly only redirects to contents
        "visible":1,
        "summary":"",
        "summaryformat":1,
        "section":0,
        "hiddenbynumsections":0,
        "uservisible":true,
        "modules":[  
            {
                "id":949513,
                "name":"\n\n\nLiebe Studierende,\nwillkommen im Moodle-Kur...",
                "instance":109599,
                "description":"<div class=\"no-overflow\">HTML Description<\/div>",
                "visible":1,
                "uservisible":true,
                "visibleoncoursepage":1,
                "modicon":"https:\/\/moodle.uni.de\/m\/theme\/image.php\/boost_campus\/label\/1576236086\/icon",
                
                "modname":"label",      // Alternative: "forum", "url", "folder", "resource", "quiz"

                "modplural":"Textfelder",
                "indent":0,
                 "contents":[   // if "url" or "resource" or "folder"
	               { 
	                  "type":"url",
	                  "filename":"Webseite der Veranstaltung Netzsicherheit 1",
	                  "filepath":null,
	                  "filesize":0,
	                  "fileurl":"https:\/\/www.nds.uni.de\/teaching\/lectures\/664\/",		// the real url
	                  "timecreated":null,
	                  "timemodified":1411680382,
	                  "sortorder":null,
	                  "userid":null,
	                  "author":null,
	                  "license":null
	               },
	               { 
	                  "type":"file",
	                  "filename":"01_Grundlagen.pdf",
	                  "filepath":"\/",
	                  "filesize":3809147,
	                  "fileurl":"https:\/\/moodle.uni.de\/m\/webservice\/pluginfile.php\/1452961\/mod_resource\/content\/4\/01_Grundlagen.pdf?forcedownload=1",
	                  "timecreated":1571408009,
	                  "timemodified":1571408019,
	                  "sortorder":1,
	                  "mimetype":"application\/pdf",
	                  "isexternalfile":false,
	                  "userid":25394,
	                  "author":"Some Dude",
	                  "license":"allrightsreserved"
	               }
	               // contents
	             ]
            },
            {  // assign
               "id":1002989,
               "url":"https:\/\/moodle.uni.de\/m\/mod\/assign\/view.php?id=1002989",
               "name":"Dateiabgabe: Aufgabe 3",
               "instance":20670,
               "visible":1,
               "uservisible":true,
               "visibleoncoursepage":1,
               "modicon":"https:\/\/moodle.uni.de\/m\/theme\/image.php\/boost_campus\/assign\/1576236086\/icon",
               "modname":"assign",
               "modplural":"Aufgaben",
               "indent":1
            },...
            // Modules
        ]
    },
    //Sections
]
```

3. Download the files given in the `fileurl` Attributes with the token as an additional parameter.

4. mod_assign_get_assignments (since version 2.4)
* Returns the courses and assignments for the users capability  (Basically the files stored in assignments (except the submissions))
* set courseid[0] to a course id to get only one course instead of all enrolled ones

```
{
   "courses":[
      {
         "id":23569,
         "fullname":"Einf\u00fchrung in die Kryptographie (141022-WiSe19\/20)",
         "shortname":"Einf\u00fchrung in die Kryptographie (141022-WiSe19\/20)",
         "timemodified":1569934149,
         "assignments":[
            {
               "id":20711,
               "cmid":1004737,
               "course":23569,
               "name":"\u00dcbung 7 (aktualisiert 29.11.2019, 20 Uhr)",
               "nosubmissions":0,
               "submissiondrafts":0,
               "sendnotifications":0,
               "sendlatenotifications":0,
               "sendstudentnotifications":1,
               "duedate":1575544500,
               "allowsubmissionsfromdate":1574945100,
               "grade":100,
               "timemodified":1575053543,
               "completionsubmit":1,
               "cutoffdate":1575544500,
               "gradingduedate":0,
               "teamsubmission":1,
               "requireallteammemberssubmit":0,
               "teamsubmissiongroupingid":1106,
               "blindmarking":0,
               "revealidentities":0,
               "attemptreopenmethod":"none",
               "maxattempts":-1,
               "markingworkflow":1,
               "markingallocation":0,
               "requiresubmissionstatement":1,
               "preventsubmissionnotingroup":1,
               "submissionstatement":"Diese Arbeit ist meine eigene Leistung. Sofern ich fremde Quellen verwendet habe, sind die Stellen entsprechend gekennzeichnet.",
               "submissionstatementformat":1,
               "configs":[
                  {
                     "plugin":"file",
                     "subtype":"assignsubmission",
                     "name":"enabled",
                     "value":"1"
                  },...
               ],
               "intro":"<p>Grundlagen von Erweiterungsk\u00f6rpern, Multiplikation und Inversion in GF(2<sup>m<\/sup>) und Addition, Subtraktion und Multiplikation in GF(p<sup>m<\/sup>).<\/p><p><br \/><\/p><p>Update (29.11.2019, 20 Uhr): Aufgabe 1 hinsichtlich Primzahlk\u00f6rper pr\u00e4zisiert.<\/p>",
               "introformat":1,
               "introfiles":[

               ],
               "introattachments":[
                  {
                     "filename":"Uebung_7_EK1_WS1920.pdf",
                     "filepath":"\/",
                     "filesize":50113,
                     "fileurl":"https:\/\/moodle.uni.de\/m\/webservice\/pluginfile.php\/1540276\/mod_assign\/introattachment\/0\/Uebung_7_EK1_WS1920.pdf",
                     "timemodified":1575053454,
                     "mimetype":"application\/pdf",
                     "isexternalfile":false
                  },...
               ]
            },...
         ]
      },...
   ],
   "warnings":[
      {
         "item":"module",
         "itemid":1016464,
         "warningcode":"1",
         "message":"No access rights in module context"
      },...
   ]
}
```

5. mod_assign_get_submission_status (since version 3.1)
User can submit files and the teacher can also submit feedback files. 
To get these call the function with this parameter `assignid` and `userid`
get_submissions would be nice to use, because it allows multiple assignments, but it doesn't work

```
{ 
   "lastattempt":{ 
      "submission":{ 
         "id":567446,
         "userid":686094,
         "attemptnumber":0,
         "timecreated":1579173255,
         "timemodified":1579173255,
         "status":"submitted",
         "groupid":0,
         "assignment":20957,
         "latest":1,
         "plugins":[ 
            { 
               "type":"file",
               "name":"Dateiabgabe",
               "fileareas":[ 
                  { 
                     "area":"submission_files",
                     "files":[ 

                     ]
                  }
               ]
            },
            { 
               "type":"comments",
               "name":"Abgabekommentare"
            }
         ]
      },
      "teamsubmission":{ 
         "id":567394,
         "userid":0,
         "attemptnumber":0,
         "timecreated":1579169954,
         "timemodified":1579173255,
         "status":"submitted",
         "groupid":42031,
         "assignment":20957,
         "latest":1,
         "plugins":[ 
            { 
               "type":"file",
               "name":"Dateiabgabe",
               "fileareas":[ 
                  { 
                     "area":"submission_files",
                     "files":[ 
                        { 
                           "filename":"HA11.pdf",
                           "filepath":"\/",
                           "filesize":78968,
                           "fileurl":"https:\/\/moodle.uni.de\/m\/webservice\/pluginfile.php\/1555802\/assignsubmission_file\/submission_files\/567394\/HA11.pdf",
                           "timemodified":1579173255,
                           "mimetype":"application\/pdf",
                           "isexternalfile":false
                        }
                     ]
                  }
               ]
            },
            { 
               "type":"comments",
               "name":"Abgabekommentare"
            }
         ]
      },
      "submissiongroup":42031,
      "submissiongroupmemberswhoneedtosubmit":[ 

      ],
      "submissionsenabled":true,
      "locked":false,
      "graded":true,
      "canedit":false,
      "caneditowner":false,
      "cansubmit":false,
      "extensionduedate":0,
      "blindmarking":false,
      "gradingstatus":"released",
      "usergroups":[ 
         42031
      ]
   },
   "feedback":{ 
      "grade":{ 
         "id":282388,
         "assignment":20957,
         "userid":686094,
         "attemptnumber":0,
         "timecreated":1579263089,
         "timemodified":1579263090,
         "grader":90976,
         "grade":"35.00000"
      },
      "gradefordisplay":"35,00&nbsp;\/&nbsp;100,00",
      "gradeddate":1579263090,
      "plugins":[ 
         { 
            "type":"comments",
            "name":"Feedback als Kommentar",
            "editorfields":[ 
               { 
                  "name":"comments",
                  "description":"Feedback als Kommentar",
                  "text":"<p>1) 30\/40<br>2) 5\/20<br>3) 0\/40<br><\/p>",
                  "format":0
               }
            ]
         },
         { 
            "type":"editpdf",
            "name":"Anmerkungen im PDF",
            "fileareas":[ 
               { 
                  "area":"download",
                  "files":[ 
                     { 
                        "filename":"User_8894397_0.pdf",
                        "filepath":"\/",
                        "filesize":158448,
                        "fileurl":"https:\/\/moodle.uni.de\/m\/webservice\/pluginfile.php\/1555802\/assignfeedback_editpdf\/download\/282388\/User_8894397_0.pdf",
                        "timemodified":1579263090,
                        "mimetype":"application\/pdf",
                        "isexternalfile":false
                     }
                  ]
               }
            ]
         },
         { 
            "type":"file",
            "name":"Feedbackdateien",
            "fileareas":[ 
               { 
                  "area":"feedback_files",
                  "files":[ 

                  ]
               }
            ]
         },
         { 
            "type":"offline",
            "name":"Offline-Bewertungstabelle"
         }
      ]
   },
   "warnings":[ 

   ]
}
```


