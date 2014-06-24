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


class ExceptionLogParser(object):

    def __init__(self):
        super(ExceptionLogParser, self).__init__()

        self._logger = logging.getLogger(self.__class__.__name__)

    def process_report(self, pkg_path, report_dir, to_overwrite):
        """Parses a given package and creates a report out of it.
        """
        # ignore existing report
        report_title = os.path.splitext(os.path.basename(pkg_path))[0]
        report_filename = report_title + u".html"
        report_filepath = os.path.join(report_dir, report_filename)

        if not to_overwrite and os.path.exists(report_filepath):
            return
        content = self.__parse_bz2pkg(pkg_path)
        if not content:
            return

        xml_data_dict = self.__create_report(content)
        if not xml_data_dict:
            return

        creator = HTMLReportCreator()
        creator.create(report_title, xml_data_dict, report_filepath, to_overwrite)

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

    def __create_report(self, content):
        """Creats a report out of a given content. It returns a dict for XML.
        """
        try:
            raw_data_dict = pickle.loads(content)
        except:
            self._logger.exception(u"Failed to load pickle content [%s]", content)
            return

        # get fields
        xml_data_dict = {}

        COPMULSORY_FIELDS = (u'sysinfo', u'comments', u'stack')

        xml_data_dict[u'timestamp'] = raw_data_dict.get(u'timestamp', None)
        post = raw_data_dict.get(u'post', None)
        if post:
            for kw, val in post:
                if kw in COPMULSORY_FIELDS:
                    xml_data_dict[kw] = val

        # check compulsory fields
        for kw in COPMULSORY_FIELDS:
            if kw not in xml_data_dict:
                xml_data_dict[kw] = None

        return xml_data_dict


class HTMLReportCreator(object):

    def __init__(self):
        super(HTMLReportCreator, self).__init__()

        self._logger = logging.getLogger(self.__class__.__name__)

    def create(self, title, data_dict, filepath, to_overwrite):
        """Creates an HTML report from a give data dict.
        """
        if os.path.exists(filepath) and not to_overwrite:
            return

        title = u"Report-%s" % title

        html_content = u"<html>\n"

        html_content += u"<head>\n"
        html_content += u"  <title>%s</title>\n" % title
        html_content += u"</head>\n"

        html_content += u"<body>\n"
        html_content += u"  <h1>%s</h1>\n" % title
        html_content += u"  <table border=\"1\">\n"
        for kw, val in data_dict.iteritems():
            if kw in (u"sysinfo", ):
                continue
            html_content += u"  <tr>\n"
            html_content += u"    <th>%s</th>\n" % kw
            content = unicode(val).replace('\n', '<br/>')
            html_content += u"    <td>%s</td>\n" % content
            html_content += u"  </tr>\n"
        html_content += u"  </table>\n"
        html_content += u"</body>\n"

        html_content += u"</html>\n"

        outfile = None
        try:
            outfile = codecs.open(filepath, 'wb', 'utf-8')
            outfile.write(html_content)
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

        if not os.path.isfile(infile_path):
            print u"Skip %s, not a file..." % infile_path
            continue

        print u"Processing %s..." % infile_path
        parser = ExceptionLogParser()
        parser.process_report(infile_path, output_dir, to_overwrite)

    print u"Done."

