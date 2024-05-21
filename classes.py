class Track:
    def __init__(self, title, artist, length, audio_id):
        self.title = title
        self.artist = artist
        self.length = length
        self.id = audio_id


class Artist:
    def __init__(self, name, followers, image_id):
        self.title = name
        self.follows = followers
        self.image = image_id


class Time:
    def __init__(self, minutes, seconds):
        self.min = minutes
        self.sec = seconds

    def __init__(self, seconds):
        self.min = seconds / 60
        self.sec = seconds % 60

