init python:
    import os
    from glob import glob

    songs = []
    for file in glob(os.path.join(config.gamedir, "songs", "*")):
        songs.append(Song(file))


    for song in songs:
        if song.name not in persistent.rhythm_game_high_scores:
            persistent.rhythm_game_high_scores[song.name] = (0, 0)

label start:
    scene bg room

    "Welcome to the Ren'Py Rhythm Game! Choose a song you'd like to play."

    window hide
    $ _game_menu_screen = None
    $ renpy.block_rollback()

    call screen select_song_screen(songs)

    if not isinstance(_return, Song):
        jump start

    $ game = RhythmGameDisplayable(_return)

    call screen rhythm_game(game)

    # TODO: set highscore if new score is higher than existing one
    # game.score
    python:
        current_high_score, current_percent = persistent.rhythm_game_high_scores[game.song.name]
        if current_high_score < game.score:
            persistent.rhythm_game_high_scores[game.song.name] = (game.score, game.song.compute_percent(game.score))

    $ _game_menu_screen = 'save'
    $ renpy.block_rollback()

    "Nice work hitting those notes! Hope you enjoyed the game."

    return

# a simpler way to launch the minigame 
label test:
    e "Welcome to the Ren'Py Rhythm Game! Ready for a challenge?"
    window hide
    $ quick_menu = False

    # avoid rolling back and losing chess game state
    $ renpy.block_rollback()

    $ song = Song('Isolation', 'audio/Isolation.mp3', 'audio/Isolation.beatmap.txt', beatmap_stride=2)
    $ rhythm_game_displayable = RhythmGameDisplayable(song)
    call screen rhythm_game(rhythm_game_displayable)

    # avoid rolling back and entering the chess game again
    $ renpy.block_rollback()

    # restore rollback from this point on
    $ renpy.checkpoint()

    $ quick_menu = True
    window show

    return