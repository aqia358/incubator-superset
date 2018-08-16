# -*- coding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import datetime as dt
import pendulum
from sqlalchemy.types import DateTime, TypeDecorator

# UTC time zone as a tzinfo instance.
utc = pendulum.timezone('UTC')
# utc = pendulum.timezone('Asia/Shanghai')

def is_localized(value):
    """
    Determine if a given datetime.datetime is aware.
    The concept is defined in Python's docs:
    http://docs.python.org/library/datetime.html#datetime.tzinfo
    Assuming value.tzinfo is either None or a proper datetime.tzinfo,
    value.utcoffset() implements the appropriate logic.
    """
    return value.utcoffset() is not None


def is_naive(value):
    """
    Determine if a given datetime.datetime is naive.
    The concept is defined in Python's docs:
    http://docs.python.org/library/datetime.html#datetime.tzinfo
    Assuming value.tzinfo is either None or a proper datetime.tzinfo,
    value.utcoffset() implements the appropriate logic.
    """
    return value.utcoffset() is None


def utcnow():
    """
    Get the current date and time in UTC
    :return:
    """

    # pendulum utcnow() is not used as that sets a TimezoneInfo object
    # instead of a Timezone. This is not pickable and also creates issues
    # when using replace()
    d = dt.datetime.utcnow()
    d = d.replace(tzinfo=utc)

    return d.astimezone(TIMEZONE)


def convert_to_utc(value):
    """
    Returns the datetime with the default timezone added if timezone
    information was not associated
    :param value: datetime
    :return: datetime with tzinfo
    """
    if not value:
        return value

    if not is_localized(value):
        value = pendulum.instance(value, TIMEZONE)

    return value.astimezone(TIMEZONE)


def utc_to_local(value):
    if not is_localized(value):
        raise ValueError(
            "utc_to_local expects a utc datetime, got %s" % value)
    return value.astimezone(TIMEZONE)


def make_aware(value, timezone=None):
    """
    Make a naive datetime.datetime in a given time zone aware.

    :param value: datetime
    :param timezone: timezone
    :return: localized datetime in settings.TIMEZONE or timezone

    """
    if timezone is None:
        timezone = TIMEZONE

    # Check that we won't overwrite the timezone of an aware datetime.
    if is_localized(value):
        raise ValueError(
            "make_aware expects a naive datetime, got %s" % value)

    if hasattr(timezone, 'localize'):
        # This method is available for pytz time zones.
        return timezone.localize(value)
    elif hasattr(timezone, 'convert'):
        # For pendulum
        return timezone.convert(value)
    else:
        # This may be wrong around DST changes!
        return value.replace(tzinfo=timezone)


def make_naive(value, timezone=None):
    """
    Make an aware datetime.datetime naive in a given time zone.

    :param value: datetime
    :param timezone: timezone
    :return: naive datetime
    """
    if timezone is None:
        timezone = TIMEZONE

    # Emulate the behavior of astimezone() on Python < 3.6.
    if is_naive(value):
        raise ValueError("make_naive() cannot be applied to a naive datetime")

    o = value.astimezone(timezone)

    # cross library compatibility
    naive = dt.datetime(o.year,
                        o.month,
                        o.day,
                        o.hour,
                        o.minute,
                        o.second,
                        o.microsecond)

    return naive


def datetime(*args, **kwargs):
    """
    Wrapper around datetime.datetime that adds settings.TIMEZONE if tzinfo not specified

    :return: datetime.datetime
    """
    if 'tzinfo' not in kwargs:
        kwargs['tzinfo'] = TIMEZONE

    return dt.datetime(*args, **kwargs)


def parse(string):
    """
    Parse a time string and return an aware datetime
    :param string: time string
    """
    return pendulum.parse(string, tz=TIMEZONE)


class LocalDateTime(TypeDecorator):
    """Almost equivalent to :class:`~sqlalchemy.types.DateTime` with
    ``timezone=True`` option, but it differs from that by:

    - Never silently take naive :class:`~datetime.datetime`, instead it
      always raise :exc:`ValueError` unless time zone aware value.
    - :class:`~datetime.datetime` value's :attr:`~datetime.datetime.tzinfo`
      is always converted to TIMEZONE.
    - Unlike SQLAlchemy's built-in :class:`~sqlalchemy.types.DateTime`,
      it never return naive :class:`~datetime.datetime`, but time zone
      aware value, even with SQLite or MySQL.

    """

    impl = DateTime(timezone=True)

    def process_bind_param(self, value, dialect):
        if value is not None:
            if not isinstance(value, dt.datetime):
                raise TypeError('expected datetime.datetime, not ' +
                                repr(value))
            elif value.tzinfo is None:
                raise ValueError('naive datetime is disallowed')
            return value.astimezone(TIMEZONE)

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=TIMEZONE)
        return value
