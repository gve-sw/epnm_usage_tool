"""
   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
"""
URL mapping of the application
"""

from django.conf.urls import url
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [

    url(r'^$', views.index),
    url(r'^auth/$', views.auth_view),
    url(r'^groupemail/$', views.send_group_email_view),
    url(r'^deviceemail/$', views.send_device_email_view),
    url(r'^login/$', views.login_view, name='login'),
    url(r'^location/(?P<loc>.*)/$', views.index, name='location'),
    url(r'^device/(?P<dev>.*)/$', views.index, name='device'),
    url(r'^alarms/(?P<location>.*)/$', views.index, name='loc_alarms'),

    # Angular mappings
    url(r'^home/?$', views.index),
    url(r'^ng/home/?$', views.home),
    url(r'^ng/main/?$', views.main),
    url(r'^ng/location/(?P<loc>.*)/$', views.location_landing),
    url(r'^ng/device/(?P<dev>.*)/$', views.device_landing),
    url(r'^ng/alarms/(?P<location>.*)/$', views.location_dump),

]
