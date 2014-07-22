from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext, loader
from django.db.models import Count
from errorreporter.models import CrashReport
import time
import operator

# Create your views here.
def index(request):
    context = {}
    return render(request, 'errorreporter/index.html', context)


def overview_crashreport_version(request):
    crashreports = CrashReport.objects.values('version').annotate(cnt=Count('version')).order_by('-version')
    context = {'crashreports': crashreports}
    return render(request, 'errorreporter/overview_crashreport_version.html', context)


def overview_crashreport_daily(request):
    crashreports = CrashReport.objects.values('date').annotate(cnt=Count('date')).order_by('-date')
    context = {'crashreports': crashreports}
    return render(request, 'errorreporter/overview_crashreport_daily.html', context)


def crashreport_daily(request, date):
    crashreports = CrashReport.objects.filter(date=date)
    comments = compact_comments(crashreports)
    objects = CrashReport.objects.values('stack').filter(date=date)
    crashreports_aggr = objects.annotate(cnt=Count('stack')).order_by('-cnt')
    
    for c in crashreports_aggr:
        tmp = CrashReport.objects.filter(stack=c['stack']).first()
        c['id'] = tmp.id
        c['comments'] = comments[c['stack']]
        
    context = {'crashreports': crashreports,
               'crashreports_aggr': crashreports_aggr,
               'date': date}
    return render(request, 'errorreporter/crashreport_daily.html', context)


def crashreport_version(request, version):
    crashreports = CrashReport.objects.filter(version=version)
    comments = compact_comments(crashreports)
    objects = CrashReport.objects.values('stack').filter(version=version)
    crashreports_aggr = objects.annotate(cnt=Count('stack')).order_by('-cnt')
    
    # add some extra info to the aggregate reports
    for c in crashreports_aggr:
        tmp = CrashReport.objects.filter(stack=c['stack']).first()
        c['id'] = tmp.id
        c['comments'] = comments[c['stack']]
    
    formattedversion = version.replace(".", "_")
    
    context = {'crashreports': crashreports,
               'crashreports_aggr': crashreports_aggr,
               'version': version,
               'formattedversion': formattedversion}
    return render(request, 'errorreporter/crashreport_version.html', context)
 
def graph_stack_occurrences(request, stack_id):
    objects = CrashReport.objects.filter(id=stack_id)
    stack = objects.first()
    
    if stack:
        objects = CrashReport.objects.values('date').filter(stack=stack.stack)
        occurrences = objects.annotate(cnt=Count('date')).order_by('date')
    else:
        occurrences = None
    
    total = 0
    for o in occurrences:
        dtt = o['date'].timetuple()
        ts = time.mktime(dtt)
        o['ts'] = int(ts)*1000
        total = total + o['cnt']
        
    context = {
               'occurrences': occurrences,
               'total': total 
               }
    return render(request, 'errorreporter/graph_stack_occurrences.html', context)
            
def stacktrace(request, stack_id):
    objects = CrashReport.objects.filter(id=stack_id)
    stack = objects.first()
    context = {'c': stack}
    return render(request, 'errorreporter/stacktrace.html', context)
            
            
def compact_comments(objects):
    """
    Collect the comments for each stack trace in a more compact fashion, i.e.:
    Stack1 - comment1 - [id1,id2,...]. This is to prevent hundreds of lines with 'Not provided' in the reports.
    """
    comments = {}
    for o in objects:
        if not o.stack in comments.keys():
            comments[o.stack] = {}
        if not o.comments in comments[o.stack].keys():        
            comments[o.stack][o.comments] = []
        comments[o.stack][o.comments].append(o.id)
    return comments 
        