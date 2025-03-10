screen select_song(song_repo):
    modal True

    frame:
        xalign 0.5
        yalign 0.5

        vbox:
            spacing 5

            label "Select A Song" xalign 0.5 text_size 25

            vbox spacing 10:
                grid 4 len(song_repo) + 1:
                    xspacing 10
                    label "Title" text_size 25
                    label "Author" text_size 25
                    label "Charter" text_size 25
                    label "Score (raw / adjusted)" text_size 25
                    for song in song_repo:
                        if len(song.name) > 25:
                            textbutton "{}...".format(song.name[:22].strip()) action [Return(song)]
                        else:
                            textbutton song.name action [Return(song)]
                        textbutton song.artist action [Return(song)]
                        textbutton song.charter action [Return(song)]
                        $ stats = persistent.game_stats.get(song.name)
                        if stats:
                            textbutton score_texts[song.name] action [Return(song)] hovered SetDict(score_texts, song.name, f"{stats['score_raw']:.0f} | {stats['score_adjusted']:.0f}") unhovered SetDict(score_texts, song.name, f"{stats['score_perc'] * 100:.0f}% | {stats['score_adjusted_perc'] * 100:.0f}%")
                        else:
                            textbutton "0% | 0%" action [Return(song)]

            textbutton _("Exit"):
                xalign 0.5
                action Return(None)

screen select_difficulty(song):
    modal True

    frame:
        xalign 0.5
        yalign 0.5
        xpadding 30
        ypadding 30

        vbox:
            spacing 20
            for difficulty in song.difficulties():
                textbutton "{}".format(difficulty) action [Return(difficulty)]

screen rhythm_game(rhythm_game_displayable):
    zorder 100 # always on top, covering textbox, quick_menu
    # disable key handling for game keys

    key 'K_1' action NullAction()
    key 'K_2' action NullAction()
    key 'K_3' action NullAction()
    key 'K_4' action NullAction()
    key 'K_5' action NullAction()

    if rhythm_game_displayable.song.video:
        add "#000"
        add rhythm_game_displayable.song.video
    else:
        add "#000"
    add rhythm_game_displayable

    vbox:
        xpos 50
        ypos 50
        spacing 20

        textbutton 'Quit' action [Confirm('Would you like to quit?', yes=[Stop(CHANNEL_RHYTHM_GAME), Return(rhythm_game_displayable.score)])]:
            text_hover_color '#fff'

        text 'Score: [rhythm_game_displayable.score]':
            color '#fff'
            size 40

    bar:
        xalign 0.5
        ypos 20
        xsize 740
        value CustomAudioPositionValue(channel=CHANNEL_RHYTHM_GAME, duration=rhythm_game_displayable.song.duration)

    if rhythm_game_displayable.has_ended:
        timer 2.0 action Return(rhythm_game_displayable.score)

screen rhythm_game_bg(rgd):
    add "#000"
    if rgd.song.video:
        add rgd.song.video:
            align (0.5, 0.5)
            fit "contain"
    elif rgd.song.album_cover:
        add rgd.song.album_cover:
            align (0.5, 0.5)
            fit "contain"

screen rhythm_game_ui(rgd):
    vbox:
        xpos 50
        ypos 50
        spacing 20

        textbutton "Quit" action [Confirm("Would you like to quit?", yes=[Stop(CHANNEL_RHYTHM_GAME), Stop(CHANNEL_RHYTHM_GAME_GUITAR), Stop(CHANNEL_RHYTHM_GAME_RHYTHM), Return(rgd.score)])]:
            text_hover_color "#fff"

        text "Score: [rgd.score]":
            color "#fff"
            size 30

    bar at delayed_appear:
        xalign 0.5
        ypos 20
        xsize 500
        ysize 15
        value CustomAudioPositionValue(channel=CHANNEL_RHYTHM_GAME, duration=rgd.song.duration)

    if rgd.has_ended:
        timer 2.0 action Return(rgd.score)

