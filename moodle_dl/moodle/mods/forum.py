import logging

from datetime import datetime
from typing import Dict, List

from moodle_dl.config import ConfigHelper
from moodle_dl.moodle.mods import MoodleMod
from moodle_dl.types import Course, File
from moodle_dl.utils import PathTools as PT


class ForumMod(MoodleMod):
    MOD_NAME = 'forum'
    MOD_PLURAL_NAME = 'forums'
    MOD_MIN_VERSION = 2013051400  # 2.5

    @classmethod
    def download_condition(cls, config: ConfigHelper, file: File) -> bool:
        # TODO: Add download condition, currently forums get filtered on API Call, and are not deleted at all
        return True

    async def real_fetch_mod_entries(self, courses: List[Course]) -> Dict[int, Dict[int, Dict]]:
        forums = await self.client.async_post(
            'mod_forum_get_forums_by_courses', self.get_data_for_mod_entries_endpoint(courses)
        )

        result = {}
        for forum in forums:
            course_id = forum.get('course', 0)
            forum_module_id = forum.get('cmid', 0)
            forum_files = forum.get('introfiles', [])
            self.set_files_types_if_empty(forum_files, 'forum_introfile')

            forum_intro = forum.get('intro', '')
            if forum_intro != '':
                forum_files.append(
                    {
                        'filename': 'Forum intro',
                        'filepath': '/',
                        'description': forum_intro,
                        'type': 'description',
                    }
                )

            self.add_module(
                result,
                course_id,
                forum_module_id,
                {
                    'id': forum.get('id', 0),
                    'name': forum.get('name', 'forum'),
                    'files': forum_files,
                    '_cmid': forum_module_id,
                },
            )

        await self.add_forum_posts(result)
        return result

    async def add_forum_posts(self, forums: Dict[int, Dict[int, Dict]]):
        """
        Fetches for the forums list the forum posts
        @param forums: Dictionary of all forums, indexed by courses, then module id
        """
        if not self.config.get_download_forums():
            return

        if self.version < 2014111000:  # 2.8
            return

        await self.run_async_load_function_on_mod_entries(forums, self.load_latest_discussions)

    async def load_latest_discussions(self, forum: Dict):
        "Adds the discussions that needs to be updated to the forum dict"
        page_num = 0
        last_timestamp = self.last_timestamps.get(self.MOD_NAME, {}).get(forum.get('_cmid', 0), 0)
        latest_discussions = []
        done = False
        while not done:
            data = {
                'forumid': forum.get('id', 0),
                'perpage': 10,
                'page': page_num,
            }

            if self.version >= 2019052000:  # 3.7
                discussions_result = await self.client.async_post('mod_forum_get_forum_discussions', data)
            else:
                discussions_result = await self.client.async_post('mod_forum_get_forum_discussions_paginated', data)

            logging.debug(
                'Loaded %(mod_name)s page %(page_num)d of "%(forum_name)s"',
                {'mod_name': self.MOD_NAME, 'page_num': page_num, 'forum_name': forum.get('name', '')},
            )

            discussions = discussions_result.get('discussions', [])

            if len(discussions) == 0:
                done = True
                break

            for discussion in discussions:
                time_modified = discussion.get('timemodified', 0)
                if discussion.get('modified', 0) > time_modified:
                    time_modified = discussion.get('modified', 0)

                if last_timestamp < time_modified:
                    latest_discussions.append(
                        {
                            'subject': discussion.get('subject', ''),
                            'timemodified': time_modified,
                            'discussion_id': discussion.get('discussion', 0),
                            'created': discussion.get('created', 0),
                        }
                    )
                else:
                    done = True
                    break
            page_num += 1

        forum['files'] += await self.run_async_collect_function_on_list(
            latest_discussions,
            self.load_files_of_discussion,
            'discussion',
            {'collect_id': 'discussion_id', 'collect_name': 'subject'},
        )

    async def load_files_of_discussion(self, discussion: Dict) -> List[Dict]:
        result = []

        data = {
            'discussionid': discussion.get('discussion_id', 0),
            'sortby': 'modified',
            'sortdirection': 'ASC',
        }
        if self.version >= 2019052000:  # 3.7
            posts = (await self.client.async_post('mod_forum_get_discussion_posts', data)).get('posts', [])
        else:
            posts = (await self.client.async_post('mod_forum_get_forum_discussion_posts', data)).get('posts', [])

        for post in posts:
            post_message = post.get('message', '') or ''

            post_files = post.get('attachments', [])
            if self.version >= 2019052000:  # 3.7
                post_parent = post.get('parentid', 0)
                post_user_fullname = post.get('author', {}).get('fullname', None) or 'Unknown'
                post_modified = post.get('timecreated', 0)
                for post_file in post_files:
                    # New return structure uses url instead of fileurl
                    post_file['fileurl'] = post_file.get('url', '')
                    # And also do return normal URLs instead of webservice URLs
                    if post_file['fileurl'].find('/webservice/') < 0:
                        post_file['fileurl'] = post_file['fileurl'].replace(
                            '/pluginfile.php/', '/webservice/pluginfile.php/'
                        )
            else:
                post_parent = post.get('parent', 0)
                post_user_fullname = post.get('userfullname', '') or 'Unknown'
                post_modified = post.get('modified', 0)

                # Also add legacy inline files from messageinlinefiles attribute
                self.add_legacy_inline_files(post.get('messageinlinefiles', []), post_file)

            post_filename = PT.to_valid_name(f"[{post.get('id', 0)}] " + post_user_fullname, is_file=False)
            if post_parent is not None and post_parent != 0:
                post_filename = PT.to_valid_name(
                    post_filename + ' response to [' + str(post_parent) + ']', is_file=False
                )

            post_path = PT.to_valid_name(
                datetime.utcfromtimestamp(discussion.get('created', 0)).strftime('%y-%m-%d')
                + ' '
                + discussion.get('subject', ''),
                is_file=False,
            )

            result.append(
                {
                    'filename': post_filename,
                    'filepath': post_path,
                    'timemodified': post_modified,
                    'description': post_message,
                    'type': 'description',
                }
            )

            for post_file in post_files:
                self.set_file_type_if_empty(post_file, 'forum_file')
                post_file['filepath'] = post_path

            result.extend(post_files)

        return result

    def add_legacy_inline_files(self, inline_files: List, post_files: List):
        for inline_file in inline_files:
            new_inline_file = True
            for attachment in post_files:
                if attachment.get('fileurl', '').replace('attachment', 'post') == inline_file.get('fileurl', ''):
                    if (
                        attachment.get('filesize', 0) == inline_file.get('filesize', 0)
                        # we assume that inline attachments can have different timestamps than the actual
                        # attachment. However, they are still the same file.
                        and attachment.get('filename', '') == inline_file.get('filename', '')
                    ):
                        new_inline_file = False
                        break
            if new_inline_file:
                post_files.append(inline_file)
