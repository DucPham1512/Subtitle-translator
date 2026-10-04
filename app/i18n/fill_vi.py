"""Fill app_vi.ts with the Vietnamese UI translations, then compile .qm files.

Run after `pyside6-lupdate` (see README):  python app/i18n/fill_vi.py
Checks that every source string has a translation and that {placeholders} match.
"""

from __future__ import annotations

import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent

VI = {
    "Add episodes": "Thêm tập",
    "Check the episode numbers. Memory builds up in episode order, so a wrong number matters.":
        "Kiểm tra số tập. Bộ nhớ được xây dựng theo thứ tự tập, nên số tập sai sẽ gây ảnh hưởng.",
    "File": "Tệp",
    "Episode": "Tập",
    "Note": "Ghi chú",
    "Register": "Đăng ký",
    "Duplicate of {id}; skipped": "Trùng với {id}; bỏ qua",
    "No video stream; skipped": "Không có luồng video; bỏ qua",
    "No number detected: enter it": "Không nhận ra số tập: hãy nhập",
    "Subtitle Agent": "Subtitle Agent",
    "The settings could not be loaded:\n{error}": "Không tải được cài đặt:\n{error}",
    "1. Calibrate": "1. Căn chỉnh",
    "2. Cast and synopsis": "2. Nhân vật và tóm tắt",
    "3. Voice clips": "3. Mẫu giọng nói",
    "4. Sprites": "4. Hình nhân vật",
    "5. Generate seed": "5. Tạo dữ liệu khởi đầu",
    "6. Review seed": "6. Duyệt dữ liệu khởi đầu",
    "Episode:": "Tập:",
    "Drag a rectangle over the subtitle line, then save. Subtitles are centred, so the band widens to be symmetric around the middle of the frame. The position is the same in every episode, so this is done once.":
        "Kéo một hình chữ nhật bao quanh dòng phụ đề rồi lưu. Phụ đề nằm giữa khung hình, nên vùng chọn sẽ được nới rộng cho cân đối hai bên quanh đường giữa khung hình. Vị trí giống nhau ở mọi tập nên chỉ cần làm một lần.",
    "Save subtitle band": "Lưu vùng phụ đề",
    "Calibrate": "Căn chỉnh",
    "Subtitle band saved.": "Đã lưu vùng phụ đề.",
    "List the characters (Chinese name, who they are), their relationships and how they address each other, and a short synopsis.":
        "Liệt kê các nhân vật (tên tiếng Trung, họ là ai), quan hệ và cách xưng hô với nhau, cùng một đoạn tóm tắt ngắn.",
    "Import file…": "Nhập tệp…",
    "Save": "Lưu",
    "Import cast list": "Nhập danh sách nhân vật",
    "Text (*.md *.txt);;All files (*)": "Văn bản (*.md *.txt);;Mọi tệp (*)",
    "Cast": "Nhân vật",
    "Saved.": "Đã lưu.",
    "Character id:": "Mã nhân vật:",
    "Mark in": "Đánh dấu đầu",
    "Mark out": "Đánh dấu cuối",
    "Save clip": "Lưu đoạn",
    "Import WAV files…": "Nhập tệp WAV…",
    "Play": "Phát",
    "Delete clip": "Xóa đoạn",
    "in {a} · out {b}": "đầu {a} · cuối {b}",
    "Voice clips": "Mẫu giọng nói",
    "Choose a character, then mark the start and end of a line spoken only by that character.":
        "Chọn nhân vật, rồi đánh dấu đầu và cuối một câu chỉ do nhân vật đó nói.",
    "Import voice clips": "Nhập mẫu giọng nói",
    "Audio (*.wav *.mp3 *.flac *.m4a *.ogg)": "Âm thanh (*.wav *.mp3 *.flac *.m4a *.ogg)",
    "{n} clips (3–5 recommended)": "{n} đoạn (nên có 3–5)",
    "Delete {name}?": "Xóa {name}?",
    "The sprite check is turned off in Settings; templates are not used.":
        "Kiểm tra hình nhân vật đang tắt trong Cài đặt; các mẫu hình sẽ không được dùng.",
    "Grab paused frame": "Lấy khung hình đang dừng",
    "Save template": "Lưu mẫu hình",
    "Sprites": "Hình nhân vật",
    "Grab a frame, drag a rectangle around the character, and choose the character id.":
        "Lấy một khung hình, kéo hình chữ nhật quanh nhân vật và chọn mã nhân vật.",
    "Drafts characters (Hán-Việt names), pronoun pairs and glossary terms from the cast list, and computes the voice bank from the clips. Nothing is written to memory until you approve the seed in step 6.":
        "Soạn nháp nhân vật (tên Hán-Việt), cặp xưng hô và thuật ngữ từ danh sách nhân vật, và tính kho giọng nói từ các đoạn mẫu. Chưa có gì được ghi vào bộ nhớ cho đến khi bạn duyệt ở bước 6.",
    "Generate seed": "Tạo dữ liệu khởi đầu",
    "Write the cast list first (step 2).": "Hãy viết danh sách nhân vật trước (bước 2).",
    "Another job is running.": "Đang có tác vụ khác chạy.",
    "Bootstrap": "Khởi tạo",
    "Seed ready. Review it in step 6.": "Dữ liệu khởi đầu đã sẵn sàng. Hãy duyệt ở bước 6.",
    "Memory seeded. You can run episode 1 now.": "Đã khởi tạo bộ nhớ. Bây giờ có thể chạy tập 1.",
    "Characters": "Nhân vật",
    "Pronoun pairs": "Cặp xưng hô",
    "Glossary": "Thuật ngữ",
    "Add row": "Thêm dòng",
    "Remove row": "Xóa dòng",
    "Character A": "Nhân vật A",
    "Character B": "Nhân vật B",
    "Similarity": "Độ giống",
    "Voices that sound alike (read-only). Double-click a name to hear a clip.":
        "Các giọng nghe giống nhau (chỉ xem). Nhấp đúp vào tên để nghe một đoạn mẫu.",
    "Confusable voices": "Giọng dễ nhầm",
    "Save draft": "Lưu bản nháp",
    "Approve and write to memory…": "Duyệt và ghi vào bộ nhớ…",
    "No seed draft yet. Generate it in step 5.": "Chưa có bản nháp. Hãy tạo ở bước 5.",
    "Seed": "Dữ liệu khởi đầu",
    "Draft saved.": "Đã lưu bản nháp.",
    "Approve seed": "Duyệt dữ liệu khởi đầu",
    "Write these characters, pronoun pairs, glossary terms and voices to memory? They are locked (only you can change them later).":
        "Ghi các nhân vật, cặp xưng hô, thuật ngữ và giọng nói này vào bộ nhớ? Chúng sẽ bị khóa (chỉ bạn mới sửa được sau này).",
    "Run dreaming": "Chạy tổng hợp",
    "Checked proposals are applied. Proposals that change locked entries are unchecked and highlighted. Double-click evidence to open the line.":
        "Các đề xuất được đánh dấu sẽ được áp dụng. Đề xuất thay đổi mục đã khóa được bỏ chọn và tô màu. Nhấp đúp vào bằng chứng để mở dòng.",
    "Proposal": "Đề xuất",
    "Before": "Trước",
    "After": "Sau",
    "Reason": "Lý do",
    "Evidence": "Bằng chứng",
    "Apply checked proposals…": "Áp dụng đề xuất đã chọn…",
    "Dreaming": "Tổng hợp",
    "Dreaming…": "Đang tổng hợp…",
    "No proposals. Run dreaming after finishing an episode.": "Không có đề xuất. Hãy chạy tổng hợp sau khi xong một tập.",
    "{n} proposals from {date}": "{n} đề xuất lúc {date}",
    "Style rules": "Quy tắc văn phong",
    "Briefings": "Tóm tắt",
    "Changes a locked entry (confirmed by a person)": "Thay đổi một mục đã khóa (do người xác nhận)",
    "Wait for the running job to finish.": "Hãy chờ tác vụ đang chạy kết thúc.",
    "Apply proposals": "Áp dụng đề xuất",
    "Apply {n} proposals to memory in one version? Unchecked proposals are discarded.":
        "Áp dụng {n} đề xuất vào bộ nhớ trong một phiên bản? Các đề xuất không chọn sẽ bị bỏ.",
    "Applied {n} changes; {c} went to Conflicts.": "Đã áp dụng {n} thay đổi; {c} chuyển sang Xung đột.",
    "Search…": "Tìm…",
    "Add": "Thêm",
    "Delete": "Xóa",
    "Save changes": "Lưu thay đổi",
    "Discard changes": "Bỏ thay đổi",
    "Memory": "Bộ nhớ",
    "{n} entries": "{n} mục",
    "Unsaved changes": "Có thay đổi chưa lưu",
    "Delete locked entries": "Xóa mục đã khóa",
    "{n} of the selected entries are locked (confirmed by a person). Delete them anyway? Deleting a character also deletes its pronoun pairs and voice.":
        "{n} mục được chọn đã khóa (do người xác nhận). Vẫn xóa? Xóa nhân vật cũng xóa các cặp xưng hô và giọng nói của nhân vật đó.",
    "Nothing to save": "Không có gì để lưu",
    "History…": "Lịch sử…",
    "Add files…": "Thêm tệp…",
    "Add folder…": "Thêm thư mục…",
    "Include subfolders": "Gồm cả thư mục con",
    "Refresh": "Làm mới",
    "Drop video files or folders on the table to add them.": "Kéo thả tệp video hoặc thư mục vào bảng để thêm.",
    "Stages": "Công đoạn",
    "Status": "Trạng thái",
    "Flags": "Cờ",
    "Cost": "Chi phí",
    "Run (auto)": "Chạy (tự động)",
    "Run (human review)": "Chạy (người duyệt)",
    "Resume": "Tiếp tục",
    "Rerun from stage…": "Chạy lại từ công đoạn…",
    "Review": "Duyệt",
    "Render": "Xuất video",
    "Relink…": "Liên kết lại…",
    "Open output folder": "Mở thư mục đầu ra",
    "Open report": "Mở báo cáo",
    "Clean temporary files": "Dọn tệp tạm",
    "Episodes": "Các tập",
    "Add video files": "Thêm tệp video",
    "Videos ({exts})": "Video ({exts})",
    "Add a folder of videos": "Thêm thư mục video",
    "Checking videos…": "Đang kiểm tra video…",
    "No video files found.": "Không tìm thấy tệp video.",
    "Episode order": "Thứ tự tập",
    "Earlier episodes are not done yet: {ids}.\nMemory builds up episode by episode, so translating out of order may use less context. Continue anyway?":
        "Các tập trước chưa xong: {ids}.\nBộ nhớ được xây dựng từng tập, nên dịch không theo thứ tự có thể thiếu ngữ cảnh. Vẫn tiếp tục?",
    "Rerun from stage": "Chạy lại từ công đoạn",
    "Stage:": "Công đoạn:",
    "Rerun {ep} from “{stage}”? These results will be replaced:\n\n{files}":
        "Chạy lại {ep} từ “{stage}”? Các kết quả sau sẽ bị thay thế:\n\n{files}",
    "(none yet)": "(chưa có)",
    "Find the video for {ep}": "Tìm video của {ep}",
    "Relink": "Liên kết lại",
    "Different file?": "Tệp khác?",
    "This file does not match the original video's fingerprint. It may be a different file, and existing results may not line up.":
        "Tệp này không khớp dấu vân tay của video gốc. Có thể đây là tệp khác, và các kết quả hiện có có thể không khớp.",
    "Keep results": "Giữ kết quả",
    "Rerun from the start": "Chạy lại từ đầu",
    "Delete {ep}'s temporary files (frame crops, audio, preview, render leftovers)? The script, edits and reports are kept.":
        "Xóa tệp tạm của {ep} (ảnh cắt khung hình, âm thanh, xem trước, phần thừa khi xuất)? Kịch bản, chỉnh sửa và báo cáo được giữ lại.",
    "A required program (ffmpeg, ffprobe or git) is not installed. Install it and restart the app.":
        "Thiếu một chương trình cần thiết (ffmpeg, ffprobe hoặc git). Hãy cài đặt rồi mở lại ứng dụng.",
    "The episode's video file was moved or deleted. Use Relink to point to its new location.":
        "Tệp video của tập đã bị di chuyển hoặc xóa. Dùng Liên kết lại để chỉ tới vị trí mới.",
    "The LLM budget for this episode was reached. Raise the budget in Settings, then Resume.":
        "Đã hết ngân sách LLM cho tập này. Tăng ngân sách trong Cài đặt rồi bấm Tiếp tục.",
    "The AI model returned invalid output twice. Resume to try again.":
        "Mô hình AI trả kết quả không hợp lệ hai lần. Bấm Tiếp tục để thử lại.",
    "The AI service could not be reached. Check your internet connection and API keys, then Resume.":
        "Không kết nối được dịch vụ AI. Kiểm tra kết nối mạng và khóa API rồi bấm Tiếp tục.",
    "An API key is missing. Enter it in Settings > API keys.": "Thiếu khóa API. Hãy nhập trong Cài đặt > Khóa API.",
    "The output folder is not set or not writable. Choose one in Settings > Files.":
        "Chưa đặt thư mục đầu ra hoặc không ghi được. Hãy chọn trong Cài đặt > Tệp.",
    "The output video already exists. Choose Overwrite or Keep both.":
        "Video đầu ra đã tồn tại. Hãy chọn Ghi đè hoặc Giữ cả hai.",
    "The review is not complete: every line must be approved and have Vietnamese text.":
        "Chưa duyệt xong: mọi dòng phải được duyệt và có bản dịch tiếng Việt.",
    "Another job is already running for this episode.": "Đang có tác vụ khác chạy cho tập này.",
    "Memory is being written by another job. Try again in a moment.":
        "Bộ nhớ đang được tác vụ khác ghi. Hãy thử lại sau giây lát.",
    "Not allowed while a job is running. Wait for it to finish.":
        "Không thể làm khi đang có tác vụ chạy. Hãy chờ tác vụ kết thúc.",
    "The settings are invalid. Fix them in Settings.": "Cài đặt không hợp lệ. Hãy sửa trong Cài đặt.",
    "A required model package is not installed. See README for the install command.":
        "Chưa cài gói mô hình cần thiết. Xem README để biết lệnh cài đặt.",
    "No subtitle font was found in the fonts folder. Add NotoSans-Regular.ttf there.":
        "Không tìm thấy phông phụ đề trong thư mục fonts. Hãy thêm NotoSans-Regular.ttf vào đó.",
    "Rendering failed. See the log for details, then try Render again.":
        "Xuất video thất bại. Xem nhật ký để biết chi tiết rồi thử Xuất video lại.",
    "This episode is not registered.": "Tập này chưa được đăng ký.",
    "Write the cast list and synopsis first (Bootstrap step 2).":
        "Hãy viết danh sách nhân vật và tóm tắt trước (Khởi tạo bước 2).",
    "Generate the seed first (Bootstrap step 5).": "Hãy tạo dữ liệu khởi đầu trước (Khởi tạo bước 5).",
    "The job was cancelled. Resume to continue where it stopped.":
        "Tác vụ đã bị hủy. Bấm Tiếp tục để chạy tiếp từ chỗ dừng.",
    "Retry limit reached": "Hết số lần thử lại",
    "Speaker unresolved": "Chưa xác định người nói",
    "Low speaker confidence": "Người nói chưa chắc chắn",
    "Possibly on-screen text": "Có thể là chữ trên màn hình",
    "OCR uncertain": "OCR không chắc chắn",
    "Check pinyin": "Kiểm tra pinyin",
    "Missing translation": "Thiếu bản dịch",
    "Line too long": "Dòng quá dài",
    "Reading speed too high": "Tốc độ đọc quá nhanh",
    "Glossary term not used": "Chưa dùng đúng thuật ngữ",
    "Pronoun mismatch": "Xưng hô không khớp",
    "Invalid speaker": "Người nói không hợp lệ",
    "Speaker differs from voice": "Người nói khác với giọng nhận dạng",
    "Low OCR confidence": "Độ tin cậy OCR thấp",
    "Not evaluated": "Chưa được đánh giá",
    "Rule warnings": "Cảnh báo quy tắc",
    "Settings": "Cài đặt",
    "No job running": "Không có tác vụ nào",
    "Device: …": "Thiết bị: …",
    "Running: {job}": "Đang chạy: {job}",
    "Device: {device}": "Thiết bị: {device}",
    "Cost ${cost} / ${budget}": "Chi phí ${cost} / ${budget}",
    "Running: {job} — {stage}": "Đang chạy: {job} — {stage}",
    "Finished: {job}": "Đã xong: {job}",
    "Failed: {job}": "Thất bại: {job}",
    "Job running": "Tác vụ đang chạy",
    "A job is running ({job}). Cancel it and close? It can be resumed later.":
        "Đang có tác vụ chạy ({job}). Hủy và đóng? Có thể tiếp tục sau.",
    "A job is running: memory is read-only until it finishes.":
        "Đang có tác vụ chạy: bộ nhớ chỉ được xem cho đến khi tác vụ kết thúc.",
    "Id": "Mã",
    "Chinese": "Tiếng Trung",
    "Vietnamese": "Tiếng Việt",
    "Description": "Mô tả",
    "Pinyin": "Pinyin",
    "Type": "Loại",
    "Notes": "Ghi chú",
    "First episode": "Tập đầu tiên",
    "Locked": "Đã khóa",
    "Source": "Nguồn",
    "Updated": "Cập nhật",
    "Pronoun matrix": "Ma trận xưng hô",
    "Voice bank": "Kho giọng nói",
    "Conflicts": "Xung đột",
    "History": "Lịch sử",
    "Some changes were not saved": "Một số thay đổi chưa được lưu",
    "Rows: speaker. Columns: listener. Cell: self term / address term. Double-click a cell to edit.":
        "Hàng: người nói. Cột: người nghe. Ô: tự xưng / gọi người nghe. Nhấp đúp vào ô để sửa.",
    "Edit": "Sửa",
    "Character": "Nhân vật",
    "Clips in bank": "Số đoạn trong kho",
    "Clip files": "Số tệp mẫu",
    "Clips (double-click to play):": "Các đoạn mẫu (nhấp đúp để phát):",
    "Recompute selected voices": "Tính lại giọng đã chọn",
    "Voice similarity (confusable pairs in red)": "Độ giống giọng (cặp dễ nhầm tô đỏ)",
    "recompute voices": "tính lại giọng",
    "Table": "Bảng",
    "Key": "Khóa",
    "Current": "Hiện tại",
    "Proposed": "Đề xuất",
    "Source / evidence": "Nguồn / bằng chứng",
    "Accept proposal": "Chấp nhận đề xuất",
    "Reject proposal": "Từ chối đề xuất",
    "Date": "Ngày",
    "Message": "Nội dung",
    "Changes": "Thay đổi",
    "Roll back to this version…": "Quay về phiên bản này…",
    "Added": "Thêm mới",
    "Changed": "Đã đổi",
    "Removed": "Đã xóa",
    "No changes in this version.": "Phiên bản này không có thay đổi.",
    "Roll back memory": "Quay lui bộ nhớ",
    "Restore memory to the version of {date} (“{message}”)?\n\nA new version is created; nothing is lost, and this rollback can itself be undone from the history.":
        "Khôi phục bộ nhớ về phiên bản lúc {date} (“{message}”)?\n\nMột phiên bản mới sẽ được tạo; không mất dữ liệu nào, và có thể hoàn tác thao tác này từ lịch sử.",
    "History of {key}": "Lịch sử của {key}",
    "Change": "Thay đổi",
    "Details": "Chi tiết",
    "Version": "Phiên bản",
    "Output folder": "Thư mục đầu ra",
    "Rendering needs an output folder.\n\n{error}": "Cần có thư mục đầu ra để xuất video.\n\n{error}",
    "Open Settings": "Mở Cài đặt",
    "Output file exists": "Tệp đầu ra đã tồn tại",
    "{name} already exists in the output folder.": "{name} đã có trong thư mục đầu ra.",
    "Overwrite": "Ghi đè",
    "Keep both": "Giữ cả hai",
    "Another job is running ({job}). Wait for it to finish or cancel it.":
        "Đang có tác vụ khác chạy ({job}). Hãy chờ xong hoặc hủy nó.",
    "Pronouns {speaker} → {listener}": "Xưng hô {speaker} → {listener}",
    "Leave the context empty for the default pair. Rows without terms are deleted.":
        "Để trống ngữ cảnh cho cặp mặc định. Dòng không có từ xưng hô sẽ bị xóa.",
    "Context": "Ngữ cảnh",
    "Self term": "Tự xưng",
    "Address term": "Gọi người nghe",
    "Since episode": "Từ tập",
    "Add variant": "Thêm biến thể",
    "Play / pause": "Phát / dừng",
    "Replay line": "Phát lại dòng",
    "Loop line": "Lặp dòng",
    "Preview unavailable: libmpv could not be loaded ({error}).\nDownload libmpv for Windows (mpv-dev-x86_64 from the mpv website), put libmpv-2.dll next to the app (project folder), and restart. Review works without the preview.":
        "Không xem trước được: không tải được libmpv ({error}).\nTải libmpv cho Windows (mpv-dev-x86_64 từ trang mpv), đặt libmpv-2.dll cạnh ứng dụng (thư mục dự án) rồi mở lại. Vẫn duyệt được khi không có xem trước.",
    "Preview unavailable: {error}": "Không xem trước được: {error}",
    "Unapproved only": "Chỉ dòng chưa duyệt",
    "Search Chinese and Vietnamese…": "Tìm trong tiếng Trung và tiếng Việt…",
    "Flag:": "Cờ:",
    "Speaker:": "Người nói:",
    "Read-only: this episode's review is finished.": "Chỉ xem: tập này đã duyệt xong.",
    "State": "Tình trạng",
    "Time": "Thời gian",
    "Speaker → listener": "Người nói → người nghe",
    "Regenerate": "Tạo lại",
    "Discard the manual pinyin and generate it from the Chinese text": "Bỏ pinyin sửa tay và tạo lại từ chữ Hán",
    "Dialogue": "Hội thoại",
    "Sign": "Biển chữ",
    "Title": "Tiêu đề",
    "Sound effect": "Hiệu ứng âm thanh",
    "Approve and next": "Duyệt và sang dòng sau",
    "Approve all remaining non-flagged…": "Duyệt mọi dòng còn lại không có cờ…",
    "Finish review…": "Hoàn tất duyệt…",
    "No episode is waiting for review. Run an episode in human mode first.":
        "Không có tập nào chờ duyệt. Hãy chạy một tập ở chế độ người duyệt trước.",
    "All": "Tất cả",
    "No flags": "Không có cờ",
    "Flagged remaining: {flagged} · Approved: {approved} / {total}":
        "Còn dòng có cờ: {flagged} · Đã duyệt: {approved} / {total}",
    "{id} (unknown)": "{id} (không rõ)",
    "Approve remaining lines": "Duyệt các dòng còn lại",
    "Approve all {n} remaining lines that have no flags?": "Duyệt tất cả {n} dòng còn lại không có cờ?",
    "Finish review": "Hoàn tất duyệt",
    "Finish the review of {ep}?\n\n{edited} edited lines will update memory (glossary changes are locked), then the video is rendered to the output folder.":
        "Hoàn tất duyệt {ep}?\n\n{edited} dòng đã sửa sẽ cập nhật bộ nhớ (thay đổi thuật ngữ sẽ bị khóa), sau đó video được xuất ra thư mục đầu ra.",
    "Reasons": "Lý do",
    "Evaluator (attempt {n})": "Đánh giá (lần {n})",
    "Glossary terms": "Thuật ngữ",
    "No pronoun pair in memory yet": "Bộ nhớ chưa có cặp xưng hô này",
    "No notes for this line.": "Dòng này không có ghi chú.",
    "Autosave failed": "Tự động lưu thất bại",
    "Cancel": "Hủy",
    "skipped": "bỏ qua",
    "done": "xong",
    "failed": "thất bại",
    "Resume continues from: {stage}": "Tiếp tục sẽ chạy từ: {stage}",
    "General": "Chung",
    "Files": "Tệp",
    "Advanced": "Nâng cao",
    "API keys": "Khóa API",
    "Language": "Ngôn ngữ",
    "Shortcuts": "Phím tắt",
    "Human review": "Người duyệt",
    "Automatic": "Tự động",
    "Automatic (GPU when available)": "Tự động (dùng GPU nếu có)",
    "GPU (CUDA)": "GPU (CUDA)",
    "CPU": "CPU",
    "Use on-screen character art to resolve uncertain speakers": "Dùng hình nhân vật trên màn hình để xác định người nói chưa chắc chắn",
    "Automatic (NVENC when available)": "Tự động (dùng NVENC nếu có)",
    "Default review mode": "Chế độ duyệt mặc định",
    "Device": "Thiết bị",
    "Budget per episode": "Ngân sách mỗi tập",
    "Sprite check": "Kiểm tra hình nhân vật",
    "Video encoder": "Bộ mã hóa video",
    "Quality (lower = better, 18–23 typical)": "Chất lượng (càng thấp càng tốt, thường 18–23)",
    "Pinyin font size": "Cỡ chữ pinyin",
    "Vietnamese font size": "Cỡ chữ tiếng Việt",
    "Required before the first render": "Bắt buộc trước lần xuất video đầu tiên",
    "Choose…": "Chọn…",
    "Delete temporary files when an episode is done": "Xóa tệp tạm khi một tập hoàn tất",
    "Type a sample file name, e.g. 仙门第3集.mp4": "Nhập thử một tên tệp, ví dụ 仙门第3集.mp4",
    "Output name suffix": "Hậu tố tên tệp đầu ra",
    "Working folder": "Thư mục làm việc",
    "Cleanup": "Dọn dẹp",
    "Video extensions": "Đuôi tệp video",
    "Episode number patterns (one per line, tried in order)": "Mẫu số tập (mỗi dòng một mẫu, thử theo thứ tự)",
    "Test": "Thử",
    "Choose a folder": "Chọn thư mục",
    "Detected episode: {n}": "Nhận ra tập: {n}",
    "No number detected": "Không nhận ra số tập",
    "The output folder does not exist: {path}": "Thư mục đầu ra không tồn tại: {path}",
    "config.yaml. It is validated before saving; comments are kept.":
        "config.yaml. Được kiểm tra trước khi lưu; các chú thích được giữ nguyên.",
    "Reload": "Tải lại",
    "Validate and save": "Kiểm tra và lưu",
    "Save keys": "Lưu khóa",
    "Test {role}": "Thử {role}",
    "Keys saved to .env.": "Đã lưu khóa vào .env.",
    "Testing {role}…": "Đang thử {role}…",
    "{role}: connected (reply: {reply})": "{role}: đã kết nối (trả lời: {reply})",
    "{role}: failed — {error}": "{role}: thất bại — {error}",
    "Apply (restarts the app)": "Áp dụng (khởi động lại ứng dụng)",
    "Interface language": "Ngôn ngữ giao diện",
    "Theme": "Giao diện",
    "Follows the Windows light / dark setting.": "Theo chế độ sáng / tối của Windows.",
    "The language changes after a restart. Restart now?": "Ngôn ngữ sẽ đổi sau khi khởi động lại. Khởi động lại ngay?",
    "Action": "Thao tác",
    "Shortcut": "Phím tắt",
    "Reset to defaults": "Khôi phục mặc định",
    "Save shortcuts": "Lưu phím tắt",
    "Saved. They apply when you open Review.": "Đã lưu. Áp dụng khi mở màn hình Duyệt.",
    "Next line": "Dòng sau",
    "Previous line": "Dòng trước",
    "Toggle loop": "Bật / tắt lặp",
    "Focus Vietnamese field": "Chuyển tới ô tiếng Việt",
    "Undo (line)": "Hoàn tác (dòng)",
    "Redo (line)": "Làm lại (dòng)",
    "Search": "Tìm",
    "Frame sampling": "Lấy mẫu khung hình",
    "OCR": "OCR",
    "Events": "Sự kiện phụ đề",
    "OCR correction": "Sửa lỗi OCR",
    "Audio": "Âm thanh",
    "Voice match": "Nhận dạng giọng",
    "Scenes": "Phân cảnh",
    "Translate + evaluate": "Dịch + đánh giá",
    "Review gate": "Cổng duyệt",
    "Memory update": "Cập nhật bộ nhớ",
    "Pipeline": "Quy trình",
    "New": "Mới",
    "Running": "Đang chạy",
    "Awaiting review": "Chờ duyệt",
    "Done": "Xong",
    "Failed": "Thất bại",
    "Video missing": "Mất video",
    "Interrupted": "Bị gián đoạn",
    "New character…": "Nhân vật mới…",
    "Add a character to memory and assign it to this line": "Thêm nhân vật vào bộ nhớ và gán cho dòng này",
    "New character": "Nhân vật mới",
    "Hán-Việt reading, e.g. Lâm Uyên": "Âm Hán-Việt, ví dụ Lâm Uyên",
    "lowercase letters, digits and _": "chữ thường, chữ số và _",
    "Who they are, in one line (optional)": "Nhân vật là ai, một dòng (không bắt buộc)",
    "Speaker of this line": "Người nói của dòng này",
    "Listener of this line": "Người nghe của dòng này",
    "Don't assign": "Không gán",
    "Also add the name to the glossary": "Thêm tên vào thuật ngữ",
    "Chinese name": "Tên tiếng Trung",
    "Vietnamese name": "Tên tiếng Việt",
    "Set as": "Gán làm",
    "The character is saved to memory now, locked as your edit.":
        "Nhân vật được lưu vào bộ nhớ ngay, và bị khóa như một chỉnh sửa của bạn.",
    "Enter the Chinese name.": "Hãy nhập tên tiếng Trung.",
    "Enter the Vietnamese name.": "Hãy nhập tên tiếng Việt.",
    "The id may only contain lowercase letters, digits and _.": "Mã chỉ được gồm chữ thường, chữ số và _.",
    "This id is already used by another character.": "Mã này đã được dùng cho nhân vật khác.",
    "Reset line": "Khôi phục dòng",
    "Undo every review change to this line (back to the pipeline's version)":
        "Bỏ mọi thay đổi khi duyệt dòng này (trở về bản do quy trình tạo)",
    "Delete line": "Xóa dòng",
    "Remove this line from the video (e.g. OCR noise). It can be restored.":
        "Bỏ dòng này khỏi video (ví dụ chữ nhiễu do OCR). Có thể khôi phục lại.",
    "Discard review…": "Hủy toàn bộ duyệt…",
    "Deleted: not shown in the video": "Đã xóa: không hiện trong video",
    "Deleted: {n}": "Đã xóa: {n}",
    "Restore line": "Khôi phục dòng đã xóa",
    "Discard review": "Hủy toàn bộ duyệt",
    "Discard the whole review of {ep}?\n\nAll edits, approvals and deletions ({n} lines) are replaced by the pipeline's output. This cannot be undone.":
        "Hủy toàn bộ phần duyệt của {ep}?\n\nMọi chỉnh sửa, phê duyệt và thao tác xóa ({n} dòng) sẽ được thay bằng bản do quy trình tạo. Không thể hoàn tác.",
    "Deleted": "Đã xóa",
    "This line is not shown in the video. Use Restore line to bring it back.":
        "Dòng này không hiện trong video. Dùng Khôi phục dòng đã xóa để đưa lại.",
    "Delete / restore line": "Xóa / khôi phục dòng",
    "Preview unavailable on this display platform.": "Không xem trước được trên nền hiển thị này.",
    "Click or drag to move through the video": "Bấm hoặc kéo để tua video",
    "Previous frame": "Khung hình trước",
    "Back 5 seconds": "Lùi 5 giây",
    "Forward 5 seconds": "Tới 5 giây",
    "Next frame": "Khung hình sau",
    "One-frame OCR fragment": "Mảnh OCR chỉ hiện một khung hình",
    "Script review: check this line": "Duyệt toàn kịch bản: kiểm tra dòng này",
    "Removed: repeat of another line": "Đã bỏ: lặp lại dòng khác",
    "Removed: OCR noise": "Đã bỏ: nhiễu OCR",
    "Removed: not part of the story": "Đã bỏ: không thuộc nội dung phim",
    "Removed by script review": "Đã bỏ khi duyệt toàn kịch bản",
    "Script review": "Duyệt toàn kịch bản",
    "Characters on screen": "Nhân vật trên hình",
    "Box": "Khung",
    "Recognised as": "Nhận ra là",
    "Talking": "Đang nói",
    "Correct to": "Sửa thành",
    "No characters were found in this line's frame.": "Không tìm thấy nhân vật nào trong khung hình của dòng này.",
    "Green: recognised · orange: not recognised · red outline: talking. Correct a box when it is wrong; this teaches the sprite bank when you finish the review.":
        "Xanh lá: đã nhận ra · cam: chưa nhận ra · viền đỏ: đang nói. Sửa khung khi nhận sai; "
        "khi hoàn tất duyệt, việc sửa này sẽ dạy lại kho hình nhân vật.",
    "unknown ({id})": "chưa rõ ({id})",
    "(as recognised)": "(như đã nhận ra)",
    "Not a character": "Không phải nhân vật",
    "The original subtitle in the video at this line (the preview hides it)":
        "Phụ đề gốc trong video ở dòng này (bản xem trước đã che nó)",
    "Original": "Bản gốc",
    "On screen": "Trên hình",
    "Line": "Dòng",
    "Green: recognised · orange: not recognised · blue: drawn by you · red outline: talking. Drag a box to move it, drag a corner to resize, drag on empty space to draw a box around a missed character (Delete removes a drawn box). Your corrections teach the sprite bank when you finish the review.":
        "Xanh lá: đã nhận ra · cam: chưa nhận ra · xanh dương: do bạn vẽ · viền đỏ: đang nói. Kéo khung để di "
        "chuyển, kéo góc để đổi kích thước, kéo trên chỗ trống để vẽ khung quanh nhân vật bị bỏ sót (Delete xoá "
        "khung bạn vẽ). Khi hoàn tất duyệt, các chỉnh sửa này sẽ dạy lại kho hình nhân vật.",
    "Green: recognised · orange: not recognised · blue: drawn by you · red outline: talking.":
        "Xanh lá: đã nhận ra · cam: chưa nhận ra · xanh dương: do bạn vẽ · viền đỏ: đang nói.",
    "not a character": "không phải nhân vật",
    "drawn by you": "do bạn vẽ",
    "(choose a character)": "(chọn nhân vật)",
    "Remove this box": "Xoá khung này",
    "Partial review suggests another speaker": "Duyệt một phần gợi ý người nói khác",
    "Speaker changed: check the pronouns": "Đã đổi người nói: kiểm tra xưng hô",
    "Use the speaker Partial review suggests (the line is then flagged so you check its pronouns)":
        "Dùng người nói mà Duyệt một phần gợi ý (dòng sẽ được đánh dấu để bạn kiểm tra xưng hô)",
    "Partial review…": "Duyệt một phần…",
    "Learn from the lines you approved so far (speakers, talking marks, character boxes, voices) and re-check the remaining lines. Nothing is saved to memory until you finish the review.":
        "Học từ các dòng bạn đã duyệt (người nói, dấu đang nói, khung nhân vật, giọng nói) rồi kiểm tra lại các "
        "dòng còn lại. Không có gì được lưu vào bộ nhớ cho đến khi bạn hoàn tất duyệt.",
    "Use {name}": "Dùng {name}",
    "Partial review": "Duyệt một phần",
    "Partial review running…": "Đang duyệt một phần…",
    "Re-checked the remaining lines with what you approved so far.\n{n} lines got a new speaker (flag: Speaker set by partial review). Check their pronouns; Undo on a line restores its speaker.":
        "Đã kiểm tra lại các dòng còn lại dựa trên những gì bạn đã duyệt.\n{n} dòng được đổi người nói "
        "(cờ: Người nói do duyệt một phần đặt). Hãy kiểm tra xưng hô; Hoàn tác trên một dòng sẽ trả lại "
        "người nói cũ.",
    "Speaker set by partial review": "Người nói do duyệt một phần đặt",
    "New NPC": "NPC mới",
    "OCR read": "OCR đã đọc",
    "Use this line": "Dùng câu này",
    "Make this line the speaker's sample: its voice, and the character marked talking in On screen as the picture (nobody marked talking: no picture, e.g. for a narrator). Changes the card only.":
        "Lấy câu này làm mẫu của người nói: giọng của câu, và nhân vật được đánh dấu đang nói ở mục Trên màn hình làm hình (không ai được đánh dấu đang nói: không có hình, ví dụ người dẫn chuyện). Chỉ thay đổi thẻ nhân vật.",
    "Saving the sample…": "Đang lưu mẫu…",
    "sample chosen by you": "mẫu do bạn chọn",
    "no reviewed line yet": "chưa có câu đã duyệt",
    "Browse characters": "Duyệt nhân vật",
    "Browse characters…": "Duyệt nhân vật…",
    "Pictures and voice samples come from a line each character speaks in an episode you reviewed. Pick the one who speaks here.":
        "Hình và mẫu giọng lấy từ một câu thoại của mỗi nhân vật trong tập bạn đã duyệt. Hãy chọn người đang nói ở đây.",
    "Picture": "Hình",
    "Voice": "Giọng",
    "Use as speaker": "Dùng làm người nói",
    "Use as listener": "Dùng làm người nghe",
    "Close": "Đóng",
    "Play a line this character speaks in an earlier episode": "Phát một câu nhân vật này nói ở tập trước",
    "See every character's picture, first episode and voice sample, and assign one to this line":
        "Xem hình, tập xuất hiện đầu tiên và mẫu giọng của mọi nhân vật, rồi gán một nhân vật cho câu này",
    "Who the speaker is: picture, first episode, description and a voice sample from an episode you reviewed":
        "Người nói là ai: hình, tập xuất hiện đầu tiên, mô tả và mẫu giọng từ một tập bạn đã duyệt",
    "Loading…": "Đang tải…",
    "on probation": "đang thử thách",
    "first seen {ep}": "xuất hiện lần đầu {ep}",
    "Subtitle style (OCR segmentation)": "Kiểu phụ đề (tách chữ cho OCR)",
    "Learns the subtitle's colours, outline and letter size from the episode above, inside the saved band. Done once per series; learning it again re-reads the subtitles of every episode run afterwards.":
        "Học màu chữ, viền và cỡ chữ của phụ đề từ tập ở trên, trong vùng phụ đề đã lưu. Chỉ làm một lần cho mỗi bộ phim; học lại thì mọi tập chạy sau đó sẽ được đọc lại phụ đề.",
    "Learn subtitle style from this episode": "Học kiểu phụ đề từ tập này",
    "Show style preview": "Xem trước kiểu phụ đề",
    "The saved subtitle style cannot be read: {error}": "Không đọc được kiểu phụ đề đã lưu: {error}",
    "OCR segmentation is on, so learn the style before running episodes.":
        "Tách chữ cho OCR đang bật, nên hãy học kiểu phụ đề trước khi chạy các tập.",
    "Only needed when OCR pre-processing is set to segmentation.":
        "Chỉ cần khi tiền xử lý OCR được đặt là tách chữ.",
    "No subtitle style learned yet.": "Chưa học kiểu phụ đề.",
    "none": "không có",
    "light": "sáng",
    "dark": "tối",
    "Learned from {episode} on {date}: {polarity} text, fill grey {fill_min}–{fill_max}, outline {outline}, stroke {stroke:.3f} and letter height {height:.2f} of the band.":
        "Học từ {episode} ngày {date}: chữ {polarity}, độ xám nền chữ {fill_min}–{fill_max}, viền {outline}, nét chữ {stroke:.3f} và chiều cao chữ {height:.2f} so với vùng phụ đề.",
    "Subtitle style": "Kiểu phụ đề",
    "Replace the saved subtitle style with one learned from {episode}? Episodes run afterwards read their subtitles again with the new style.":
        "Thay kiểu phụ đề đã lưu bằng kiểu học từ {episode}? Các tập chạy sau đó sẽ đọc lại phụ đề theo kiểu mới.",
    "Learning the subtitle style from {episode}…": "Đang học kiểu phụ đề từ {episode}…",
    "Subtitle style preview": "Xem trước kiểu phụ đề",
    "Each pair: the subtitle band, then what segmentation keeps for OCR.":
        "Mỗi cặp: vùng phụ đề, rồi phần mà bước tách chữ giữ lại cho OCR.",
    "Script review: OCR error in the Chinese (fix suggested)": "Rà soát kịch bản: lỗi OCR trong chữ Hán (có gợi ý sửa)",
    "What OCR read for this line after pre-processing (segmentation and cropping), at its position in the band; grey was not read":
        "Phần OCR đã đọc cho dòng này sau tiền xử lý (phân vùng và cắt), ở đúng vị trí trong dải phụ đề; "
        "phần màu xám không được đọc",
    "Not saved: the episode's temporary files were cleaned up, or OCR ran without pre-processing":
        "Không có: tệp tạm của tập đã được dọn, hoặc OCR chạy không có tiền xử lý",
    "Give this line's speaker a new automatic id (npc_<episode>_<n>) without saving anything to memory. Use the same id on the character's other lines: at Finish review, with at least 3 approved lines as speaker it goes on probation, and becomes a character only if it speaks again in the next 2 episodes.":
        "Đặt cho người nói của dòng này một mã tự động mới (npc_<tập>_<số>) mà không lưu gì vào bộ nhớ. Dùng cùng "
        "mã đó cho các dòng khác của nhân vật: khi hoàn tất duyệt, nếu nói ít nhất 3 dòng đã duyệt, nhân vật được "
        "đưa vào diện thử thách, và chỉ trở thành nhân vật chính thức nếu nói lại trong 2 tập kế tiếp.",
    "{id} (on probation since {ep})": "{id} (đang thử thách từ {ep})",
    "{id} (new NPC)": "{id} (NPC mới)",
    "Suggested speaker: <b>{name}</b> ({reason})": "Người nói gợi ý: <b>{name}</b> ({reason})",
    "Talking on screen: {name}": "Đang nói trên hình: {name}",
    "Voice: {name} {score:.2f} ({status})": "Giọng nói: {name} {score:.2f} ({status})",
    "Run": "Chạy",
    "Run {n} episodes in episode order ({mode}): {ids}": "Chạy {n} tập theo thứ tự tập ({mode}): {ids}",
    "auto": "tự động",
    "human review": "duyệt thủ công",
    "Run again with today's memory (done or waiting for review): {ids}. Their translations and review drafts are replaced; a review in progress is lost.":
        "Chạy lại với bộ nhớ hiện tại (đã xong hoặc đang chờ duyệt): {ids}. Bản dịch và bản nháp duyệt của các "
        "tập này sẽ bị thay thế; phần duyệt đang làm dở sẽ mất.",
    "{ep} is already done or waiting for review. Run it again with today's memory?\n\nFrom OCR correction on, every step runs again; its translation and review draft are replaced (a review in progress is lost). Memory and the finished video change only when the new run is finished.\n\nReplaced: {files}":
        "{ep} đã xong hoặc đang chờ duyệt. Chạy lại với bộ nhớ hiện tại?\n\nTừ bước sửa lỗi OCR trở đi, mọi "
        "bước chạy lại; bản dịch và bản nháp duyệt sẽ bị thay thế (phần duyệt đang làm dở sẽ mất). Bộ nhớ và "
        "video hoàn chỉnh chỉ thay đổi khi lần chạy mới hoàn tất.\n\nBị thay thế: {files}",
    "Run again": "Chạy lại",
    "Earlier episodes not done and not selected: {ids}. Memory builds up episode by episode.": "Các tập trước chưa xong và không được chọn: {ids}. Bộ nhớ được xây dựng theo từng tập.",
    "Auto mode stops at the first failed episode; finished episodes stay done.": "Chế độ tự động dừng ở tập lỗi đầu tiên; các tập đã xong vẫn giữ nguyên.",
    "Each episode stops at review; a failed episode does not stop the others.": "Mỗi tập dừng ở bước duyệt; một tập lỗi không làm dừng các tập khác.",
    "Run several episodes": "Chạy nhiều tập",
    "{n} episodes ({mode})": "{n} tập ({mode})",
    "Output files exist": "Tệp đầu ra đã tồn tại",
    "The output video already exists for: {ids}.": "Video đầu ra đã tồn tại cho: {ids}.",
    "Running: {job} · episode {episode}": "Đang chạy: {job} · tập {episode}",
    "Batch": "Hàng loạt",
    "Who really speaks:": "Người thật sự nói:",
    "Pick the right speaker: your answers make a test set that scores later versions automatically (Audit → Benchmark)": "Chọn đúng người nói: câu trả lời của bạn tạo thành bộ kiểm tra để tự động chấm điểm các phiên bản sau (Kiểm định → Đánh giá)",
    "(choose)": "(chọn)",
    "— nobody known: an NPC or a new character without an id (blank is right)": "— không rõ ai: NPC hoặc nhân vật mới chưa có id (để trống là đúng)",
    "Benchmark…": "Đánh giá…",
    "Re-run speaker decisions of the audited episodes with today's code and memory in a sandbox, and score them against your audit answers. Changes nothing; costs a few cents of translation per episode.": "Chạy lại việc xác định người nói của các tập đã kiểm định bằng mã và bộ nhớ hiện tại trong vùng thử, rồi chấm điểm theo câu trả lời kiểm định của bạn. Không thay đổi gì; tốn vài xu tiền dịch mỗi tập.",
    "Benchmark history…": "Lịch sử đánh giá…",
    "Benchmark": "Đánh giá",
    "A name for this run (optional):": "Tên cho lần chạy này (không bắt buộc):",
    "Benchmark history": "Lịch sử đánh giá",
    "{n} answers missing": "thiếu {n} câu trả lời",
    "Generic": "Chung",
    "not audited: reviewed by hand": "không kiểm định: đã duyệt thủ công",
    "Human-reviewed: the output is your corrected script, and its edit list already records every machine error. Set audit.include_human to audit it anyway.":
        "Đã duyệt thủ công: kết quả là kịch bản bạn đã sửa, và danh sách chỉnh sửa đã ghi lại mọi lỗi của máy. "
        "Đặt audit.include_human để vẫn kiểm định tập này.",
    "Speaker": "Người nói",
    "Translation": "Bản dịch",
    "Pronouns": "Xưng hô",
    "n/a": "k/áp dụng",
    "Note (optional)": "Ghi chú (không bắt buộc)",
    "All correct, next": "Đúng hết, tiếp",
    "Mark every aspect correct and go to the next sampled line (Ctrl+Enter)": "Đánh dấu mọi mục là đúng và sang dòng mẫu tiếp theo (Ctrl+Enter)",
    "Next unmarked": "Dòng chưa đánh dấu tiếp theo",
    "random sample": "mẫu ngẫu nhiên",
    "signals disagree": "các tín hiệu không khớp",
    "Measure accuracy without checking every line: each finished episode gets a small random sample (flagged and unflagged lines in proportion) plus the lines where voice, picture and speaker disagree. Mark the sampled lines; the report estimates accuracy for all lines. Marks change no output and teach no memory.": "Đo độ chính xác mà không cần kiểm tra mọi dòng: mỗi tập đã xong có một mẫu ngẫu nhiên nhỏ (dòng có cờ và không cờ theo tỉ lệ) cùng các dòng mà giọng nói, hình ảnh và người nói không khớp. Hãy đánh dấu các dòng mẫu; báo cáo sẽ ước tính độ chính xác cho mọi dòng. Việc đánh dấu không đổi kết quả và không dạy bộ nhớ.",
    "Mode": "Chế độ",
    "Lines": "Số dòng",
    "Sampled": "Đã lấy mẫu",
    "Marked": "Đã đánh dấu",
    "Errors so far": "Lỗi đến nay",
    "Draw samples for finished episodes": "Lấy mẫu cho các tập đã xong",
    "Audit selected episode": "Kiểm định tập đã chọn",
    "Report…": "Báo cáo…",
    "Audit": "Kiểm định",
    "Audit report": "Báo cáo kiểm định",
    "Saved: {path}": "Đã lưu: {path}",
    "{marked} / {total} sampled lines marked": "Đã đánh dấu {marked} / {total} dòng mẫu",
    "The video is not available: {error}": "Không mở được video: {error}",
    "No cast data for this episode (the Characters on screen stage did not run).":
        "Tập này chưa có dữ liệu nhân vật (bước Nhân vật trên hình chưa chạy).",
    "Script review: {note}": "Duyệt toàn kịch bản: {note}",
    "Times removed": "Số lần bỏ",
    "Times kept": "Số lần giữ",
    "Last episode": "Tập gần nhất",
    "Status reason": "Lý do trạng thái",
    "(archived)": "(đã lưu trữ)",
    "Translator": "Dịch",
    "Evaluator": "Đánh giá",
    "Script reviewer": "Duyệt toàn kịch bản",
    "Pinyin (polyphones)": "Pinyin (chữ đa âm)",
    "Memory briefing": "Tóm tắt bộ nhớ",
    "Forget rejected proposals…": "Quên các đề xuất đã từ chối…",
    "Proposals you rejected are never proposed again; this clears that list":
        "Đề xuất bạn đã từ chối sẽ không được đề xuất lại; nút này xóa danh sách đó",
    "{n} you rejected before were left out": "{n} đề xuất bạn từng từ chối đã được bỏ qua",
    "No rejected proposals are remembered.": "Không có đề xuất bị từ chối nào được ghi nhớ.",
    "Forget rejected proposals": "Quên các đề xuất đã từ chối",
    "Forget the {n} proposals you rejected? Dreaming may propose them again.":
        "Quên {n} đề xuất bạn đã từ chối? Tổng hợp có thể đề xuất lại chúng.",
    "Forgot {n} rejected proposals.": "Đã quên {n} đề xuất bị từ chối.",
    "Checked proposals are applied; unchecked ones are rejected and not proposed again. Proposals that change locked entries are unchecked and highlighted. Double-click evidence to open the line.":
        "Các đề xuất được đánh dấu sẽ được áp dụng; đề xuất không đánh dấu bị từ chối và sẽ không được đề xuất lại. Đề xuất thay đổi mục đã khóa được bỏ chọn và tô màu. Nhấp đúp vào bằng chứng để mở dòng.",
    "Line decisions": "Quyết định giữ / bỏ dòng",
    "Incomplete: no price set for {models} (Settings > Advanced, llm.prices)":
        "Chưa đầy đủ: chưa đặt giá cho {models} (Cài đặt > Nâng cao, llm.prices)",
}

_PH = re.compile(r"\{[a-z_]+\}")


def fill(ts: Path, translations: dict[str, str]) -> list[str]:
    tree = ET.parse(ts)
    missing: list[str] = []
    for message in tree.getroot().iter("message"):
        source = message.find("source").text or ""
        target = message.find("translation")
        text = translations.get(source)
        if text is None:
            missing.append(source)
            continue
        if sorted(_PH.findall(source)) != sorted(_PH.findall(text)):
            raise SystemExit(f"placeholder mismatch: {source!r} -> {text!r}")
        target.text = text
        target.attrib.pop("type", None)
    tree.write(ts, encoding="utf-8", xml_declaration=True)
    return missing


def main() -> int:
    missing = fill(HERE / "app_vi.ts", VI)
    if missing:
        print("missing Vietnamese translations:\n  " + "\n  ".join(missing))
        return 1
    lrelease = Path(sys.executable).parent / ("pyside6-lrelease.exe" if sys.platform == "win32" else "pyside6-lrelease")
    for lang in ("en", "vi"):
        subprocess.run([str(lrelease), str(HERE / f"app_{lang}.ts"), "-qm", str(HERE / f"app_{lang}.qm")], check=True)
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
