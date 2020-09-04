# Moodle: Structural Documentation
 
 [Also check out the Wiki](https://github.com/C0D3D3V/Moodle-Downloader-2/wiki)

## Usage


1. mod_assign_get_assignments (since version 2.4)
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

2. mod_assign_get_submission_status (since version 3.1)
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


