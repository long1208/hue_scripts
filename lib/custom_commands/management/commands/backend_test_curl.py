#!/usr/bin/env python
import os
import sys
import logging
import datetime
import time

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext_lazy as _t, ugettext as _

import desktop.conf
from desktop.conf import TIME_ZONE
from search.conf import SOLR_URL, SECURITY_ENABLED as SOLR_SECURITY_ENABLED
from liboozie.conf import OOZIE_URL, SECURITY_ENABLED as OOZIE_SECURITY_ENABLED
from hadoop import conf as hdfs_conf
from hadoop import cluster

from hue_curl import Curl

def get_service_info(service):
  service_info = {}
  if service.lower() == 'solr':
    service_info['url'] = SOLR_URL.get()
    service_info['security_enabled'] = SOLR_SECURITY_ENABLED.get()
  if service.lower() == 'oozie':
    service_info['url'] = OOZIE_URL.get()
    service_info['security_enabled'] = OOZIE_SECURITY_ENABLED.get()
  if service.lower() == 'httpfs':
    hdfs_config = hdfs_conf.HDFS_CLUSTERS['default']
    service_info['url'] = hdfs_config.WEBHDFS_URL.get()
    service_info['security_enabled'] = hdfs_config.SECURITY_ENABLED.get()
  if service.lower() == 'rm':
    yarn_cluster = cluster.get_cluster_conf_for_job_submission()
    service_info['url'] = yarn_cluster.RESOURCE_MANAGER_API_URL.get()
    service_info['security_enabled'] = yarn_cluster.SECURITY_ENABLED.get()

#REFERNCE
#  history_server_api_url
#  spark_history_server_url
#  spark_history_server_security_enabled

  if 'url' not in service_info:
    logging.info("Hue does not have %s configured, cannot test %s" % (service, service))
  elif service_info['url'] is None:
    logging.info("Hue does not have %s configured, cannot test %s" % (service, service))

  return service_info


def add_service_test(available_services, options=None, service_name=None, testname=None, suburl=None, method='GET', teststring=None):
  if options['service'] == "all" or options['service'] == service_name.lower():
    if not service_name in available_services:
      service_info = get_service_info(service_name)
      url = service_info['url']
      security_enabled = service_info['security_enabled']
      available_services[service_name] = {}
      available_services[service_name]['url'] = url
      available_services[service_name]['security_enabled'] = security_enabled
    # Tests
    if not 'tests' in available_services[service_name]:
      available_services[service_name]['tests'] = {}
    if not testname in available_services[service_name]['tests']:
      available_services[service_name]['tests'][testname] = {}
      available_services[service_name]['tests'][testname]['url'] = '%s/%s' % (available_services[service_name]['url'], suburl)
      available_services[service_name]['tests'][testname]['method'] = method
      available_services[service_name]['tests'][testname]['test'] = teststring


class Command(BaseCommand):
  """
  Handler for renaming duplicate User objects
  """

  try:
    from optparse import make_option
    option_list = BaseCommand.option_list + (
      make_option("--service", help=_t("Service to test, all, httpfs, solr, oozie, rm, jhs, sparkhs."),
                  action="store", default='all', dest='service'),
      make_option("--showcurl", help=_t("Show curl commands."),
                  action="store_true", default=False, dest='showcurl'),
      make_option("--response", help=_t("Show entire REST response."),
                  action="store_true", default=False, dest='entireresponse'),
      make_option("--username", help=_t("User to doAs."),
                  action="store", default="admin", dest='username'),
      make_option("--verbose", help=_t("Verbose."),
                  action="store_true", default=False, dest='verbose'),
    )

  except AttributeError, e:
    baseoption_test = 'BaseCommand' in str(e) and 'option_list' in str(e)
    if baseoption_test:
      def add_arguments(self, parser):
        parser.add_argument("--service", help=_t("Service to test, all, httpfs, solr, oozie, rm, jhs, sparkhs."),
                    action="store", default='all', dest='service'),
        parser.add_argument("--showcurl", help=_t("Show curl commands."),
                    action="store_true", default=False, dest='showcurl'),
        parser.add_argument("--response", help=_t("Show entire REST response."),
                    action="store_true", default=False, dest='entireresponse'),
        parser.add_argument("--username", help=_t("User to doAs."),
                    action="store", default="admin", dest='username'),
        parser.add_argument("--verbose", help=_t("Verbose."),
                    action="store_true", default=False, dest='verbose')
    else:
      logging.exception(str(e))
      sys.exit(1)

  def handle(self, *args, **options):

    curl = Curl(verbose=options['verbose'])

    available_services = {}

    #Add Solr
    add_service_test(available_services, options=options, service_name="Solr", testname="JMX",
                     suburl='jmx', method='GET', teststring='solr.solrxml.location')

    #Add Oozie
    add_service_test(available_services, options=options, service_name="Oozie", testname="STATUS",
                     suburl='v1/admin/status?timezone=%s&user.name=hue&doAs=%s' % (TIME_ZONE.get(), options['username']), teststring='{"systemMode":"NORMAL"}')

    #Add HTTPFS
    add_service_test(available_services, options=options, service_name="Httpfs", testname="USERHOME",
                     suburl='user/%s?op=GETFILESTATUS&user.name=hue&doas=%s' % (options['username'], options['username']), method='GET', teststring='"type":"DIRECTORY"')

    #Add RM
    add_service_test(available_services, options=options, service_name="RM", testname="CLUSTERINFO",
                     suburl='ws/v1/cluster/info', method='GET', teststring='"clusterInfo"')

    for service in available_services:
      for service_test in available_services[service]['tests']:
        logging.info("Running %s %s Test:" % (service, service_test))
        response = curl.do_curl_available_services(available_services[service]['tests'][service_test])
        logging.info("entireresponse: %s" % options['entireresponse'])
        if available_services[service]['tests'][service_test]['test'] in response:
          logging.info("%s %s Test Passed: %s found in response" % (service, service_test, available_services[service]['tests'][service_test]['test']))
        if options['entireresponse']:
          logging.info("%s %s Test Response: %s" % (service, service_test, response))




