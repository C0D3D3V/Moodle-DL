from typing import Optional, TypedDict

from moodle_dl.types import Course, File


class NtfyMessage(TypedDict):
    title: str
    message: str
    source_url: Optional[str]


def _get_change_type(file: File) -> str:
    if file.modified:
        return "modified"
    elif file.deleted:
        return "deleted"
    elif file.moved:
        return "moved"
    else:
        return "new"


def create_full_moodle_diff_messages(changes: list[Course]) -> list[NtfyMessage]:
    messages = []
    for course in changes:
        files_generic_msg = NtfyMessage()
        misc_generic_msg = NtfyMessage()
        files_generic_msg["message"] = f"{course.fullname}\n"
        misc_generic_msg["message"] = f"{course.fullname}\n"
        files_generic_cnt = 0
        misc_generic_cnt = 0
        for file in course.files:
            change_type = _get_change_type(file)
            if file.content_type == "description":
                msg = NtfyMessage(
                    title=" ".join(file.content_filepath.split()[1:]),
                    message=f"{course.fullname}\n{file.content_filename}",
                    source_url=file.content_fileurl,
                )
                if change_type != "new":
                    msg["message"] += f"\nMessage {change_type}"
                messages.append(msg)
            elif file.content_type in ("file", "assignfile"):
                msg_str = f"* {file.content_filename}"
                if file.content_type == "assignfile":
                    msg_str += " | Assignment File"
                if change_type != "new":
                    msg_str += f" | File {change_type}"
                msg_str += "\n"
                files_generic_msg["message"] += msg_str
                files_generic_cnt += 1
            else:
                misc_generic_msg["message"] += f"* {file.content_filename}\n"
                misc_generic_cnt += 1
        files_generic_msg["title"] = f"{files_generic_cnt} File Changes"
        misc_generic_msg["title"] = f"{misc_generic_cnt} Misc Changes"
        if files_generic_cnt:
            messages.append(files_generic_msg)
        if misc_generic_cnt:
            messages.append(misc_generic_msg)
    return messages
