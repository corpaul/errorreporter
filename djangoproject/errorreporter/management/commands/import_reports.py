from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

import bz2
import pickle
import os
import logging
import re
import codecs
import subprocess
from StringIO import StringIO
from errorreporter.models import CrashReport
from django.conf import settings
from django.db.models import Count
import shutil

# Class MUST be named 'Command'
class Command(BaseCommand):

    # Displayed from 'manage.py help mycommand'
    help = "Import reports that are not in the database yet."

    # make_option requires options in optparse format
    option_list = BaseCommand.option_list + (
                        make_option('--input-dir', action='store',
                            dest='input-dir',
                            default="",
                            help='Directory containing crash reports'),
                        make_option('--output-dir', action='store',
                            dest='output-dir',
                            default="",
                            help='Output directory for generated reports and graphs'),
                  )

    def handle(self, *app_labels, **options):
        """
        app_labels - app labels (eg. myapp in "manage.py reset myapp")
        options - configurable command line options
        """

        # Return a success message to display to the user on success
        # or raise a CommandError as a failure condition
        if options['input-dir'] == "":
            raise CommandError('Please specify input-dir.')
        elif options['output-dir'] == "":
            raise CommandError('Please specify output-dir.')
        # input-dir and output-dir set, so parse stuff
        else:
            self.importReports(options['input-dir'], options['output-dir'])
            self.generateFlamegraphs(options['output-dir'])

    #
    def importReports(self, input_dir, output_dir):
        if not os.path.exists(input_dir) or not os.path.isdir(input_dir):
            raise CommandError("input-dir doesn't exist or is not a dir.")
        if not os.path.exists(output_dir) or not os.path.isdir(output_dir):
            raise CommandError("output-dir doesn't exist or is not a dir.")

        # make parsed directory for storing parsed reports
        parsed_dir = os.path.join(input_dir, "parsed")
        if not os.path.isdir(parsed_dir):
            try:
                os.mkdir(parsed_dir)
            except:
                print "Could not create parsed directory"

        # list all files in the input dir
        for infile in os.listdir(input_dir):
            infile_path = os.path.join(input_dir, infile)

            if not infile.startswith(u"exception"):
                continue
            if not os.path.isfile(infile_path):
                continue

            # generate stack trace reports
            print u"Processing %s..." % infile_path
            parser = ExceptionLogParser()
            parser.insert_data(infile_path, output_dir, True)
            # move parsed report to parsed directory so we don't try to parse it every time
            try:
                shutil.move(infile_path, os.path.join(parsed_dir, infile))
            except:
                print "Could not backup file: %s" % infile

        print "Success!"

    def generateFlamegraphs(self, output_dir):
        print "Generating flamegraphs..."
        creator = FlameGraphCreator()
        creator.create(output_dir, "date")
        creator.create(output_dir, "version")
        print "Done"


