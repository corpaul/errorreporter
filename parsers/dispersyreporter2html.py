#!/usr/bin/env python
"""Create HTML reports from exception bzip2 archives.

Usage:
    -i, --input-dir=  :  Input directory.
    -o, --output-dir= :  Output directory.
    -f, --force       :  To overwrite the HTML report if exists.
"""
import codecs
import bz2
import pickle
import os
import sys
import getopt
import logging
from StringIO import StringIO
import hashlib
import operator
import re


class ExceptionLogParser(object):

    def __init__(self):
        super(ExceptionLogParser, self).__init__()

        self._logger = logging.getLogger(self.__class__.__name__)
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        self._logger.addHandler(ch)

    def process_report(self, pkg_path, report_dir, to_overwrite):
        """Parses a given package and creates a report out of it.
        """
        # ignore existing report
        report_title = os.path.splitext(os.path.basename(pkg_path))[0]
        report_filename = u"%s.html" % (report_title)
        report_filepath = os.path.join(report_dir, report_filename)
        flamegraph_filename = u"%s_fg.txt" % (report_title)
        flamegraph_filepath = os.path.join(report_dir, flamegraph_filename)
        trace = 0
        if not to_overwrite and os.path.exists(report_filepath):
            return

        content = self.__parse_bz2pkg(pkg_path)
        if not content:
            return

        in_s = StringIO(content)

        stacktraces = []
        aggregate_stacktraces = {}
        while True:
            try:
                xml_data_dict = self.__create_report(in_s)
                if not xml_data_dict:
                    return
            except EOFError:
                break
            else:
                xml_data_dict[u'id'] = trace
                trace = trace + 1
                stacktraces.append(xml_data_dict)
                m = hashlib.md5()
                if xml_data_dict.get(u'stack') is None:
                    continue
                m.update(xml_data_dict.get(u'stack'))
                digest = m.digest()
                if digest in aggregate_stacktraces:
                    aggregate_stacktraces[digest].addStacktrace(xml_data_dict)
                else:
                    aggregate_stacktraces[digest] = AggregateStacktrace(xml_data_dict)

        # init html report
        creator = StacktraceReportCreator()
        creator.create(report_title, report_filepath, to_overwrite, stacktraces, aggregate_stacktraces)

        creator.appendAggregate(aggregate_stacktraces, flamegraph_filepath)
        creator.appendAggregateToFlamegraph(aggregate_stacktraces)
        for i in range(0, len(stacktraces)):
            creator.appendStack(stacktraces[i])

        creator.write(report_filepath)
        creator.writeFlamegraph(flamegraph_filepath)

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

    def __create_report(self, content_stream):
        """Creats a report out of a given content. It returns a dict for XML.
        """
        # try:
        raw_data_dict = pickle.load(content_stream)
        # except:
        #    self._logger.exception(u"Failed to load pickle content [%s]", content_stream)
        #    raise EOFError

        # get fields
        xml_data_dict = {}

        COMPULSORY_FIELDS = (u'sysinfo', u'comments', u'stack', u'remote_host')

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


class AggregateStacktrace(object):
    def __init__(self, stacktrace):
        super(AggregateStacktrace, self).__init__()
        self._stacktrace = stacktrace.get(u'stack')
        self.count = 1
        self.comments = {}
        self.comments[stacktrace.get(u'id')] = (stacktrace.get(u'comments'))

    def addStacktrace(self, stacktrace):
        self.comments[stacktrace.get(u'id')] = (stacktrace.get(u'comments'))
        self.count = self.count + 1


