# -*- coding: utf-8 -*-
"""
Data classes for all Discrivener messages, plus code
to deserialize them from JSON.
"""


import collections
import datetime
import enum
import typing

from oobabot import types


def object_pairs_hook(
    pairs: typing.List[typing.Tuple[str, typing.Any]]
) -> typing.List["DiscrivenerMessage"]:
    cls = MESSAGE_TYPE_TO_CLASS.get(pairs[0][0])
    if cls is not None and len(pairs) == 1:
        return cls(pairs[0][1])
    return collections.OrderedDict(pairs)


class DiscrivenerMessageType(str, enum.Enum):
    """
    Enumerates the different types of Discrivener messages.
    """

    CHANNEL_SILENT = "ChannelSilent"
    CONNECT = "Connect"
    DISCONNECT = "Disconnect"
    RECONNECT = "Reconnect"
    TRANSCRIPTION = "Transcription"
    USER_JOIN = "UserJoin"
    USER_LEAVE = "UserLeave"


class DiscrivenerMessage:
    """
    Base class for all Discrivener messages.
    """

    type: DiscrivenerMessageType


class ChannelSilentData(DiscrivenerMessage):
    """
    Represents whether any user is speaking in the channel.
    """

    def __init__(self, data: dict):
        self.type = DiscrivenerMessageType.CHANNEL_SILENT
        self.silent = bool(data)

    def __repr__(self):
        return f"ChannelSilent(silent={self.silent})"


class ConnectData(DiscrivenerMessage):
    """
    Represents us connecting or reconnecting to the voice channel.
    """

    def __init__(self, data: dict):
        self.type = DiscrivenerMessageType.CONNECT
        self.channel_id = data.get("channel_id")
        self.guild_id = data.get("guild_id")
        self.session_id = data.get("session_id")
        self.server = data.get("server")
        self.ssrc = data.get("ssrc")

    def __repr__(self):
        return (
            f"ConnectData(channel_id={self.channel_id}, "
            + f"guild_id={self.guild_id}, "
            + f"session_id={self.session_id}, "
            + f"server={self.server}, "
            + f"ssrc={self.ssrc})"
        )


class DisconnectData(DiscrivenerMessage):
    """
    Represents a disconnect from the voice channel.
    """

    def __init__(self, data: dict):
        self.type = DiscrivenerMessageType.DISCONNECT
        self.kind: str = data.get("kind")
        self.reason: str = data.get("reason")
        self.channel_id: int = data.get("channel_id")
        self.guild_id: int = data.get("guild_id")
        self.session_id: int = data.get("session_id")

    def __repr__(self):
        return (
            f"DisconnectData(kind={self.kind}, "
            + f"reason={self.reason}, "
            + f"channel_id={self.channel_id}, "
            + f"guild_id={self.guild_id}, "
            + f"session_id={self.session_id})"
        )


class UserJoinData(DiscrivenerMessage):
    """
    Represents a user joining a voice channel.
    """

    def __init__(self, data: dict):
        self.type = DiscrivenerMessageType.USER_JOIN
        self.user_id: int = data

    def __str__(self):
        return f"User #{self.user_id} joined voice channel"


class UserLeaveData(DiscrivenerMessage):
    """
    Represents a user leaving a voice channel.
    """

    def __init__(self, data: dict):
        self.type = DiscrivenerMessageType.USER_LEAVE
        self.user_id: int = data

    def __str__(self):
        return f"User #{self.user_id} left voice channel"


class TokenWithProbability:
    """
    Represents a token with a probability.
    """

    def __init__(self, data: dict):
        self.probability: int = data.get("p", 0)
        self.token_id: int = data.get("token_id", 0)
        self.token_text: str = str(data.get("token_text"))

    def __repr__(self):
        return (
            "TokenWithProbability("
            + f"probability={self.probability}, "
            + f"token_id={self.token_id}, "
            + f"token_text={self.token_text})"
        )


def to_datetime(message: dict) -> datetime.datetime:
    """
    Converts a message into a datetime object.
    """
    seconds: int = message.get("secs_since_epoch", 0)
    nanos: int = message.get("nanos_since_epoch", 0)
    return datetime.datetime.fromtimestamp(seconds + nanos / 1e9)


def to_duration(message: dict) -> datetime.timedelta:
    """
    Converts a message into a timedelta object.
    """
    seconds: int = message.get("secs", 0)
    nanos: int = message.get("nanos", 0)
    return datetime.timedelta(seconds=seconds, microseconds=nanos / 1e3)


class TextSegment:
    """
    Represents a single text segment of a transcribed message.
    """

    def __init__(self, message: dict):
        self.tokens_with_probability = [
            TokenWithProbability(data)
            for data in message.get("tokens_with_probability")
        ]
        self.start_offset_ms: int = message.get("start_offset_ms")
        self.end_offset_ms: int = message.get("end_offset_ms")

    def __repr__(self):
        return (
            f"TextSegment(tokens_with_probability={self.tokens_with_probability}, "
            + f"start_offset_ms={self.start_offset_ms}, "
            + f"end_offset_ms={self.end_offset_ms})"
        )

    def __str__(self) -> str:
        return "".join([t.token_text for t in self.tokens_with_probability])


class UserVoiceMessage(types.VoiceMessageWithTokens):
    """
    Represents a transcribed message.
    """

    def __init__(self, message: dict):
        self.type = DiscrivenerMessageType.TRANSCRIPTION
        self._processing_time: datetime.timedelta = to_duration(
            message.get("processing_time")
        )
        self._segments: typing.List[TextSegment] = [
            TextSegment(s) for s in message.get("segments")
        ]
        super().__init__(
            message.get("user_id"),
            to_datetime(message.get("start_timestamp")),
            to_duration(message.get("audio_duration")),
        )
        self._latency: datetime.timedelta = (
            datetime.datetime.now() - self._start_time - self._audio_duration
        )

    @property
    def processing_time(self):
        """
        Returns the processing time of the transcription.
        """
        return self._processing_time

    @property
    def latency(self):
        """
        Returns the latency of the transcription.
        """
        return self._latency

    @property
    def text(self) -> str:
        """
        Returns the text of the transcription.
        """
        return "".join([str(s) for s in self._segments])

    @property
    def is_bot(self) -> bool:
        """
        Returns whether the user is a bot.
        """
        return False

    @property
    def tokens_with_confidence(self) -> typing.List[typing.Tuple[str, int]]:
        """
        Returns the tokens with their confidence.
        """
        return [
            (t.token_text, t.probability)
            for s in self._segments
            for t in s.tokens_with_probability
        ]

    def __repr__(self) -> str:
        return (
            "UserVoiceMessage("
            + f"start_time={self._start_time}, "
            + f"user_id={self._user_id}, "
            + f"audio_duration={self._audio_duration}, "
            + f"processing_time={self._processing_time}, "
            + f"segments={self._segments}, "
            + f"latency={self._latency})"
        )


MESSAGE_TYPE_TO_CLASS = {
    DiscrivenerMessageType.CHANNEL_SILENT: ChannelSilentData,
    DiscrivenerMessageType.CONNECT: ConnectData,
    DiscrivenerMessageType.DISCONNECT: DisconnectData,
    DiscrivenerMessageType.RECONNECT: ConnectData,
    DiscrivenerMessageType.TRANSCRIPTION: UserVoiceMessage,
    DiscrivenerMessageType.USER_JOIN: UserJoinData,
    DiscrivenerMessageType.USER_LEAVE: UserLeaveData,
}
