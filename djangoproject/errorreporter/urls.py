from django.conf.urls import patterns, url

from errorreporter import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^crashreport_daily/(?P<date>\d{4}-\d{2}-\d{2})$', views.crashreport_daily, name='date'),
)
