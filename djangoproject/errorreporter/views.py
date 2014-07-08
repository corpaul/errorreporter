from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext, loader
from errorreporter.models import CrashReport


# Create your views here.
def index(request):
    crashreports = sorted(CrashReport.objects.values('date').distinct(), reverse=True)
    context = {'crashreports': crashreports}
    return render(request, 'errorreporter/index.html', context)


def crashreport_daily(request, date):
    crashreports = CrashReport.objects.filter(date=date)
    context = {'crashreports': crashreports,
               'date': date}
    return render(request, 'errorreporter/crashreport_daily.html', context)
