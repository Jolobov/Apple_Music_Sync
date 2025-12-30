# config.py

# Window Configuration
WINDOW_SIZE = "720x680"
MIN_SIZE = (680, 600)

# Fonts
FONT_UI = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 20, "bold")
FONT_LOG = ("Consolas", 9)


# Codec Mapping
CODEC_MAP = {
    "m4a (AAC - Original)": "aac-legacy",
    "mp3 (Converted)": "mp3"
}

# Themes
THEMES = {
    "light": {
        "bg": "#F2F2F7", "card_bg": "#FFFFFF", "card_border": "#E5E5EA",
        "fg": "#000000", "sub_fg": "#8E8E93",
        "entry_bg": "#FFFFFF", "entry_fg": "#000000", "input_border": "#C7C7CC",
        "divider": "#E5E5EA",
        "accent": "#FA233B", "accent_fg": "#FFFFFF",
        "stop_bg": "#E5E5EA", "stop_fg": "#FF3B30",
        "log_bg": "#1C1C1E", "log_fg": "#00FF00",
        "placeholder": "#C7C7CC"
    },
    "dark": {
        "bg": "#000000", "card_bg": "#1C1C1E", "card_border": "#2C2C2E",
        "fg": "#FFFFFF", "sub_fg": "#98989D",
        "entry_bg": "#1C1C1E", "entry_fg": "#FFFFFF", "input_border": "#3A3A3C",
        "divider": "#2C2C2E",
        "accent": "#FA233B", "accent_fg": "#FFFFFF",
        "stop_bg": "#2C2C2E", "stop_fg": "#FF453A",
        "log_bg": "#121212", "log_fg": "#00FF00",
        "placeholder": "#636366"
    }
}


# Gamdl Configuration Template
GAMDL_CONFIG_TEMPLATE = """[gamdl]
save_cover = true
no_synced_lyrics = true
log_level = INFO
log_file = null
no_exceptions = false
language = en-US
wvd_path = null
overwrite = false
save_playlist = false
nm3u8dlre_path = {nm3u8}
mp4decrypt_path = {decrypt}
ffmpeg_path = {ffmpeg}
mp4box_path = {mp4box}
download_mode = ytdlp
remux_mode = ffmpeg
cover_format = jpg
album_folder_template = {album_artist}/{album}
compilation_folder_template = Compilations/{album}
single_disc_file_template = {track:02d} {title}
multi_disc_file_template = {disc}-{track:02d} {title}
no_album_folder_template = {artist}/Unknown Album
no_album_file_template = {title}
playlist_file_template = Playlists/{playlist_artist}/{playlist_title}
date_tag_template = %Y-%m-%dT%H:%M:%SZ
exclude_tags = null
cover_size = 1200
truncate = null
synced_lyrics_format = lrc
synced_lyrics_only = false
music_video_codec_priority = h264,h265
music_video_remux_format = m4v
music_video_resolution = 1080p
uploaded_video_quality = best
codec_song = {codec}
cookies_path = {cookies}
"""