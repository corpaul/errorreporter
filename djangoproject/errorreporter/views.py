from django.shortcuts import render
from django.db.models import Count
from errorreporter.models import CrashReport
from django.shortcuts import redirect
import time


# Create your views here.
def index(request):
    return redirect('overview_daily')


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

    os_objects = CrashReport.objects.values('os').filter(date=date)
    os_info = os_objects.annotate(cnt=Count('os')).order_by('os')
    for o in os_info:
        o['descr'] = o['os']

    machine_objects = CrashReport.objects.values('machine').filter(date=date)
    machine_info = machine_objects.annotate(cnt=Count('machine')).order_by('machine')
    for m in machine_info:
        m['descr'] = m['machine']

    for c in crashreports_aggr:
        tmp = CrashReport.objects.filter(stack=c['stack']).first()
        c['id'] = tmp.id
        c['comments'] = comments[c['stack']]

    context = {'crashreports': crashreports,
               'crashreports_aggr': crashreports_aggr,
               'report_for': date,
               'fg_prefix': "fg_d" + date,
               'os_info': os_info,
               'machine_info': machine_info}
    return render(request, 'errorreporter/crashreport_aggr.html', context)


def crashreport_version(request, version):
    crashreports = CrashReport.objects.filter(version=version)
    comments = compact_comments(crashreports)
    objects = CrashReport.objects.values('stack').filter(version=version)
    crashreports_aggr = objects.annotate(cnt=Count('stack')).order_by('-cnt')

    os_objects = CrashReport.objects.values('os').filter(version=version)
    os_info = os_objects.annotate(cnt=Count('os')).order_by('os')
    for o in os_info:
        o['descr'] = o['os']

    machine_objects = CrashReport.objects.values('machine').filter(version=version)
    machine_info = machine_objects.annotate(cnt=Count('machine')).order_by('machine')
    for m in machine_info:
        m['descr'] = m['machine']

    # add some extra info to the aggregate reports
    for c in crashreports_aggr:
        tmp = CrashReport.objects.filter(stack=c['stack']).first()
        c['id'] = tmp.id
        c['comments'] = comments[c['stack']]

    formattedversion = version.replace(".", "_")

    context = {'crashreports': crashreports,
               'crashreports_aggr': crashreports_aggr,
               'report_for': version,
               'fg_prefix': "fg_v" + formattedversion,
               'os_info': os_info,
               'machine_info': machine_info}
    return render(request, 'errorreporter/crashreport_aggr.html', context)


def stacktrace_graphs(request, stack_id):
    objects = CrashReport.objects.filter(id=stack_id)
    stack = objects.first()

    if stack:
        objects = CrashReport.objects.values('date').filter(stack=stack.stack)
        occurrences = objects.annotate(cnt=Count('date')).order_by('date')
        os_objects = CrashReport.objects.values('os').filter(stack=stack.stack)
        os_info = os_objects.annotate(cnt=Count('os')).order_by('os')
        for o in os_info:
            o['descr'] = o['os']
        machine_objects = CrashReport.objects.values('machine').filter(stack=stack.stack)
        machine_info = machine_objects.annotate(cnt=Count('machine')).order_by('machine')
        for m in machine_info:
            m['descr'] = m['machine']
    else:
        occurrences = None
        os_info = None

    total = 0
    for o in occurrences:
        dtt = o['date'].timetuple()
        ts = time.mktime(dtt)
        o['ts'] = int(ts) * 1000
        total = total + o['cnt']

    context = {
               'occurrences': occurrences,
               'total': total,
               'os_info': os_info,
               'machine_info': machine_info
               }
    return render(request, 'errorreporter/stacktrace_graphs.html', context)


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