class ExceptionLogParser(object):

    def __init__(self):
        super(ExceptionLogParser, self).__init__()

        self._logger = logging.getLogger(self.__class__.__name__)
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        self._logger.addHandler(ch)

    def insert_data(self, pkg_path, report_dir, to_overwrite):
        """Parses a given package and creates a report out of it.
        """
        # ignore existing report
        # report_title = os.path.splitext(os.path.basename(pkg_path))[0]
        # report_filename = u"%s.html" % (report_title)
        # report_filepath = os.path.join(report_dir, report_filename)
        # flamegraph_filename = u"%s_fg.txt" % (report_title)
        # flamegraph_filepath = os.path.join(report_dir, flamegraph_filename)
        # trace = 0
        # if not to_overwrite and os.path.exists(report_filepath):
        #    return

        if pkg_path.endswith("bz2"):
            content = self.__parse_bz2pkg(pkg_path)
        else:
            with file(pkg_path) as f:
                content = f.read()

        if not content:
            return

        in_s = StringIO(content)

        # parse date
        date = pkg_path.replace("exception_", "").replace(".bz2", "")
        date = date[-8:]
        date = "%s-%s-%s" % (date[0:4], date[4:-2], date[6:])
        # aggregate_stacktraces = {}
        while True:
            try:
                xml_data_dict = self.__parse_data(in_s)
                if not xml_data_dict:
                    return
            except EOFError:
                break

            else:
                if CrashReport.objects.filter(timestamp=xml_data_dict[u"timestamp"]).exists():
                    continue
                if xml_data_dict[u"stack"] and xml_data_dict[u"stack"].startswith("Tribler version:"):
                    version = xml_data_dict[u"stack"].split('\n', 1)[0].replace("Tribler version: ", "")
                    stack = xml_data_dict[u"stack"].replace("Tribler version: %s\n" % version, "")
                else:
                    version = "x.x.x"
                    stack = xml_data_dict[u"stack"]

                os = ""
                machine = ""

                # sysinfo may be None
                if xml_data_dict[u"sysinfo"]:
                    details = re.findall('platform.details(.*?)\n', xml_data_dict[u"sysinfo"], re.S)
                    if details and len(details) > 0:
                        os = details[0].strip()

                    details = re.findall('platform.machine(.*?)\n', xml_data_dict[u"sysinfo"], re.S)
                    if details and len(details) > 0:
                        machine = details[0].strip()

                report = CrashReport(timestamp=xml_data_dict[u"timestamp"], sysinfo=xml_data_dict[u"sysinfo"],
                                     comments=xml_data_dict[u"comments"], stack=stack,
                                     version=version, date=date, os=os, machine=machine)
                report.save()

    def __parse_bz2pkg(self, pkg_path):
        """Parses a bzip2 packge of an exception report and returns a data
           dict if successful. None will be returned if not succesful.
        """
        bz2_file = None
        try:
            bz2_file = bz2.BZ2File(pkg_path, 'r')
            content = ""
            while True:
                line = bz2_file.readline()
                if not line:
                    break
                content += line
        except:
            self._logger.exception(u"Failed to extract bzip2 [%s]", pkg_path)
            return None
        finally:
            if bz2_file:
                bz2_file.close()

        return content

    def __parse_data(self, content_stream):
        """Creats a report out of a given content. It returns a dict for XML.
        """
        try:
            raw_data_dict = pickle.load(content_stream)
        except:
            return

        # get fields
        xml_data_dict = {}

        COMPULSORY_FIELDS = (u'sysinfo', u'comments', u'stack', u'remote_host', u'sysinfo')

        xml_data_dict[u'timestamp'] = raw_data_dict.get(u'timestamp', None)
        post = raw_data_dict.get(u'post', None)
        if post:
            for kw, val in post:
                if kw in COMPULSORY_FIELDS:
                    xml_data_dict[kw] = val

        # check compulsory fields
        for kw in COMPULSORY_FIELDS:
            if kw not in xml_data_dict:
                xml_data_dict[kw] = None
        return xml_data_dict


class FlameGraphCreator(object):
    def __init__(self):
        super(FlameGraphCreator, self).__init__()

        self._logger = logging.getLogger(self.__class__.__name__)
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        self._logger.addHandler(ch)

    def create(self, output_dir, fg_type):
        if fg_type not in ["date", "version"]:
            print "Unknown type for flamegraph generation"
            return
        for v in CrashReport.objects.values(fg_type).distinct():
            if fg_type is "date":
                v = v[fg_type].strftime("%Y-%m-%d")
            if fg_type is "version":
                v_dots = v[fg_type]
                v = v[fg_type].replace(".", "_")
            fg_path = os.path.join(os.path.abspath(output_dir), "fg_%s%s.txt" % (fg_type[0], v))
            # do not regenerate flamegraph if it exists
            if os.path.isfile(fg_path):
                continue
            fg = ""

            if fg_type is "date":
                records = CrashReport.objects.values('stack').filter(date=v).annotate(cnt=Count('stack'))

            if fg_type is "version":
                records = CrashReport.objects.values('stack').filter(version=v_dots).annotate(cnt=Count('stack'))

            for r in records:
                p = StacktraceParser()
                stack = unicode(r['stack']).replace('\n', ';')
                parsedstack = p.parse(stack, ';')
                fg += "%s %d\n" % (parsedstack, r['cnt'])
            self.writeFlamegraph(fg_path, fg)
            self.generateSvg(fg_path)

    def writeFlamegraph(self, filepath, fg):
        outfile = None
        try:
            outfile = codecs.open(filepath, 'wb', 'utf-8')
            outfile.write(fg)
        except:
            self._logger.exception(u"Failed to write to flamegraph file [%s]", filepath)
        finally:
            if outfile:
                outfile.close()

    def generateSvg(self, input_file):
        output_file = input_file.replace(".txt", ".svg")
        cmd = "/bin/cat %s | %s/flamegraph.pl > %s" % (input_file, settings.FLAMEGRAPH_PATH, output_file)
        subprocess.call([cmd], shell=True)


class StacktraceParser(object):
    def __init__(self):
        super(StacktraceParser, self).__init__()

        self._logger = logging.getLogger(self.__class__.__name__)

    def parse(self, stacktrace, sep):
        lines = stacktrace.split(sep)
        p = re.compile(r'File \"(.*)\", line (.*), in (.*)', re.M)
        result = ""
        for l in lines:
            match = re.search(p, l)
            if not match:
                continue
            stack_file = match.group(1)
            stack_line = match.group(2)
            function = match.group(3)
            if result is not "":
                result = "%s;%s:%s" % (result, stack_file, function)
            else:
                result = "%s:%s" % (stack_file, function)
        return result