screen rhythm_game_display(rgd):
    zorder 100 # always on top, covering textbox, quick_menu

    # disable key handling for game keys
    if persistent.keymap == "numbers":
        key "K_1" action NullAction()
        key "K_2" action NullAction()
        key "K_3" action NullAction()
        key "K_4" action NullAction()
        key "K_5" action NullAction()
    elif persistent.keymap == "numbers_left":
        key "K_1" action NullAction()
        key "K_2" action NullAction()
        key "K_3" action NullAction()
        key "K_4" action NullAction()
        key "K_SPACE" action NullAction()
    elif persistent.keymap == "numbers_right":
        key "K_SPACE" action NullAction()
        key "K_7" action NullAction()
        key "K_8" action NullAction()
        key "K_9" action NullAction()
        key "K_0" action NullAction()
    elif persistent.keymap == "dfsjk":
        key "D" action NullAction()
        key "F" action NullAction()
        key "K_SPACE" action NullAction()
        key "J" action NullAction()
        key "K" action NullAction()

    add rgd:
        ypos -600

default persistent.keymap = "numbers"
default persistent.note_offset = 0
default persistent.game_stats = {}

init python:
    import math
    from glob import glob
    from pathlib import Path
    from collections import MutableMapping, OrderedDict

    import pygame
    import chparse
    from configparser import ConfigParser

    _game_menu_screen = "preferences"

    score_texts = {}

    mr = MusicRoom(fadeout=0.5)
    mr.lut = {}

    for file in renpy.list_files():
        if file.startswith("images/rhythm_game/cg/"):
            file = Path(file)
            renpy.image(f"{file.parent.stem} {file.stem}", str(file).replace("\\", "/"))
        elif file.startswith("songs/") and (file.endswith(".mp3") or file.endswith(".opus")):
            mr.add(file)

    config.keymap['hide_windows'].remove("noshift_K_h")
    config.keymap['screenshot'].remove("noshift_K_s")
    config.keymap['dismiss'].remove("K_SPACE")
    config.keymap["director"].remove("noshift_K_d")
    config.keymap["toggle_fullscreen"].remove("noshift_K_f")

    renpy.add_layer("game_bg", below="screens")
    renpy.add_layer("game_display", above="game_bg")
    renpy.add_layer("game_ui", above="game_display")

    SCORES = {
        "good": 6,
        "perfect": 10
    }

    # green red yellow blue orange
    IMG_0 = "images/rhythm_game/0.webp"
    IMG_1 = "images/rhythm_game/1.webp"
    IMG_2 = "images/rhythm_game/2.webp"
    IMG_3 = "images/rhythm_game/3.webp"
    IMG_4 = "images/rhythm_game/4.webp"

    CHANNEL_RHYTHM_GAME = "rhythm_music"
    CHANNEL_RHYTHM_GAME_GUITAR = "rhythm_music_guitar"
    CHANNEL_RHYTHM_GAME_RHYTHM = "rhythm_music_rhythm"

    _preferences.volumes["voice"] = 0.0
    renpy.music.register_channel("silent", "voice", movie=True)
    renpy.music.register_channel(CHANNEL_RHYTHM_GAME, mixer="music")
    renpy.music.register_channel(CHANNEL_RHYTHM_GAME_GUITAR, mixer="music")
    renpy.music.register_channel(CHANNEL_RHYTHM_GAME_RHYTHM, mixer="music")

    class CaseInsensitiveDict(MutableMapping):
        """ Ordered case insensitive mutable mapping class. """
        def __init__(self, *args, **kwargs):
            self._d = OrderedDict(*args, **kwargs)
            self._convert_keys()
        def _convert_keys(self):
            for k in list(self._d.keys()):
                v = self._d.pop(k)
                self._d.__setitem__(k, v)
        def __len__(self):
            return len(self._d)
        def __iter__(self):
            return iter(self._d)
        def __setitem__(self, k, v):
            self._d[k.lower()] = v
        def __getitem__(self, k):
            return self._d[k.lower()]
        def __delitem__(self, k):
            del self._d[k.lower()]

    class SongRepository:
        def __init__(self, compensation=0.0, delay=3.0):
            self.paths = []
            self.songs = []
            self.compensation = compensation
            self.delay = delay

        def add_path(self, path):
            self.paths.append(Path(path))

        def load(self):
            for path in self.paths:
                # print(f"Loading songs from {path}")
                for file in filter(lambda p: p.is_dir(), path.glob("*/")):
                    chart_file = file / "notes.chart"
                    if not chart_file.exists():
                        continue
                    # print(f"Loading song {file}")
                    song = Song(file, compensation=self.compensation, delay=self.delay)
                    self.songs.append(song)
                    mr.lut[str(song.audio)] = song
                    stats = persistent.game_stats.get(song.name)
                    if stats:
                        score_texts[song.name] = f"{stats['score_perc'] * 100:.0f}% | {stats['score_adjusted_perc'] * 100:.0f}%"
                    else:
                        score_texts[song.name] = "0% | 0%"

        def __iter__(self):
            return iter(self.songs)

        def __len__(self):
            return len(self.songs)

    def find_file_with_extensions(files, extensions):
        for ext in extensions:
            for file in files:
                candidate = file.with_suffix(ext)
                if candidate.is_file():
                    return candidate

    class Song:
        def __init__(self, path, compensation=0.0, delay=0.0):
            # read metadata
            song_config = ConfigParser(dict_type=CaseInsensitiveDict)
            song_config.read(path / "song.ini")

            self.delay = delay

            self.compensation = compensation + song_config.getfloat("song", "compensation", fallback=0.0)

            self.character = song_config.get("display", "character", fallback="john")

            # find audio
            song_path = find_file_with_extensions([path / "song"], [".ogg", ".mp3", ".opus"])
            guitar_path = find_file_with_extensions([path / "guitar"], [".ogg", ".mp3", ".opus"])
            rhythm_path = find_file_with_extensions([path / "rhythm"], [".ogg", ".mp3", ".opus"])

            if song_path is None and guitar_path is None and rhythm_path is None:
                raise FileNotFoundError(f"Could not find any audio file for song {path}")

            if song_path is None:
                if guitar_path:
                    song_path = guitar_path
                elif rhythm_path:
                    song_path = rhythm_path

            self.audio_guitar = None
            self.audio_rhythm = None
            self.audio = str(song_path.relative_to(config.gamedir)).replace("\\", "/")
            if guitar_path:
                self.audio_guitar = str(guitar_path.relative_to(config.gamedir)).replace("\\", "/")
            if rhythm_path:
                self.audio_rhythm = str(rhythm_path.relative_to(config.gamedir)).replace("\\", "/")

            # find optional album cover
            album_cover_path = find_file_with_extensions([path / "album"], [".jpg", ".jpeg", ".png"])

            if album_cover_path and album_cover_path.is_file():
                self.album_cover = str(album_cover_path.relative_to(config.gamedir)).replace("\\", "/")
            else:
                self.album_cover = None

            # find optional video
            self.video = None
            self.video_start_time = song_config.getfloat("song", "video_start_time", fallback=0) / 1000.0
            video_start_time = self.video_start_time

            def play_callback(old, new):
                if self.video_start_time < 0:
                    renpy.music.play([f"<silence {abs(video_start_time)}>", new._play], channel=new.channel, loop=new.loop, synchro_start=True)
                else:
                    renpy.music.play(new._play, channel=new.channel, loop=new.loop, synchro_start=True)
                if new.mask:
                    renpy.music.play(new.mask, channel=new.mask_channel, loop=new.loop, synchro_start=True)

            video_path = find_file_with_extensions([path / "video"], [".webm", ".mp4"])

            if video_path:
                self.video = Movie(play=str(video_path.relative_to(config.gamedir)), channel="silent", play_callback=play_callback)
            # else:
            #     print(f"Warning: No video found for song {path}")

            # get name and song duration
            self.name = song_config.get("song", "name", fallback="Unknown")
            self.artist = song_config.get("song", "artist", fallback="Unknown")
            self.charter = song_config.get("song", "charter", fallback="Unknown")

            # read the actual chart file
            # chart file reference:
            # https://docs.google.com/document/d/1v2v0U-9HQ5qHeccpExDOLJ5CMPZZ3QytPmAG5WF0Kzs
            # print(f"Loading chart for song {path / 'notes.chart'}")
            # the CHart class has a class variable that sticks around between instantiations
            # due to how the library is designed, we can't get rid of it, so we need to clear it
            # before loading a new chart
            chparse.chart.Chart.instruments = {
                chparse.EXPERT: {},
                chparse.HARD: {},
                chparse.MEDIUM: {},
                chparse.EASY: {},
                chparse.NA: {},
            }
            with open(path / "notes.chart") as f:
                chart = chparse.load(f)

            # extract valid note lists per difficulty
            # we only target guitar charts here
            self.notes = {}

            for difficulty, data in chart.instruments.items():
                if not data or difficulty.value is None:
                    continue
                notes = data.get(chparse.Instruments.GUITAR)
                if not notes:
                    continue
                self.notes[difficulty.value.lower()] = notes

            self.tempo_events = [item for item in chart.sync_track if item.kind == chparse.NoteTypes.BPM]

            self.resolution = float(chart.Resolution)

            try:
                self.duration = song_config.getfloat("song", "song_length") / 1000.0
            except:
                tmp_diff = list(self.notes.keys())[0]
                self.duration = float(sorted(list(self.notes[tmp_diff]) + self.tempo_events, key=lambda n: n.time)[-1].time)

            self.duration += self.delay

        def difficulties(self):
            return list(self.notes.keys())

        def load(self, difficulty):
            # compute note times in seconds
            # this is similar to how MIDI works
            tempo = 120.0
            last_tick = 0.0
            wall_time = 0.0
            self.onset_times = []
            for note in sorted(list(self.notes[difficulty]) + self.tempo_events, key=lambda n: n.time):
                if isinstance(note, chparse.note.Event):
                    continue

                if note.kind == chparse.NoteTypes.BPM:
                    tempo = float(note.value) / 1000.0

                delta_ms = (float(note.time) - last_tick) / self.resolution * 60.0 / tempo
                wall_time += delta_ms

                if note.kind == chparse.NoteTypes.NOTE:
                    self.onset_times.append((wall_time + self.compensation + self.delay, note.fret))

                last_tick = float(note.time)

            # compute maximum possible score
            self.max_score = len(self.onset_times) * SCORES["perfect"]

        def compute_percent(self, score):
            return round(score / float(self.max_score) * 100)

    class CustomAudioPositionValue(BarValue, DictEquality):
        def __init__(self, channel="music", update_interval=0.1, duration=None):
            self.channel = channel
            self.update_interval = update_interval
            self.static_duration = duration
            self.adjustment = None

        def get_pos_duration(self):
            pos = renpy.music.get_pos(self.channel) or 0.0
            if self.static_duration:
                return pos, self.static_duration
            duration = renpy.music.get_duration(self.channel) or 1.0
            return pos, duration

        def get_adjustment(self):
            pos, duration = self.get_pos_duration()
            self.adjustment = ui.adjustment(value=pos, range=duration, adjustable=False)
            return self.adjustment

        def periodic(self, st):
            pos, duration = self.get_pos_duration()
            self.adjustment.set_range(duration)
            self.adjustment.change(pos)
            return self.update_interval

    class RhythmGameDisplayable(renpy.Displayable):
        def __init__(self, song):
            super(RhythmGameDisplayable, self).__init__()

            self.started = False
            self.song = song
            self.has_ended = False

            # offset from the left of the screen
            self.x_offset = 500

            self.track_bar_width = 9
            self.track_bar_height = int(config.screen_height * 1.7)

            self.horizontal_bar_height = 8

            self.note_width = 30 # width of the note image
            # zoom in on the note when it is hittable
            self.zoom_scale = 1.2
            # offset the note to the right so it shows at the center of the track
            self.note_xoffset = (self.track_bar_width - self.note_width) / 2
            self.note_xoffset_large = (self.track_bar_width - self.note_width * self.zoom_scale) / 2
            # place the hit text some spacing from the end of the track bar
            self.hit_text_yoffset = 5

            # since the notes are scrolling from the screen top to bottom
            # they appear on the tracks prior to the onset time
            # this scroll time is also the note's entire lifespan time before it's either
            # hit or considered a miss
            # the note now takes 3 seconds to travel the screen
            # can be used to set difficulty level of the game
            self.note_offset = 3.0
            # speed = distance / time
            self.note_speed = config.screen_height / self.note_offset

            # number of track bars
            self.num_track_bars = 5
            # drawing position
            # self.track_bar_spacing = (config.screen_width - self.x_offset * 2) / (self.num_track_bars - 1)
            self.track_bar_spacing = 66
            # the xoffset of each track bar
            self.track_xoffsets = {
                track_idx: self.x_offset + track_idx * self.track_bar_spacing
                for track_idx in range(self.num_track_bars)
            }

            # define the notes' onset times
            self.onset_times = [t for t, _ in song.onset_times]

            # assign notes to tracks, same length as self.onset_times
            self.track_indices = [fret for _, fret in song.onset_times]

            # map track_idx to a list of active note timestamps
            self.active_notes_per_track = {track_idx: [] for track_idx in range(self.num_track_bars)}

            self.track_highlight = {track_idx: False for track_idx in range(self.num_track_bars)}

            # detect and record score
            self.score = 0
            # map onset timestamp to whether it has been hit, initialized to False
            self.onset_hits = {onset: {i: None for i in range(self.num_track_bars)} for onset in self.onset_times}
            # if the note is hit within 0.3 seconds of its actual onset time
            # we consider it a hit
            # can set different threshold for Good, Great hit scoring
            # miss if you hit the note too early, 0.1 second window before note becomes hittable
            self.prehit_miss_threshold = 0.2 # seconds
            self.hit_threshold = 0.2 # seconds
            self.perfect_threshold = 0.1 # seconds
            # therefore good is between hit and perfect
            ## visual explanation
            #     miss       good       perfect    good      miss
            # (-0.4, -0.3)[-0.3, -0.1)[-0.1, 0.1](0.1, 0.3](0.3, inf)

            # map pygame key code to track idx
            if persistent.keymap == "numbers":
                self.keycode_to_track_idx = {
                    pygame.K_1: 0,
                    pygame.K_2: 1,
                    pygame.K_3: 2,
                    pygame.K_4: 3,
                    pygame.K_5: 4,
                }
            elif persistent.keymap == "numbers_left":
                self.keycode_to_track_idx = {
                    pygame.K_1: 0,
                    pygame.K_2: 1,
                    pygame.K_3: 2,
                    pygame.K_4: 3,
                    pygame.K_SPACE: 4,
                }
            elif persistent.keymap == "numbers_right":
                self.keycode_to_track_idx = {
                    pygame.K_SPACE: 0,
                    pygame.K_7: 1,
                    pygame.K_8: 2,
                    pygame.K_9: 3,
                    pygame.K_0: 4,
                }
            elif persistent.keymap == "dfsjk":
                self.keycode_to_track_idx = {
                    pygame.K_d: 0,
                    pygame.K_f: 1,
                    pygame.K_SPACE: 2,
                    pygame.K_j: 3,
                    pygame.K_k: 4,
                }

            # define the drawables
            self.miss_text_drawable = Transform(Text("Miss!", color="#fff", size=15), rotate=-90, xoffset=-18) # small text
            self.good_text_drawable = Transform(Text("Good!", color="#fff", size=20), rotate=-90, xoffset=-30) # big text
            self.perfect_text_drawable = Transform(Text("Perfect!", color="#fff", size=20), rotate=-90, xoffset=-35) # bigger text
            self.track_bar_drawable = Solid("#fff", xsize=self.track_bar_width, ysize=self.track_bar_height)
            self.track_bar_drawable_highlight = Solid("#ff0000", xsize=self.track_bar_width, ysize=self.track_bar_height)
            self.horizontal_bar_drawable = Solid("#fff", xsize=config.screen_width, ysize=self.horizontal_bar_height)

            # map track_idx to the note drawables
            self.note_drawables = {
                0: Image(IMG_0),
                1: Image(IMG_1),
                2: Image(IMG_2),
                3: Image(IMG_3),
                4: Image(IMG_4),
            }

            # map track_idx to the enlarged note drawables
            self.note_drawables_large = {
                0: Transform(self.note_drawables[0], zoom=self.zoom_scale),
                1: Transform(self.note_drawables[1], zoom=self.zoom_scale),
                2: Transform(self.note_drawables[2], zoom=self.zoom_scale),
                3: Transform(self.note_drawables[3], zoom=self.zoom_scale),
                4: Transform(self.note_drawables[4], zoom=self.zoom_scale),
            }

            if persistent.keymap == "numbers":
                self.keymap_drawable = {
                    0: Text("1", color="#fff", size=25),
                    1: Text("2", color="#fff", size=25),
                    2: Text("3", color="#fff", size=25),
                    3: Text("4", color="#fff", size=25),
                    4: Text("5", color="#fff", size=25),
                }
            elif persistent.keymap == "numbers_left":
                self.keymap_drawable = {
                    0: Text("1", color="#fff", size=25),
                    1: Text("2", color="#fff", size=25),
                    2: Text("3", color="#fff", size=25),
                    3: Text("4", color="#fff", size=25),
                    4: Text("S", color="#fff", size=25),
                }
            elif persistent.keymap == "numbers_right":
                self.keymap_drawable = {
                    0: Text("S", color="#fff", size=25),
                    1: Text("7", color="#fff", size=25),
                    2: Text("8", color="#fff", size=25),
                    3: Text("9", color="#fff", size=25),
                    4: Text("0", color="#fff", size=25),
                }
            elif persistent.keymap == "dfsjk":
                self.keymap_drawable = {
                    0: Text("D", color="#fff", size=25),
                    1: Text("F", color="#fff", size=25),
                    2: Text("S", color="#fff", size=25),
                    3: Text("J", color="#fff", size=25),
                    4: Text("K", color="#fff", size=25),
                }

            # record all the drawables for self.visit
            self.drawables = [
                self.miss_text_drawable,
                self.good_text_drawable,
                self.perfect_text_drawable,
                self.track_bar_drawable,
                self.track_bar_drawable_highlight,
                self.horizontal_bar_drawable,
            ]
            self.drawables.extend(list(self.note_drawables.values()))
            self.drawables.extend(list(self.note_drawables_large.values()))
            self.drawables.extend(list(self.keymap_drawable.values()))

            delay = f"<silence {song.delay}>" if song.delay > 0 else None

            # after all intializations are done, start playing the song
            if self.song.video_start_time > 0:
                if delay:
                    template = [delay, f"<silence {self.song.video_start_time}>"]
                else:
                    template = [f"<silence {self.song.video_start_time}>"]
                renpy.music.queue(template + [self.song.audio], channel=CHANNEL_RHYTHM_GAME, loop=False)
                if self.song.audio_guitar:
                    renpy.music.queue(template + [self.song.audio_guitar], channel=CHANNEL_RHYTHM_GAME_GUITAR, loop=False)
                if self.song.audio_rhythm:
                    renpy.music.queue(template + [self.song.audio_rhythm], channel=CHANNEL_RHYTHM_GAME_RHYTHM, loop=False)
            else:
                template = []
                if delay:
                    template.append(delay)
                renpy.music.queue(template + [self.song.audio], channel=CHANNEL_RHYTHM_GAME, loop=False)
                if self.song.audio_guitar:
                    renpy.music.queue(template + [self.song.audio_guitar], channel=CHANNEL_RHYTHM_GAME_GUITAR, loop=False)
                if self.song.audio_rhythm:
                    renpy.music.queue(template + [self.song.audio_rhythm], channel=CHANNEL_RHYTHM_GAME_RHYTHM, loop=False)

        def stats(self):
            hits_miss = 0
            hits_good = 0
            hits_perfect = 0

            for onset, data in self.onset_hits.items():
                for fret, status in data.items():
                    if status == "miss":
                        hits_miss += 1
                    elif status == "good":
                        hits_good += 1
                    elif status == "perfect":
                        hits_perfect += 1

            total = hits_miss + hits_good + hits_perfect
            # perfect hits give 100%, good hits give 75%, missed hits give nothing
            accuracy = (hits_perfect + hits_good * 0.75) / total if total > 0 else 0

            return {
                "max_score": self.song.max_score,
                "score_raw": self.score,
                "score_adjusted": self.score * accuracy,
                "score_perc": self.score / self.song.max_score,
                "score_adjusted_perc": (self.score * accuracy) / self.song.max_score,
                "accuracy": accuracy,
            }

        def render(self, width, height, st, at):
            render = renpy.Render(width, height)

            # draw the vertical tracks
            for track_idx in range(self.num_track_bars):
                # look up the offset for drawing
                x_offset = self.track_xoffsets[track_idx]
                # y = 0 starts from the top
                if self.track_highlight[track_idx]:
                    render.place(self.track_bar_drawable_highlight, x=x_offset, y=0)
                else:
                    render.place(self.track_bar_drawable, x=x_offset, y=0)

            for idx, d in self.keymap_drawable.items():
                render.place(d, x=self.track_xoffsets[idx], y=self.track_bar_height + 60)

            # draw the horizontal bar to indicate where the track ends
            # x = 0 starts from the left
            render.place(self.horizontal_bar_drawable, x=0, y=self.track_bar_height)

            if renpy.music.get_playing(channel=CHANNEL_RHYTHM_GAME) is None:
                self.has_ended = True
                renpy.timeout(0)  # ensure event is called one more time
                return render

            # update self.active_notes_per_track
            self.active_notes_per_track = self.get_active_notes_per_track(st)

            # render notes on each track
            for track_idx in self.active_notes_per_track:
                # look up track xoffset
                x_offset = self.track_xoffsets[track_idx]

                # loop through active notes
                for onset, note_timestamp in self.active_notes_per_track[track_idx]:
                    # render the notes that are active and haven't been hit
                    if self.onset_hits[onset][track_idx] is None:
                        time_delta = st - onset

                        # zoom in on the note if it is within the hit threshold
                        if abs(time_delta) <= self.hit_threshold:
                            note_drawable = self.note_drawables_large[track_idx]
                            note_xoffset = x_offset + self.note_xoffset_large
                        else:
                            note_drawable = self.note_drawables[track_idx]
                            note_xoffset = x_offset + self.note_xoffset

                        if time_delta > 0:
                            self.onset_hits[onset][track_idx] = "miss"
                            render.place(self.miss_text_drawable, x=x_offset, y=self.track_bar_height + self.hit_text_yoffset)

                        # compute where on the vertical axes the note is
                        # the vertical distance from the top that the note has already traveled
                        # is given by time * speed
                        note_distance_from_top = note_timestamp * self.note_speed
                        y_offset = self.track_bar_height - note_distance_from_top
                        render.place(note_drawable, x=note_xoffset, y=y_offset)
                    elif self.onset_hits[onset][track_idx] == "miss":
                        render.place(self.miss_text_drawable, x=x_offset, y=self.track_bar_height + self.hit_text_yoffset)
                    # else show hit text
                    elif self.onset_hits[onset][track_idx] == "good":
                        render.place(self.good_text_drawable, x=x_offset, y=self.track_bar_height + self.hit_text_yoffset)
                    elif self.onset_hits[onset][track_idx] == "perfect":
                        render.place(self.perfect_text_drawable, x=x_offset, y=self.track_bar_height + self.hit_text_yoffset)

            renpy.redraw(self, 0)
            return render

        def event(self, ev, x, y, st):
            if self.has_ended:
                # refresh the screen
                renpy.restart_interaction()
                return

            if ev.type not in (pygame.KEYUP, pygame.KEYDOWN):
                return

            # only handle the four keys we defined
            if ev.key not in self.keycode_to_track_idx:
                return

            # look up the track that correponds to the key pressed
            track_idx = self.keycode_to_track_idx[ev.key]

            if ev.type == pygame.KEYUP:
                self.track_highlight[track_idx] = False
                return

            self.track_highlight[track_idx] = True

            active_notes_on_track = self.active_notes_per_track[track_idx]

            # loop over active notes to check if one is hit
            note_hit = False
            for onset, _ in active_notes_on_track:
                if self.onset_hits[onset][track_idx] is not None or note_hit: # status already determined, one of miss, good, perfect
                    continue

                # compute the time difference between when the key is pressed
                # and when we consider the note hittable as defined by self.hit_threshold

                ## visual explanation
                #     miss       good       perfect    good      miss
                # (-0.4, -0.3)[-0.3, -0.1)[-0.1, 0.1](0.1, 0.3](0.3, inf)

                # time diff between curr time and actual onset
                time_delta = st - onset

                # any of the events below makes the note disappear from the screen
                # from narrowest range to widest range
                if -self.perfect_threshold <= time_delta <= self.perfect_threshold:
                    self.onset_hits[onset][track_idx] = "perfect"
                    self.score += SCORES["perfect"]
                    note_hit = True
                    renpy.restart_interaction()
                elif (-self.hit_threshold <= time_delta < self.perfect_threshold) or (self.perfect_threshold < time_delta <= self.hit_threshold):
                    self.onset_hits[onset][track_idx] = "good"
                    self.score += SCORES["good"]
                    note_hit = True
                    renpy.restart_interaction()
                elif (-self.prehit_miss_threshold <= time_delta < -self.hit_threshold):
                    self.onset_hits[onset][track_idx] = "miss"
                    renpy.restart_interaction()

        def get_active_notes_per_track(self, current_time):
            active_notes = {track_idx: [] for track_idx in range(self.num_track_bars)}

            for onset, track_idx in zip(self.onset_times, self.track_indices):
                # determine if this note should appear on the track
                time_before_appearance = onset - current_time
                if time_before_appearance < -0.5: # already below the bottom of the screen
                    continue
                # should be on screen
                # recall that self.note_offset is 3 seconds, the note's lifespan
                elif time_before_appearance <= self.note_offset:
                    active_notes[track_idx].append((onset, time_before_appearance))
                # there is still time before the next note should show
                # break out of the loop so we don't process subsequent notes that are even later
                elif time_before_appearance > self.note_offset:
                    break

            return active_notes

        def visit(self):
            return self.drawables
