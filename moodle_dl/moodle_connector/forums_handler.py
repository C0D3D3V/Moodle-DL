from datetime import datetime

from moodle_dl.moodle_connector.request_helper import RequestHelper
from moodle_dl.state_recorder.course import Course
from moodle_dl.download_service.path_tools import PathTools


class ForumsHandler:
    """
    Fetches and parses the various endpoints in Moodle for Forum Entries.
    """

    def __init__(self, request_helper: RequestHelper, version: int):
        self.request_helper = request_helper
        self.version = version

    def fetch_forums(self, courses: [Course]) -> {int: {int: {}}}:
        """
        Fetches the Databases List for all courses from the
        Moodle system
        @return: A Dictionary of all databases,
                 indexed by courses, then databases
        """
        # do this only if version is greater then 2.5
        # because mod_forum_get_forums_by_courses will fail
        if self.version < 2013051400:
            return {}

        print('\rDownloading forums information\033[K', end='')

        # We create a dictionary with all the courses we want to request.
        extra_data = {}
        courseids = {}
        for index, course in enumerate(courses):
            courseids.update({str(index): course.id})

        extra_data.update({'courseids': courseids})

        forums = self.request_helper.post_REST('mod_forum_get_forums_by_courses', extra_data)

        result = {}
        for forum in forums:
            # This is the instance id with which we can make the API queries.
            forum_id = forum.get('id', 0)
            forum_name = forum.get('name', 'forum')
            forum_intro = forum.get('intro', '')
            forum_course_module_id = forum.get('cmid', 0)
            forum_introfiles = forum.get('introfiles', [])
            course_id = forum.get('course', 0)

            # normalize
            for forum_file in forum_introfiles:
                file_type = forum_file.get('type', '')
                if file_type is None or file_type == '':
                    forum_file.update({'type': 'forum_introfile'})

            forum_entry = {
                forum_course_module_id: {
                    'id': forum_id,
                    'name': forum_name,
                    'intro': forum_intro,
                    'files': forum_introfiles,
                }
            }

            course_dic = result.get(course_id, {})

            course_dic.update(forum_entry)

            result.update({course_id: course_dic})

        return result

    def fetch_forums_posts(self, forums: {}, last_timestamps_per_forum: {}) -> {}:
        """
        Fetches for the forums list of all courses the additionally
        entries. This is kind of waste of resources, because there
        is no API to get all entries at once.
        @param forums: the dictionary of forums of all courses.
        @return: A Dictionary of all forums,
                 indexed by courses, then forums
        """
        # do this only if version is greater then 2.8
        # because mod_forum_get_forum_discussions_paginated will fail
        if self.version < 2014111000:
            return forums

        counter = 0
        total = 0
        # count total forums for nice console output
        for course_id in forums:
            for forum_id in forums[course_id]:
                total += 1

        for course_id in forums:
            for forum_id in forums[course_id]:
                counter += 1
                real_id = forums[course_id][forum_id].get('id', 0)
                page_num = 0
                last_timestamp = last_timestamps_per_forum.get(forum_id, 0)
                latest_discussions = []
                done = False
                while not done:
                    data = {
                        'forumid': real_id,
                        'perpage': 10,
                        'page': page_num,
                    }

                    print(
                        '\rDownloading forum discussions %3d/%3d [%6s|%6s|p%s]\033[K'
                        % (counter, total, course_id, real_id, page_num),
                        end='',
                    )

                    if self.version >= 2019052000:
                        discussions_result = self.request_helper.post_REST('mod_forum_get_forum_discussions', data)
                    else:
                        discussions_result = self.request_helper.post_REST(
                            'mod_forum_get_forum_discussions_paginated', data
                        )

                    discussions = discussions_result.get('discussions', [])

                    if len(discussions) == 0:
                        done = True
                        break

                    for discussion in discussions:

                        timemodified = discussion.get('timemodified', 0)
                        if discussion.get('modified', 0) > timemodified:
                            timemodified = discussion.get('modified', 0)

                        if last_timestamp < timemodified:
                            latest_discussions.append(
                                {
                                    'subject': discussion.get('subject', ''),
                                    'timemodified': timemodified,
                                    'discussion_id': discussion.get('discussion', 0),
                                    'created': discussion.get('created', 0),
                                }
                            )
                        else:
                            done = True
                            break
                    page_num += 1

                forums_files = self._get_files_of_discussions(latest_discussions)
                forums[course_id][forum_id]['files'] += forums_files

        return forums

    def _get_files_of_discussions(self, latest_discussions: []) -> []:
        result = []

        for i, discussion in enumerate(latest_discussions):
            valid_subject = PathTools.to_valid_name(discussion.get('subject', ''))
            shorted_discussion_name = valid_subject
            if len(shorted_discussion_name) > 17:
                shorted_discussion_name = shorted_discussion_name[:15] + '..'
            discussion_id = discussion.get('discussion_id', 0)
            discussion_created = discussion.get('created', 0)

            print(
                '\rDownloading posts of discussion [%-17s|%6s] %3d/%3d\033[K'
                % (shorted_discussion_name, discussion_id, i, len(latest_discussions) - 1),
                end='',
            )

            data = {
                'discussionid': discussion_id,
                'sortby': 'modified',
                'sortdirection': 'ASC',
            }

            posts_result = self.request_helper.post_REST('mod_forum_get_forum_discussion_posts', data)

            posts = posts_result.get('posts', [])

            for post in posts:
                post_message = post.get('message', '')
                if post_message is None:
                    post_message = ''
                post_modified = post.get('modified', 0)

                post_id = post.get('id', 0)
                post_parent = post.get('parent', 0)
                post_userfullname = post.get('userfullname', '')
                if post_userfullname is None:
                    post_userfullname = "Unknown"

                post_filename = PathTools.to_valid_name('[' + str(post_id) + '] ' + post_userfullname)
                if post_parent != 0:
                    post_filename = PathTools.to_valid_name(post_filename + ' response to [' + str(post_parent) + ']')

                post_path = PathTools.to_valid_name(
                    datetime.utcfromtimestamp(discussion_created).strftime('%y-%m-%d') + ' ' + valid_subject
                )

                post_files = post.get('messageinlinefiles', [])
                post_files += post.get('attachments', [])

                post_file = {
                    'filename': post_filename,
                    'filepath': post_path,
                    'timemodified': post_modified,
                    'description': post_message,
                    'type': 'description',
                }
                result.append(post_file)

                for post_file in post_files:
                    file_type = post_file.get('type', '')
                    if file_type is None or file_type == '':
                        post_file.update({'type': 'forum_file'})
                    post_file.update({'filepath': post_path})
                    result.append(post_file)

        return result
