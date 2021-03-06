#
# This file is part of my.gpodder.org.
#
# my.gpodder.org is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# my.gpodder.org is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public
# License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with my.gpodder.org. If not, see <http://www.gnu.org/licenses/>.
#

import os.path
from django.conf.urls import include, url, patterns
from django.contrib import admin
from django.conf import settings

# strip the leading "/"
static_prefix = settings.STATIC_URL[1:]

# This URLs should be always be served, even during maintenance mode
urlpatterns = patterns('',
    (r'^%s(?P<path>.*)$' % static_prefix, 'django.contrib.staticfiles.views.serve')
)


# Check for maintenace mode
from django.conf import settings
if settings.MAINTENANCE:
    urlpatterns += patterns('mygpo.web.utils',
        (r'', 'maintenance'),
    )


# URLs are still registered during maintenace mode because we need to
# build links from them (eg login-link).
urlpatterns += patterns('',
    (r'^',           include('mygpo.web.urls')),
    (r'^',           include('mygpo.directory.urls')),
    (r'^',           include('mygpo.api.urls')),
    (r'^',           include('mygpo.userfeeds.urls')),
    (r'^',           include('mygpo.share.urls')),
    (r'^',           include('mygpo.history.urls')),
    (r'^',           include('mygpo.subscriptions.urls')),
    (r'^',           include('mygpo.users.urls')),
    (r'^',           include('mygpo.podcastlists.urls')),
    (r'^suggestions/', include('mygpo.suggestions.urls')),
    (r'^publisher/', include('mygpo.publisher.urls')),
    (r'^administration/', include('mygpo.administration.urls')),
    (r'^pubsub/',    include('mygpo.pubsub.urls')),
 url(r'^admin/',     include(admin.site.urls)),
)
