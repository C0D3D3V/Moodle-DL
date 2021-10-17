moodle_html_header = '''
<!DOCTYPE html>

<html dir="ltr" lang="de" xml:lang="de">

<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <link rel="stylesheet" href="http://maxcdn.bootstrapcdn.com/font-awesome/latest/css/font-awesome.min.css">
    <script id="firstthemesheet"
        type="text/css">/** Required in order to fix style inclusion problems in IE with YUI **/</script>
    <link rel="stylesheet" type="text/css"
        href="https://moodle.ruhr-uni-bochum.de/theme/styles.php/boost/1633802793_1/all" />
    <script>
        //<![CDATA[
        var M = {}; M.yui = {};
        M.pageloadstarttime = new Date();
        M.cfg = { "wwwroot": "https:\\/\\/moodle.ruhr-uni-bochum.de", "sesskey": "roflAffe", "sessiontimeout": "28800", "themerev": "1633802793", "slasharguments": 1, "theme": "boost", "iconsystemmodule": "core\\/icon_system_fontawesome", "jsrev": "1633802793", "admin": "admin", "svgicons": true, "usertimezone": "Europa\\/London", "contextid": 104, "langrev": 1633946764, "templaterev": "1633802793" }; var yui1ConfigFn = function (me) { if (/-skin|reset|fonts|grids|base/.test(me.name)) { me.type = 'css'; me.path = me.path.replace(/\\.js/, '.css'); me.path = me.path.replace(/\\/yui2-skin/, '/assets/skins/sam/yui2-skin') } };
        var yui2ConfigFn = function (me) {
            var parts = me.name.replace(/^moodle-/, '').split('-'), component = parts.shift(), module = parts[0], min = '-min'; if (/-(skin|core)$/.test(me.name)) { parts.pop(); me.type = 'css'; min = '' }
            if (module) { var filename = parts.join('-'); me.path = component + '/' + module + '/' + filename + min + '.' + me.type } else { me.path = component + '/' + component + '.' + me.type }
        };
        YUI_config = { "debug": false, "base": "https:\\/\\/moodle.ruhr-uni-bochum.de\\/lib\\/yuilib\\/3.17.2\\/", "comboBase": "https:\\/\\/moodle.ruhr-uni-bochum.de\\/theme\\/yui_combo.php?", "combine": true, "filter": null, "insertBefore": "firstthemesheet", "groups": { "yui2": { "base": "https:\\/\\/moodle.ruhr-uni-bochum.de\\/lib\\/yuilib\\/2in3\\/2.9.0\\/build\\/", "comboBase": "https:\\/\\/moodle.ruhr-uni-bochum.de\\/theme\\/yui_combo.php?", "combine": true, "ext": false, "root": "2in3\\/2.9.0\\/build\\/", "patterns": { "yui2-": { "group": "yui2", "configFn": yui1ConfigFn } } }, "moodle": { "name": "moodle", "base": "https:\\/\\/moodle.ruhr-uni-bochum.de\\/theme\\/yui_combo.php?m\\/1633802793\\/", "combine": true, "comboBase": "https:\\/\\/moodle.ruhr-uni-bochum.de\\/theme\\/yui_combo.php?", "ext": false, "root": "m\\/1633802793\\/", "patterns": { "moodle-": { "group": "moodle", "configFn": yui2ConfigFn } }, "filter": null, "modules": { "moodle-core-event": { "requires": ["event-custom"] }, "moodle-core-chooserdialogue": { "requires": ["base", "panel", "moodle-core-notification"] }, "moodle-core-languninstallconfirm": { "requires": ["base", "node", "moodle-core-notification-confirm", "moodle-core-notification-alert"] }, "moodle-core-blocks": { "requires": ["base", "node", "io", "dom", "dd", "dd-scroll", "moodle-core-dragdrop", "moodle-core-notification"] }, "moodle-core-tooltip": { "requires": ["base", "node", "io-base", "moodle-core-notification-dialogue", "json-parse", "widget-position", "widget-position-align", "event-outside", "cache-base"] }, "moodle-core-formchangechecker": { "requires": ["base", "event-focus", "moodle-core-event"] }, "moodle-core-dragdrop": { "requires": ["base", "node", "io", "dom", "dd", "event-key", "event-focus", "moodle-core-notification"] }, "moodle-core-popuphelp": { "requires": ["moodle-core-tooltip"] }, "moodle-core-lockscroll": { "requires": ["plugin", "base-build"] }, "moodle-core-handlebars": { "condition": { "trigger": "handlebars", "when": "after" } }, "moodle-core-actionmenu": { "requires": ["base", "event", "node-event-simulate"] }, "moodle-core-notification": { "requires": ["moodle-core-notification-dialogue", "moodle-core-notification-alert", "moodle-core-notification-confirm", "moodle-core-notification-exception", "moodle-core-notification-ajaxexception"] }, "moodle-core-notification-dialogue": { "requires": ["base", "node", "panel", "escape", "event-key", "dd-plugin", "moodle-core-widget-focusafterclose", "moodle-core-lockscroll"] }, "moodle-core-notification-alert": { "requires": ["moodle-core-notification-dialogue"] }, "moodle-core-notification-confirm": { "requires": ["moodle-core-notification-dialogue"] }, "moodle-core-notification-exception": { "requires": ["moodle-core-notification-dialogue"] }, "moodle-core-notification-ajaxexception": { "requires": ["moodle-core-notification-dialogue"] }, "moodle-core-maintenancemodetimer": { "requires": ["base", "node"] }, "moodle-core_availability-form": { "requires": ["base", "node", "event", "event-delegate", "panel", "moodle-core-notification-dialogue", "json"] }, "moodle-backup-backupselectall": { "requires": ["node", "event", "node-event-simulate", "anim"] }, "moodle-backup-confirmcancel": { "requires": ["node", "node-event-simulate", "moodle-core-notification-confirm"] }, "moodle-course-util": { "requires": ["node"], "use": ["moodle-course-util-base"], "submodules": { "moodle-course-util-base": {}, "moodle-course-util-section": { "requires": ["node", "moodle-course-util-base"] }, "moodle-course-util-cm": { "requires": ["node", "moodle-course-util-base"] } } }, "moodle-course-management": { "requires": ["base", "node", "io-base", "moodle-core-notification-exception", "json-parse", "dd-constrain", "dd-proxy", "dd-drop", "dd-delegate", "node-event-delegate"] }, "moodle-course-categoryexpander": { "requires": ["node", "event-key"] }, "moodle-course-formatchooser": { "requires": ["base", "node", "node-event-simulate"] }, "moodle-course-dragdrop": { "requires": ["base", "node", "io", "dom", "dd", "dd-scroll", "moodle-core-dragdrop", "moodle-core-notification", "moodle-course-coursebase", "moodle-course-util"] }, "moodle-form-passwordunmask": { "requires": [] }, "moodle-form-dateselector": { "requires": ["base", "node", "overlay", "calendar"] }, "moodle-form-shortforms": { "requires": ["node", "base", "selector-css3", "moodle-core-event"] }, "moodle-question-searchform": { "requires": ["base", "node"] }, "moodle-question-chooser": { "requires": ["moodle-core-chooserdialogue"] }, "moodle-question-preview": { "requires": ["base", "dom", "event-delegate", "event-key", "core_question_engine"] }, "moodle-availability_completion-form": { "requires": ["base", "node", "event", "moodle-core_availability-form"] }, "moodle-availability_date-form": { "requires": ["base", "node", "event", "io", "moodle-core_availability-form"] }, "moodle-availability_grade-form": { "requires": ["base", "node", "event", "moodle-core_availability-form"] }, "moodle-availability_group-form": { "requires": ["base", "node", "event", "moodle-core_availability-form"] }, "moodle-availability_grouping-form": { "requires": ["base", "node", "event", "moodle-core_availability-form"] }, "moodle-availability_profile-form": { "requires": ["base", "node", "event", "moodle-core_availability-form"] }, "moodle-mod_assign-history": { "requires": ["node", "transition"] }, "moodle-mod_quiz-toolboxes": { "requires": ["base", "node", "event", "event-key", "io", "moodle-mod_quiz-quizbase", "moodle-mod_quiz-util-slot", "moodle-core-notification-ajaxexception"] }, "moodle-mod_quiz-autosave": { "requires": ["base", "node", "event", "event-valuechange", "node-event-delegate", "io-form"] }, "moodle-mod_quiz-util": { "requires": ["node", "moodle-core-actionmenu"], "use": ["moodle-mod_quiz-util-base"], "submodules": { "moodle-mod_quiz-util-base": {}, "moodle-mod_quiz-util-slot": { "requires": ["node", "moodle-mod_quiz-util-base"] }, "moodle-mod_quiz-util-page": { "requires": ["node", "moodle-mod_quiz-util-base"] } } }, "moodle-mod_quiz-questionchooser": { "requires": ["moodle-core-chooserdialogue", "moodle-mod_quiz-util", "querystring-parse"] }, "moodle-mod_quiz-dragdrop": { "requires": ["base", "node", "io", "dom", "dd", "dd-scroll", "moodle-core-dragdrop", "moodle-core-notification", "moodle-mod_quiz-quizbase", "moodle-mod_quiz-util-base", "moodle-mod_quiz-util-page", "moodle-mod_quiz-util-slot", "moodle-course-util"] }, "moodle-mod_quiz-modform": { "requires": ["base", "node", "event"] }, "moodle-mod_quiz-quizbase": { "requires": ["base", "node"] }, "moodle-message_airnotifier-toolboxes": { "requires": ["base", "node", "io"] }, "moodle-filter_glossary-autolinker": { "requires": ["base", "node", "io-base", "json-parse", "event-delegate", "overlay", "moodle-core-event", "moodle-core-notification-alert", "moodle-core-notification-exception", "moodle-core-notification-ajaxexception"] }, "moodle-filter_mathjaxloader-loader": { "requires": ["moodle-core-event"] }, "moodle-editor_atto-editor": { "requires": ["node", "transition", "io", "overlay", "escape", "event", "event-simulate", "event-custom", "node-event-html5", "node-event-simulate", "yui-throttle", "moodle-core-notification-dialogue", "moodle-core-notification-confirm", "moodle-editor_atto-rangy", "handlebars", "timers", "querystring-stringify"] }, "moodle-editor_atto-plugin": { "requires": ["node", "base", "escape", "event", "event-outside", "handlebars", "event-custom", "timers", "moodle-editor_atto-menu"] }, "moodle-editor_atto-menu": { "requires": ["moodle-core-notification-dialogue", "node", "event", "event-custom"] }, "moodle-editor_atto-rangy": { "requires": [] }, "moodle-report_eventlist-eventfilter": { "requires": ["base", "event", "node", "node-event-delegate", "datatable", "autocomplete", "autocomplete-filters"] }, "moodle-report_loglive-fetchlogs": { "requires": ["base", "event", "node", "io", "node-event-delegate"] }, "moodle-gradereport_grader-gradereporttable": { "requires": ["base", "node", "event", "handlebars", "overlay", "event-hover"] }, "moodle-gradereport_history-userselector": { "requires": ["escape", "event-delegate", "event-key", "handlebars", "io-base", "json-parse", "moodle-core-notification-dialogue"] }, "moodle-tool_capability-search": { "requires": ["base", "node"] }, "moodle-tool_lp-dragdrop-reorder": { "requires": ["moodle-core-dragdrop"] }, "moodle-tool_monitor-dropdown": { "requires": ["base", "event", "node"] }, "moodle-assignfeedback_editpdf-editor": { "requires": ["base", "event", "node", "io", "graphics", "json", "event-move", "event-resize", "transition", "querystring-stringify-simple", "moodle-core-notification-dialog", "moodle-core-notification-alert", "moodle-core-notification-warning", "moodle-core-notification-exception", "moodle-core-notification-ajaxexception"] }, "moodle-atto_accessibilitychecker-button": { "requires": ["color-base", "moodle-editor_atto-plugin"] }, "moodle-atto_accessibilityhelper-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_align-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_bold-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_charmap-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_clear-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_collapse-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_emojipicker-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_emoticon-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_equation-button": { "requires": ["moodle-editor_atto-plugin", "moodle-core-event", "io", "event-valuechange", "tabview", "array-extras"] }, "moodle-atto_h5p-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_html-button": { "requires": ["promise", "moodle-editor_atto-plugin", "moodle-atto_html-beautify", "moodle-atto_html-codemirror", "event-valuechange"] }, "moodle-atto_html-beautify": {}, "moodle-atto_html-codemirror": { "requires": ["moodle-atto_html-codemirror-skin"] }, "moodle-atto_image-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_indent-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_italic-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_link-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_managefiles-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_managefiles-usedfiles": { "requires": ["node", "escape"] }, "moodle-atto_media-button": { "requires": ["moodle-editor_atto-plugin", "moodle-form-shortforms"] }, "moodle-atto_noautolink-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_orderedlist-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_recordrtc-button": { "requires": ["moodle-editor_atto-plugin", "moodle-atto_recordrtc-recording"] }, "moodle-atto_recordrtc-recording": { "requires": ["moodle-atto_recordrtc-button"] }, "moodle-atto_rtl-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_strike-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_subscript-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_superscript-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_table-button": { "requires": ["moodle-editor_atto-plugin", "moodle-editor_atto-menu", "event", "event-valuechange"] }, "moodle-atto_title-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_underline-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_undo-button": { "requires": ["moodle-editor_atto-plugin"] }, "moodle-atto_unorderedlist-button": { "requires": ["moodle-editor_atto-plugin"] } } }, "gallery": { "name": "gallery", "base": "https:\\/\\/moodle.ruhr-uni-bochum.de\\/lib\\/yuilib\\/gallery\\/", "combine": true, "comboBase": "https:\\/\\/moodle.ruhr-uni-bochum.de\\/theme\\/yui_combo.php?", "ext": false, "root": "gallery\\/1633802793\\/", "patterns": { "gallery-": { "group": "gallery" } } } }, "modules": { "core_filepicker": { "name": "core_filepicker", "fullpath": "https:\\/\\/moodle.ruhr-uni-bochum.de\\/lib\\/javascript.php\\/1633802793\\/repository\\/filepicker.js", "requires": ["base", "node", "node-event-simulate", "json", "async-queue", "io-base", "io-upload-iframe", "io-form", "yui2-treeview", "panel", "cookie", "datatable", "datatable-sort", "resize-plugin", "dd-plugin", "escape", "moodle-core_filepicker", "moodle-core-notification-dialogue"] }, "core_comment": { "name": "core_comment", "fullpath": "https:\\/\\/moodle.ruhr-uni-bochum.de\\/lib\\/javascript.php\\/1633802793\\/comment\\/comment.js", "requires": ["base", "io-base", "node", "json", "yui2-animation", "overlay", "escape"] }, "mathjax": { "name": "mathjax", "fullpath": "https:\\/\\/cdn.jsdelivr.net\\/npm\\/mathjax@2.7.8\\/MathJax.js?delayStartupUntil=configured" }, "core_question_flags": { "name": "core_question_flags", "fullpath": "https:\\/\\/moodle.ruhr-uni-bochum.de\\/lib\\/javascript.php\\/1633802793\\/question\\/flags.js", "requires": ["base", "dom", "event-delegate", "io-base"] }, "core_question_engine": { "name": "core_question_engine", "fullpath": "https:\\/\\/moodle.ruhr-uni-bochum.de\\/lib\\/javascript.php\\/1633802793\\/question\\/qengine.js", "requires": ["node", "event"] }, "mod_quiz": { "name": "mod_quiz", "fullpath": "https:\\/\\/moodle.ruhr-uni-bochum.de\\/lib\\/javascript.php\\/1633802793\\/mod\\/quiz\\/module.js", "requires": ["base", "dom", "event-delegate", "event-key", "core_question_engine", "moodle-core-formchangechecker"] } } };
        M.yui.loader = { modules: {} };

//]]>
    </script>

    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>

<body id="page-mod-quiz-review" class="fpage-mod-quiz-review"
    class="format-topics path-mod path-mod-quiz gecko dir-ltr lang-de yui-skin-sam yui3-skin-sam pagelayout-incourse course-3 context-104 cmid-59 category-1 jsenabled vsc-initialized drawer-ease">

    <div id="page-wrapper" class="d-print-block">

        <script
            src="https://moodle.ruhr-uni-bochum.de/lib/javascript.php/1633802793/lib/babel-polyfill/polyfill.min.js"></script>
        <script
            src="https://moodle.ruhr-uni-bochum.de/lib/javascript.php/1633802793/lib/polyfills/polyfill.js"></script>
        <script
            src="https://moodle.ruhr-uni-bochum.de/theme/yui_combo.php?rollup/3.17.2/yui-moodlesimple-min.js"></script>
        <script src="https://moodle.ruhr-uni-bochum.de/lib/javascript.php/1633802793/lib/javascript-static.js"></script>
        <script>
            document.body.className += ' jsenabled';
        </script>

        <div id="page" class="container-fluid d-print-block">

            <div id="page-content" class="row pb-3 d-print-block">
                <div id="region-main-box" class="col-12">
                    <section id="region-main" class="has-blocks mb-3" aria-label="Inhalt">

                        <div role="main"><span id="maincontent"></span>
                            <form action=""
                                method="post" class="questionflagsaveform">
                                <div>
    '''

