# Moodle: Structural Documentation

## Important links
1. [Obtain Token](https://docs.moodle.org/dev/Creating_a_web_service_client)
2. [Use API Function](https://docs.moodle.org/dev/Web_service_API_functions)

## Usage

1. core_webservice_get_site_info	
* get the userid (and all available functions)

2.	core_enrol_get_users_courses	
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

3.	core_course_get_contents		
* get course content (modules + web service file urls)	

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
                
                "modname":"label",      // Alternative: "forum", "url", "resource", "quiz"

                "modplural":"Textfelder",
                "indent":0,
                 "contents":[   // if "url" or "resource"
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
            // Modules

        ]
    },
    //Sections
]
```