class StacktraceReportCreator(object):

    def __init__(self):
        super(StacktraceReportCreator, self).__init__()

        self._logger = logging.getLogger(self.__class__.__name__)
        self.title = ""
        self.html_content = ""
        self.flamegraph_content = ""

    def create(self, title, filepath, to_overwrite, stacktraces, aggregates):
        """Creates an HTML stack trace report from a given data dict.
        """
        if os.path.exists(filepath) and not to_overwrite:
            return
        self.title = u"Report-%s" % title

        self.html_content = u"<html>\n"

        self.html_content += u"<head>\n"
        self.html_content += u"  <title>Report overview for %s</title>\n" % title
        self.html_content += u"</head>\n"
        self.html_content += u"<body>\n"
        self.html_content += u"<h1>Overview report</h1>"
        self.html_content += u"Total # of reports: %s<br>\n" % len(stacktraces)
        self.html_content += u"Total # of different stacks: %s" % len(aggregates)

    def appendAggregate(self, aggregates, flamegraph):
        flamegraph = os.path.basename(flamegraph.replace("txt", "svg"))
        self.html_content += u"<object data=\"%s\" type=\"image/svg+xml\" id=\"version1\" width=\"1000px\">" \
                              " </object>\n" % flamegraph
        self.html_content += u"  <h1>Aggregate stacks</h1>\n"
        # for aggr in aggregates.values():
        for aggr in (sorted(aggregates.values(), key=operator.attrgetter('count'), reverse=True)):
            self.html_content += u"  <table border=\"1\" style=\"width: 1000px; margin-bottom: 20px;\">\n"
            self.html_content += u"  <tr>\n"
            self.html_content += u"    <th>Aggregate stacktrace (# of reports: %d)</th>\n" % aggr.count
            self.html_content += u"  </tr><tr>\n"
            stack = unicode(aggr._stacktrace).replace('\n', '<br/>')
            self.html_content += u"    <td>%s</td>\n" % stack
            self.html_content += u"</tr><tr>\n"
            self.html_content += u"    <th>Comments:</th>\n</tr><tr>\n<td>"
            comments_not_provided = ""
            for i, c in aggr.comments.iteritems():
                if c != "Not provided":
                    self.html_content += u"    %s (<a href=\"#%s\">#%s</a>)\n<br>----<br>" % (c, i, i)
                else:
                    comments_not_provided += u"<a href=\"#%s\">#%s</a>, " % (i, i)
            if comments_not_provided != "":
                self.html_content += u" Not provided (%s)\n<br>" % comments_not_provided[:-2]
            self.html_content += u"</td></tr>"
            self.html_content += u"  </table>\n"

    def appendAggregateToFlamegraph(self, aggregates):
        for aggr in (sorted(aggregates.values(), key=operator.attrgetter('count'), reverse=True)):
            p = StacktraceParser()
            stack = unicode(aggr._stacktrace).replace('\n', ';')
            parsedstack = p.parse(stack, ';')
            self.flamegraph_content += "%s %d\n" % (parsedstack, aggr.count)

    def appendStack(self, data_dict):
        self.html_content += u"  <h1><a name=\"%s\">Stack #%s</a></h1>\n" % (data_dict[u'id'], data_dict[u'id'])
        self.html_content += u"  <table border=\"1\" style=\"width: 1000px; margin-bottom: 20px;\">\n"
        for kw, val in data_dict.iteritems():
            if kw in (u"sysinfo",):
                continue
            self.html_content += u"  <tr>\n"
            self.html_content += u"    <th>%s</th>\n" % kw
            content = unicode(val).replace('\n', '<br/>')
            self.html_content += u"    <td>%s</td>\n" % content
            self.html_content += u"  </tr>\n"
        self.html_content += u"  </table>\n"

    def write(self, filepath):
        outfile = None
        try:
            outfile = codecs.open(filepath, 'wb', 'utf-8')
            self.html_content += u"</body>\n"

            self.html_content += u"</html>\n"
            outfile.write(self.html_content)
        except:
            self._logger.exception(u"Failed to write to file [%s]", filepath)
        finally:
            if outfile:
                outfile.close()

    def writeFlamegraph(self, filepath):
        outfile = None
        try:
            outfile = codecs.open(filepath, 'wb', 'utf-8')
            outfile.write(self.flamegraph_content)
        except:
            self._logger.exception(u"Failed to write to flamegraph file [%s]", filepath)
        finally:
            if outfile:
                outfile.close()


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