moodle_html_footer = '''
  </div>
                            </form>

                        </div>


                    </section>

                </div>
            </div>
        </div>

        <div id="goto-top-link">
            <a class="btn btn-light" role="button" href="#" aria-label="Nach oben">
                <i class="icon fa fa-arrow-up fa-fw " aria-hidden="true"></i>
            </a>
        </div>
        <footer id="page-footer" class="py-3 bg-dark text-light">
            <div class="container">

                <script>
                    //<![CDATA[
                    var require = {
                        baseUrl: 'https://moodle.ruhr-uni-bochum.de/lib/requirejs.php/1633802793/',
                        // We only support AMD modules with an explicit define() statement.
                        enforceDefine: true,
                        skipDataMain: true,
                        waitSeconds: 0,

                        paths: {
                            jquery: 'https://moodle.ruhr-uni-bochum.de/lib/javascript.php/1633802793/lib/jquery/jquery-3.5.1.min',
                            jqueryui: 'https://moodle.ruhr-uni-bochum.de/lib/javascript.php/1633802793/lib/jquery/ui-1.12.1/jquery-ui.min',
                            jqueryprivate: 'https://moodle.ruhr-uni-bochum.de/lib/javascript.php/1633802793/lib/requirejs/jquery-private'
                        },

                        // Custom jquery config map.
                        map: {
                            // '*' means all modules will get 'jqueryprivate'
                            // for their 'jquery' dependency.
                            '*': { jquery: 'jqueryprivate' },
                            // Stub module for 'process'. This is a workaround for a bug in MathJax (see MDL-60458).
                            '*': { process: 'core/first' },

                            // 'jquery-private' wants the real jQuery module
                            // though. If this line was not here, there would
                            // be an unresolvable cyclic dependency.
                            jqueryprivate: { jquery: 'jquery' }
                        }
                    };

//]]>
                </script>
                <script
                    src="https://moodle.ruhr-uni-bochum.de/lib/javascript.php/1633802793/lib/requirejs/require.min.js"></script>
                <script>
                    //<![CDATA[
                    M.util.js_pending("core/first");
                    require(['core/first'], function () {
                        require(['core/prefetch'])
                            ;
                        require(["media_videojs/loader"], function (loader) {
                            loader.setUp('de');
                        });;

                        require(['jquery', 'core/custom_interaction_events'], function ($, CustomEvents) {
                            CustomEvents.define('#single_select6164887fd25b35', [CustomEvents.events.accessibleChange]);
                            $('#single_select6164887fd25b35').on(CustomEvents.events.accessibleChange, function () {
                                var ignore = $(this).find(':selected').attr('data-ignore');
                                if (typeof ignore === typeof undefined) {
                                    $('#single_select_f6164887fd25b34').submit();
                                }
                            });
                        });
                        ;

                        require(['jquery', 'message_popup/notification_popover_controller'], function ($, controller) {
                            var container = $('#nav-notification-popover-container');
                            var controller = new controller(container);
                            controller.registerEventListeners();
                            controller.registerListNavigationEventListeners();
                        });
                        ;

                        require(
                            [
                                'jquery',
                                'core_message/message_popover'
                            ],
                            function (
                                $,
                                Popover
                            ) {
                                var toggle = $('#message-drawer-toggle-6164887fdb8d26164887fd25b38');
                                Popover.init(toggle);
                            });
                        ;

                        require(['jquery', 'core/custom_interaction_events'], function ($, CustomEvents) {
                            CustomEvents.define('#jump-to-activity', [CustomEvents.events.accessibleChange]);
                            $('#jump-to-activity').on(CustomEvents.events.accessibleChange, function () {
                                if (!$(this).val()) {
                                    return false;
                                }
                                $('#url_select_f6164887fd25b317').submit();
                            });
                        });
                        ;

                        require(['jquery', 'core_message/message_drawer'], function ($, MessageDrawer) {
                            var root = $('#message-drawer-6164887fddde16164887fd25b318');
                            MessageDrawer.init(root, '6164887fddde16164887fd25b318', false);
                        });
                        ;

                        require(['jquery', 'core/custom_interaction_events'], function ($, CustomEvents) {
                            CustomEvents.define('#single_select6164887fd25b320', [CustomEvents.events.accessibleChange]);
                            $('#single_select6164887fd25b320').on(CustomEvents.events.accessibleChange, function () {
                                var ignore = $(this).find(':selected').attr('data-ignore');
                                if (typeof ignore === typeof undefined) {
                                    $('#single_select_f6164887fd25b319').submit();
                                }
                            });
                        });
                        ;

                        M.util.js_pending('theme_boost/loader');
                        require(['theme_boost/loader'], function () {
                            M.util.js_complete('theme_boost/loader');
                        });

                        M.util.js_pending('theme_boost/drawer');
                        require(['theme_boost/drawer'], function (drawer) {
                            drawer.init();
                            M.util.js_complete('theme_boost/drawer');
                        });
                        ;
                        M.util.js_pending('qtype_multichoice/answers'); require(['qtype_multichoice/answers'], function (amd) { amd.init("question-8-1"); M.util.js_complete('qtype_multichoice/answers'); });;
                        M.util.js_pending('core/notification'); require(['core/notification'], function (amd) { amd.init(104, []); M.util.js_complete('core/notification'); });;
                        M.util.js_pending('core/log'); require(['core/log'], function (amd) { amd.setConfig({ "level": "warn" }); M.util.js_complete('core/log'); });;
                        M.util.js_pending('core/page_global'); require(['core/page_global'], function (amd) { amd.init(); M.util.js_complete('core/page_global'); });
                        M.util.js_complete("core/first");
                    });
//]]>
                </script>
                <script>
                    //<![CDATA[
                    M.yui.add_module({ "qtype_multianswer": { "name": "qtype_multianswer", "fullpath": "https:\\/\\/moodle.ruhr-uni-bochum.de\\/lib\\/javascript.php\\/1633802793\\/question\\/type\\/multianswer\\/module.js", "requires": ["base", "node", "event", "overlay"] }, "core_question_engine": { "name": "core_question_engine", "fullpath": "https:\\/\\/moodle.ruhr-uni-bochum.de\\/lib\\/javascript.php\\/1633802793\\/question\\/qengine.js", "requires": ["node", "event"] }, "mod_quiz": { "name": "mod_quiz", "fullpath": "https:\\/\\/moodle.ruhr-uni-bochum.de\\/lib\\/javascript.php\\/1633802793\\/mod\\/quiz\\/module.js", "requires": ["base", "dom", "event-delegate", "event-key", "core_question_engine", "moodle-core-formchangechecker"] } });

//]]>
                </script>
                <script>
                    //<![CDATA[
                    M.str = { "moodle": { "lastmodified": "Zuletzt ge\\u00e4ndert", "name": "Name", "error": "Fehler", "info": "Infos", "yes": "Ja", "no": "Nein", "cancel": "Abbrechen", "changesmadereallygoaway": "Sie haben etwas ver\\u00e4ndert. M\\u00f6chten Sie die Seite wirklich verlassen, ohne die \\u00c4nderungen zu speichern?", "confirm": "Best\\u00e4tigen", "areyousure": "Sind Sie sicher?", "closebuttontitle": "Schlie\\u00dfen", "unknownerror": "Unbekannter Fehler", "file": "Datei", "url": "URL" }, "repository": { "type": "Typ", "size": "Gr\\u00f6\\u00dfe", "invalidjson": "Ung\\u00fcltiger JSON-Text", "nofilesattached": "Keine Datei", "filepicker": "Dateiauswahl", "logout": "Abmelden", "nofilesavailable": "Keine Dateien vorhanden", "norepositoriesavailable": "Sie k\\u00f6nnen hier zur Zeit keine Dateien hochladen.", "fileexistsdialogheader": "Datei bereits vorhanden", "fileexistsdialog_editor": "Eine Datei mit diesem Namen wurde bereits an den Text angeh\\u00e4ngt, den Sie gerade bearbeiten", "fileexistsdialog_filemanager": "Eine Datei mit diesem Namen wurde bereits an den Text angeh\\u00e4ngt", "renameto": "Nach '{$a}' umbenennen", "referencesexist": "Es gibt {$a} Links zu dieser Datei.", "select": "W\\u00e4hlen Sie" }, "admin": { "confirmdeletecomments": "M\\u00f6chten Sie die Kommentare wirklich l\\u00f6schen?", "confirmation": "Best\\u00e4tigung" }, "question": { "flagged": "markiert" }, "quiz": { "functiondisabledbysecuremode": "Diese Funktion ist aktuell deaktiviert", "startattempt": "Versuch beginnen", "timesup": "Zeit ist abgelaufen." }, "debug": { "debuginfo": "Debug-Info", "line": "Zeile", "stacktrace": "Stack trace" }, "langconfig": { "labelsep": ":\\u00a0" } };
//]]>
                </script>
                <script>
                    //<![CDATA[
                    (function () {
                        Y.use("moodle-filter_mathjaxloader-loader", function () {
                            M.filter_mathjaxloader.configure({ "mathjaxconfig": "\\nMathJax.Hub.Config({\\n    config: [\\"Accessible.js\\", \\"Safe.js\\"],\\n    errorSettings: { message: [\\"!\\"] },\\n    skipStartupTypeset: true,\\n    messageStyle: \\"none\\"\\n});\\n", "lang": "de" });
                        });
                        M.util.js_pending('random6164887fd25b31'); Y.use('core_question_flags', function (Y) { M.core_question_flags.init(Y, "https:\\/\\/moodle.ruhr-uni-bochum.de\\/question\\/toggleflag.php", [{ "src": "https:\\/\\/moodle.ruhr-uni-bochum.de\\/theme\\/image.php\\/boost\\/core\\/1633802793\\/i\\/unflagged", "title": "Diese Frage als Referenz markieren", "alt": "nicht markiert" }, { "src": "https:\\/\\/moodle.ruhr-uni-bochum.de\\/theme\\/image.php\\/boost\\/core\\/1633802793\\/i\\/flagged", "title": "Markierung entfernen", "alt": "markiert" }], ["Frage markieren", "Markierung entfernen"]); M.util.js_complete('random6164887fd25b31'); });
                        M.util.js_pending('random6164887fd25b32'); Y.use('mod_quiz', function (Y) { M.mod_quiz.nav.init(Y); M.util.js_complete('random6164887fd25b32'); });
                        M.util.help_popups.setup(Y);
                        M.util.js_pending('random6164887fd25b321'); Y.use('qtype_multianswer', function (Y) { M.qtype_multianswer.init(Y, "#question-8-5"); M.util.js_complete('random6164887fd25b321'); });
                        M.util.js_pending('random6164887fd25b322'); Y.use('mod_quiz', function (Y) { M.mod_quiz.init_review_form(Y); M.util.js_complete('random6164887fd25b322'); });
                        M.util.js_pending('random6164887fd25b323'); Y.on('domready', function () { M.util.js_complete("init"); M.util.js_complete('random6164887fd25b323'); });
                    })();
//]]>
                </script>

            </div>
        </footer>
    </div>

</body>

</html>
    '''
