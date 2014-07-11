from django.conf.urls import patterns, url

from errorreporter import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^index$', views.index, name='index'),
    url(r'^overview_crashreport_daily$', views.overview_crashreport_daily, name='overview_daily'),
    url(r'^overview_crashreport_version$', views.overview_crashreport_version, name='overview_version'),
    url(r'^crashreport_daily/(?P<date>\d{4}-\d{2}-\d{2})$', views.crashreport_daily, name='date'),
    url(r'^crashreport_version/(?P<version>.+)$', views.crashreport_version, name='version'),
    url(r'^graph_stack_occurrences/(?P<stack_id>.+)$', views.graph_stack_occurrences, name='stack_id'),
)
