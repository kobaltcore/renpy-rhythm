define IMG_UP = "images/renpy-rhythm/up.png"
define IMG_LEFT = "images/renpy-rhythm/left.png"
define IMG_RIGHT = "images/renpy-rhythm/right.png"
define IMG_DOWN = "images/renpy-rhythm/down.png"

define CHANNEL_RHYTHM_GAME = "rhythm_music"

define SCORE_GOOD = 6
define SCORE_PERFECT = 10

screen select_song_screen(songs):
    modal True

    frame:
        xalign 0.5
        yalign 0.5
        xpadding 30
        ypadding 30

        vbox:
            spacing 20

            label 'Click on a song to play' xalign 0.5

            vbox spacing 10:
                grid 3 len(songs) + 1:
                    xspacing 100
                    label 'Song Name'
                    label 'Highest Score'
                    label '% Perfect Hits'
                    for song in songs:
                        textbutton "{}".format(song.name[:15]) action [
                            Return(song)
                        ]
                        $ highest_score, highest_percent = persistent.rhythm_game_high_scores[song.name]
                        text str(highest_score)
                        text '([highest_percent]%)'

            textbutton _("Exit"):
                xalign 0.5
                action Return(None)

screen rhythm_game(rhythm_game_displayable):
    zorder 100

    zorder 100 # always on top, covering textbox, quick_menu
    # disable key handling for game keys
    key 'K_1' action NullAction()
    key 'K_2' action NullAction()
    key 'K_3' action NullAction()
    key 'K_4' action NullAction()
    key 'K_5' action NullAction()

    add Solid('#000')
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

