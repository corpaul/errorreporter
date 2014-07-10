from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext, loader
from django.db.models import Count
from errorreporter.models import CrashReport


# Create your views here.
def index(request):
    context = {}
    return render(request, 'errorreporter/index.html', context)


def overview_crashreport_version(request):
    crashreports = sorted(CrashReport.objects.values('version').distinct(), reverse=True)
    print crashreports
    context = {'crashreports': crashreports}
    return render(request, 'errorreporter/overview_crashreport_version.html', context)


def overview_crashreport_daily(request):
    crashreports = sorted(CrashReport.objects.values('date').distinct(), reverse=True)
    context = {'crashreports': crashreports}
    return render(request, 'errorreporter/overview_crashreport_daily.html', context)


def crashreport_daily(request, date):
    crashreports = CrashReport.objects.filter(date=date)
    objects = CrashReport.objects.values('stack').filter(date=date)
    crashreports_aggr = objects.annotate(cnt=Count('stack')).order_by('-cnt')
    context = {'crashreports': crashreports,
               'crashreports_aggr': crashreports_aggr,
               'date': date}
    return render(request, 'errorreporter/crashreport_daily.html', context)


def crashreport_version(request, version):
    objects = CrashReport.objects.values('stack').filter(version=version)
    crashreports_aggr = objects.annotate(cnt=Count('stack')).order_by('-cnt')
    context = {'crashreports_aggr': crashreports_aggr,
               'version': version}
    return render(request, 'errorreporter/crashreport_version.html', context)