class HTMLReportCreator(object):

    def __init__(self):
        super(HTMLReportCreator, self).__init__()

        self._logger = logging.getLogger(self.__class__.__name__)
        self.html_content = ""
        
    def create(self, input_dir):
        self.title = u"Overview of received crash reports"

        self.html_content = u"<html>\n"

        self.html_content += u"<head>\n"
        self.html_content += u"  <title>Overview of received crash reports</title>\n"
        self.html_content += u" <script src=\"http://ajax.googleapis.com/ajax/libs/jquery/1.11.1/jquery.min.js\"></script>"
        #self.html_content += u"<script type=\"text/javascript\">$(\"#reports\").change(function(){ var url = \"signature.php?sign=\"+$(this).val(); alert(url);" \
        #                       "$(\"iframe\").attr(\"src\",url); });</script>" 
        self.html_content += u"<script type=\"text/javascript\">$(document).ready(function(){ $(\"select\").change(function(){ var url = $(this).val(); $(\"iframe\").attr(\"src\",url); }) });</script>"
        self.html_content += u"</head>\n"
        self.html_content += u"<body>\n"
        self.html_content += u"<h1>Overview of received crash reports</h1>"

        self.html_content += u"<select id=\"reports\">"
        for infile in sorted(os.listdir(input_dir)):
            if infile.endswith(u"html") and not infile.startswith(u"crashreports.html"):
                self.html_content += u"<option value=\"%s\">%s</option>" % (infile, infile)
        self.html_content += u"</select><br><br>"
        
    def write(self, filepath):
        outfile = None
        try:
            outfile = codecs.open(filepath, 'wb', 'utf-8')
            self.html_content += u"<iframe style=\"width: 1100px; height: 800px;\"></iframe>"
            self.html_content += u"</body>\n"

            self.html_content += u"</html>\n"
            outfile.write(self.html_content)
        except:
            self._logger.exception(u"Failed to write to file [%s]", filepath)
        finally:
            if outfile:
                outfile.close()

if __name__ == '__main__':
    optlist, args = getopt.getopt(sys.argv[1:], 'i:o:f',
        ['--input-dir=', '--output-dir=', '--force'])

    input_dir = None
    output_dir = None
    to_overwrite = False
    for opt, val in optlist:
        if opt in ('-i', '--input-dir='):
            input_dir = val
        elif opt in ('-o', '--output-dir='):
            output_dir = val
        elif opt in ('-f', '--force'):
            to_overwrite = True

    if not input_dir or not output_dir:
        print u"input-dir or output-dir unspecified."
        sys.exit()

    if not os.path.exists(input_dir) or not os.path.isdir(input_dir):
        print u"input-dir doesn't exist or is not a dir."
        sys.exit()
    if not os.path.exists(output_dir) or not os.path.isdir(output_dir):
        print u"output-dir doesn't exist or is not a dir."
        sys.exit()

    # list all files in the input dir
    for infile in os.listdir(input_dir):
        infile_path = os.path.join(input_dir, infile)

        if not infile.startswith(u"exception"):
            print u"Skip %s, not an exception report..." % infile_path
            continue
        if not infile.endswith(u"bz2"):
            print u"Skip %s, not an bz2 file (empty?)..." % infile_path
            continue
        if not os.path.isfile(infile_path):
            print u"Skip %s, not a file..." % infile_path
            continue

        # generate stack trace reports
        print u"Processing %s..." % infile_path
        parser = ExceptionLogParser()
        parser.process_report(infile_path, output_dir, to_overwrite)


    print u"Generating crashreports.html..."
    # generate html report combining the stack traces
    creator = HTMLReportCreator()
    creator.create(output_dir)
    report_filepath = os.path.join(output_dir, u"crashreports.html")
    creator.write(report_filepath)    

    print u"Done."