init python:
    import os
    import pygame
    import chparse
    from configparser import ConfigParser

    renpy.music.register_channel(CHANNEL_RHYTHM_GAME)

    class Song():

        def __init__(self, path, compensation=0.2):
            # read metadata
            song_config = ConfigParser()
            song_config.read(os.path.join(path, "song.ini"))

            # find audio
            song_path = os.path.join(path, "song.ogg")
            if not os.path.isfile(song_path):
                song_path = os.path.join(path, "guitar.ogg")
            self.audio = os.path.relpath(song_path, config.gamedir)

            # find optional video
            self.video = None
            video_path = os.path.join(path, "video.mp4")
            if os.path.isfile(video_path):
                self.video_path = os.path.relpath(video_path, config.gamedir)

            # get name and song duration
            self.name = song_config.get("song", "name")
            self.duration = float(song_config.get("song", "song_length")) / 1000.0

            # read the actual chart file
            # chart file reference:
            # https://docs.google.com/document/d/1v2v0U-9HQ5qHeccpExDOLJ5CMPZZ3QytPmAG5WF0Kzs
            with open(os.path.join(path, "notes.chart")) as f:
                chart = chparse.load(f)

            # extract valid note lists per difficulty
            # we only target guitar charts here
            # by default we select the easiest difficulty
            self.notes = {}
            expert = chart.instruments[chparse.Difficulties.EXPERT]
            if expert and expert.get(chparse.Instruments.GUITAR):
                self.notes["expert"] = expert[chparse.Instruments.GUITAR]
                self.difficulty = "expert"
            hard = chart.instruments[chparse.Difficulties.HARD]
            if hard and hard.get(chparse.Instruments.GUITAR):
                self.notes["hard"] = hard[chparse.Instruments.GUITAR]
                self.difficulty = "hard"
            medium = chart.instruments[chparse.Difficulties.MEDIUM]
            if medium and medium.get(chparse.Instruments.GUITAR):
                self.notes["medium"] = medium[chparse.Instruments.GUITAR]
                self.difficulty = "medium"
            easy = chart.instruments[chparse.Difficulties.EASY]
            if easy and easy.get(chparse.Instruments.GUITAR):
                self.notes["easy"] = easy[chparse.Instruments.GUITAR]
                self.difficulty = "easy"
            # na = chart.instruments[chparse.Difficulties.NA]
            # if na and na.get(chparse.Instruments.GUITAR):
            #     notes["na"] = na[chparse.Instruments.GUITAR]
            #     self.difficulty = "na"

            # extract tempo events from sync track
            tempo_events = [item for item in chart.sync_track if item.kind == chparse.NoteTypes.BPM]

            # compute note times in seconds
            # this is similar to how MIDI works
            tempo = 120.0
            last_tick = 0.0
            wall_time = 0.0
            resolution = float(chart.Resolution)
            self.onset_times = []
            for note in sorted(list(self.notes[self.difficulty]) + tempo_events, key=lambda n: n.time):
                if isinstance(note, chparse.note.Event):
                    continue
                delta_ms = (float(note.time) - last_tick) / resolution * 60.0 / tempo
                wall_time += delta_ms
                if note.kind == chparse.NoteTypes.NOTE:
                    self.onset_times.append((wall_time + compensation, note.fret))
                last_tick = float(note.time)
                if note.kind == chparse.NoteTypes.BPM:
                    tempo = float(note.value) / 1000.0

            # compute maximum possible score
            self.max_score = len(self.onset_times) * SCORE_PERFECT

        def compute_percent(self, score):
            return round(score / float(self.max_score) * 100)

    class CustomAudioPositionValue(BarValue, DictEquality):
        def __init__(self, channel='music', update_interval=0.1, duration=None):
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
            self.x_offset = 400

            self.track_bar_width = 12
            self.track_bar_height = int(config.screen_height * 0.85)

            self.horizontal_bar_height = 8

            self.note_width = 50 # width of the note image
            # zoom in on the note when it is hittable
            self.zoom_scale = 1.2
            # offset the note to the right so it shows at the center of the track
            self.note_xoffset = (self.track_bar_width - self.note_width) / 2
            self.note_xoffset_large = (self.track_bar_width - self.note_width * self.zoom_scale) / 2
            # place the hit text some spacing from the end of the track bar
            self.hit_text_yoffset = 30

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
            self.track_bar_spacing = (config.screen_width - self.x_offset * 2) / (self.num_track_bars - 1)
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

            # detect and record score
            self.score = 0
            # map onset timestamp to whether it has been hit, initialized to False
            self.onset_hits = {onset: None for onset in self.onset_times}
            # if the note is hit within 0.3 seconds of its actual onset time
            # we consider it a hit
            # can set different threshold for Good, Great hit scoring
            # miss if you hit the note too early, 0.1 second window before note becomes hittable
            self.prehit_miss_threshold = 0.4 # seconds
            self.hit_threshold = 0.2 # seconds
            self.perfect_threshold = 0.1 # seconds
            # therefore good is between hit and perfect
            ## visual explanation
            #     miss       good       perfect    good      miss
            # (-0.4, -0.3)[-0.3, -0.1)[-0.1, 0.1](0.1, 0.3](0.3, inf)

            # map pygame key code to track idx
            self.keycode_to_track_idx = {
                pygame.K_1: 0,
                pygame.K_2: 1,
                pygame.K_3: 2,
                pygame.K_4: 3,
                pygame.K_5: 4,
            }

            # define the drawables
            self.miss_text_drawable = Text("Miss!", color="#fff", size=20) # small text
            self.good_text_drawable = Text("Good!", color="#fff", size=30) # big text
            self.perfect_text_drawable = Text("Perfect!", color="#fff", size=40) # bigger text
            self.track_bar_drawable = Solid("#fff", xsize=self.track_bar_width, ysize=self.track_bar_height)
            self.horizontal_bar_drawable = Solid("#fff", xsize=config.screen_width, ysize=self.horizontal_bar_height)

            # map track_idx to the note drawables
            self.note_drawables = {
                0: Image(IMG_LEFT),
                1: Image(IMG_UP),
                2: Image(IMG_DOWN),
                3: Image(IMG_RIGHT),
                4: Image(IMG_RIGHT),
            }

            # map track_idx to the enlarged note drawables
            self.note_drawables_large = {
                0: Transform(self.note_drawables[0], zoom=self.zoom_scale),
                1: Transform(self.note_drawables[1], zoom=self.zoom_scale),
                2: Transform(self.note_drawables[2], zoom=self.zoom_scale),
                3: Transform(self.note_drawables[3], zoom=self.zoom_scale),
                4: Transform(self.note_drawables[4], zoom=self.zoom_scale),
            }

            # record all the drawables for self.visit
            self.drawables = [
                self.miss_text_drawable,
                self.good_text_drawable,
                self.perfect_text_drawable,
                self.track_bar_drawable,
                self.horizontal_bar_drawable,
            ]
            self.drawables.extend(list(self.note_drawables.values()))
            self.drawables.extend(list(self.note_drawables_large.values()))

            # after all intializations are done, start playing the song
            renpy.music.queue([self.song.audio], channel=CHANNEL_RHYTHM_GAME, loop=False)

        def render(self, width, height, st, at):
            render = renpy.Render(width, height)

            # draw the vertical tracks
            for track_idx in range(self.num_track_bars):
                # look up the offset for drawing
                x_offset = self.track_xoffsets[track_idx]
                # y = 0 starts from the top
                render.place(self.track_bar_drawable, x=x_offset, y=0)

            # draw the horizontal bar to indicate where the track ends
            # x = 0 starts from the left
            render.place(self.horizontal_bar_drawable, x=0, y=self.track_bar_height)

            # update self.active_notes_per_track
            self.active_notes_per_track = self.get_active_notes_per_track(st)

            # render notes on each track
            for track_idx in self.active_notes_per_track:
                # look up track xoffset
                x_offset = self.track_xoffsets[track_idx]

                # loop through active notes
                for onset, note_timestamp in self.active_notes_per_track[track_idx]:
                    # render the notes that are active and haven't been hit
                    if self.onset_hits[onset] is None:
                        # zoom in on the note if it is within the hit threshold
                        if abs(st - onset) <= self.hit_threshold:
                            note_drawable = self.note_drawables_large[track_idx]
                            note_xoffset = x_offset + self.note_xoffset_large
                        else:
                            note_drawable = self.note_drawables[track_idx]
                            note_xoffset = x_offset + self.note_xoffset

                        # compute where on the vertical axes the note is
                        # the vertical distance from the top that the note has already traveled
                        # is given by time * speed
                        note_distance_from_top = note_timestamp * self.note_speed
                        y_offset = self.track_bar_height - note_distance_from_top
                        render.place(note_drawable, x=note_xoffset, y=y_offset)
                    elif self.onset_hits[onset] == "miss":
                        render.place(self.miss_text_drawable, x=x_offset, y=self.track_bar_height + self.hit_text_yoffset)
                    # else show hit text
                    elif self.onset_hits[onset] == "good":
                        render.place(self.good_text_drawable, x=x_offset, y=self.track_bar_height + self.hit_text_yoffset)
                    elif self.onset_hits[onset] == "perfect":
                        render.place(self.perfect_text_drawable, x=x_offset, y=self.track_bar_height + self.hit_text_yoffset)

            renpy.redraw(self, 0)
            return render

        def event(self, ev, x, y, st):
            if self.has_ended:
                # refresh the screen
                renpy.restart_interaction()
                return

            # check if some keys have been pressed
            if ev.type == pygame.KEYDOWN:
                # only handle the four keys we defined
                if not ev.key in self.keycode_to_track_idx:
                    return
                # look up the track that correponds to the key pressed
                track_idx = self.keycode_to_track_idx[ev.key]

                active_notes_on_track = self.active_notes_per_track[track_idx]

                # loop over active notes to check if one is hit
                for onset, _ in active_notes_on_track:
                    if self.onset_hits[onset] is not None: # status already determined, one of miss, good, perfect
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
                        self.onset_hits[onset] = "perfect"
                        self.score += SCORE_PERFECT
                        renpy.restart_interaction()
                    elif (-self.hit_threshold <= time_delta < self.perfect_threshold) or (self.perfect_threshold < time_delta <= self.hit_threshold):
                        self.onset_hits[onset] = "good"
                        self.score += SCORE_GOOD
                        renpy.restart_interaction()
                    elif (-self.prehit_miss_threshold <= time_delta < -self.hit_threshold):
                        self.onset_hits[onset] = "miss"
                        renpy.restart_interaction()

        def get_active_notes_per_track(self, current_time):
            active_notes = {track_idx: [] for track_idx in range(self.num_track_bars)}

            for onset, track_idx in zip(self.onset_times, self.track_indices):
                # determine if this note should appear on the track
                time_before_appearance = onset - current_time
                if time_before_appearance < 0: # already below the bottom of the screen
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
