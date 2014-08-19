from __future__ import unicode_literals

import json
from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

from mygpo.podcasts.models import Tag
from mygpo.users.models import Chapter as C, EpisodeUserState
from mygpo.chapters.models import Chapter
from mygpo.subscriptions.models import Subscription, PodcastConfig
from mygpo.history.models import EpisodeHistoryEntry
from mygpo.podcasts.models import Episode, Podcast

import logging
logger = logging.getLogger(__name__)


def to_maxlength(cls, field, val):
    """ Cut val to the maximum length of cls's field """
    max_length = cls._meta.get_field(field).max_length
    orig_length = len(val)
    if orig_length > max_length:
        val = val[:max_length]
        logger.warn('%s.%s length reduced from %d to %d',
                    cls.__name__, field, orig_length, max_length)

    return val


#class EpisodeUserState(Document, SettingsMixin):
#    ref_url       = StringProperty(required=True)
#    podcast_ref_url = StringProperty(required=True)


def migrate_estate(state):
    """ migrate a podcast state """

    try:
        user = User.objects.get(profile__uuid=state.user)
    except User.DoesNotExist:
        logger.warn("User with ID '{id}' does not exist".format(
            id=state.user))
        return

    try:
        podcast = Podcast.objects.all().get_by_any_id(state.podcast)
    except Podcast.DoesNotExist:
        logger.warn("Podcast with ID '{id}' does not exist".format(
            id=state.podcast))
        return

    try:
        episode = Episode.objects.filter(podcast=podcast).get_by_any_id(state.episode)
    except Episode.DoesNotExist:
        logger.warn("Episode with ID '{id}' does not exist".format(
            id=state.episode))
        return

    logger.info('Updating episode state for user {user} and episode {episode}'
                .format(user=user, episode=episode))

    for chapter in state.chapters:
        migrate_chapter(user, episode, chapter)

    for action in state.actions:
        migrate_eaction(user, episode, action)

    # only create the PodcastConfig obj if there are any settings
    # TODO: where to put the settings?
    if state.settings:
        logger.info('Updating {num} settings'.format(num=len(state.settings)))
        PodcastConfig.objects.update_or_create(user=user, podcast=podcast,
            defaults = {
                'settings': json.dumps(state.settings),
            }
        )

def migrate_chapter(user, episode, c):

    chapter, created = Chapter.objects.get_or_create(user=user,
                                                     episode=episode,
                                                     start=c.start,
                                                     end=c.end,
                                                    )
    chapter.label = c.label
    chapter.advertisement = c.advertisement
    chapter.save()


def migrate_eaction(user, episode, ea):

    try:
        client = user.client_set.get(id=action.device)
    except Client.DoesNotExist:
        logger.warn("Client '{cid}' does not exist; skipping".format(
            cid=action.device))
        return

    entry, created = EpisodeHistoryEntry.objects.get_or_create(
        user=user,
        client=client,
        episode=episode,
        action=ea.action,
        timestamp=ea.timestamp,
        defaults = {
            'created': ea.upload_timestamp,
            'started': ea.started,
            'stopped': ea.playmark,
            'total': ea.total,
            'podcast_ref_url': ea.podcast_ref_url,
            'episode_ref_url': ea.ref_url,
        },
    )

    if created:
        logger.info('Episode History Entry created: {user} {action} {episode}'
                    'on {client} @ {timestamp}'.format(user=user,
                        action=action, episode=episode, client=client,
                        timestamp=timestamp))



def get_subscribed_devices(state):
    """ device Ids on which the user subscribed to the podcast """
    devices = {}

    for action in state.actions:
        if action.action == "subscribe":
            if not action.device in state.disabled_devices:
                devices[action.device] = action.timestamp
        else:
            if action.device in devices:
                devices.pop(action.device)

    return devices



from couchdbkit import Database
db = Database('http://127.0.0.1:6984/mygpo_userdata_copy')
from couchdbkit.changes import ChangesStream, fold, foreach


MIGRATIONS = {
    'PodcastUserState': (None, None),
    'User': (None, None),
    'Suggestions': (None, None),
    'EpisodeUserState': (EpisodeUserState, migrate_estate),
}

def migrate_change(c):
    logger.info('Migrate seq %s', c['seq'])
    doc = c['doc']

    if not 'doc_type' in doc:
        logger.warn('Document contains no doc_type: %r', doc)
        return

    doctype = doc['doc_type']

    cls, migrate = MIGRATIONS[doctype]

    if cls is None:
        logger.warn("Skipping '%s'", doctype)
        return

    obj = cls.wrap(doc)
    migrate(obj)


def migrate(since=0):
    with ChangesStream(db,
                       feed="continuous",
                       heartbeat=True,
                       include_docs=True,
                       since=since,
                    ) as stream:
        for change in stream:
            migrate_change(change)
