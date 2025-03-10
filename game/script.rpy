transform delayed_appear:
    alpha 0.0
    pause 3.0
    ease 0.5 alpha 1.0

transform image_dissolve:
    alpha 0.0
    on hide:
        ease 0.5 alpha 0.0
    on appear:
        ease 0.5 alpha 0.75
    on show:
        ease 0.5 alpha 0.75

label before_main_menu:
    $ load_repo()
    if not persistent.cold_start:
        $ renpy.store.scenarios_loaded = True
    $ renpy.music.stop(CHANNEL_RHYTHM_GAME, fadeout=0.5)
    $ renpy.music.stop(CHANNEL_RHYTHM_GAME_GUITAR, fadeout=0.5)
    $ renpy.music.stop(CHANNEL_RHYTHM_GAME_RHYTHM, fadeout=0.5)
    return

init python:
    from pathlib import Path

    def load_repo():
        renpy.store.song_repo = SongRepository(compensation=-1.4 + (persistent.note_offset / 1000.0))
        renpy.store.song_repo.add_path(Path(config.gamedir) / "songs")
        renpy.store.song_repo.load()

transform rotate_in:
    matrixtransform RotateMatrix(0.0, 0.0, 0.0)
    ease 1.0 matrixtransform RotateMatrix(45.0, 0.0, 0.0)

transform rotate_out:
    matrixtransform RotateMatrix(45.0, 0.0, 0.0)
    ease 1.0 matrixtransform RotateMatrix(0.0, 0.0, 0.0)

label start:
    scene bg room

    "Welcome to the Ren'Py Rhythm Game! Choose a song you'd like to play."

    $ renpy.choice_for_skipping()

    # avoid rolling back and losing game state
    $ renpy.block_rollback()

    $ load_repo()

    $ quick_menu = False
    window hide

    call screen select_song(song_repo)

    $ song = _return

    if not isinstance(song, Song):
        "No song selected. Please try again."
        return

    stop music fadeout 1.0

    if len(song.difficulties()) > 1:
        call screen select_difficulty(song)
        $ difficulty = _return
    else:
        $ difficulty = song.difficulties()[0]

    $ song.load(difficulty)

    $ game = RhythmGameDisplayable(song)

    camera game_display:
        perspective True
        rotate_in

    show screen rhythm_game_bg(game) onlayer game_bg
    show screen rhythm_game_display(game) onlayer game_display
    call screen rhythm_game_ui(game) onlayer game_ui
    with dissolve

    camera game_display:
        rotate_out

    camera reset

    window show
    $ quick_menu = True

    if game.score > persistent.game_stats.get(song.name, {}).get("score_raw", 0):
        $ persistent.game_stats[song.name] = game.stats()

    "You finished with a score of [game.score]!"

    hide screen rhythm_game_bg onlayer game_bg
    hide screen rhythm_game_display onlayer game_display
    hide screen rhythm_game_ui onlayer game_ui
    scene black
    with dissolve

    jump start
