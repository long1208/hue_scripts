import os
import sys
import logging
import datetime
import time
import subprocess

from cm_environment import check_security
from hue_shared import which

#logging.basicConfig()
#logging = logging.getLogger(__name__)

class Curl(object):

  def __init__(self, verbose=False):
    self.curl = which('curl')
    if self.curl is None:
      logging.exception("curl is required, please install and rerun")
      sys.exit(1)

    self.cmd = self.curl
    logging.info("Checking security status")
    self.security_enabled = check_security()
    self.verbose = verbose

    if self.security_enabled:
      self.cmf = self.cmd + '--negotiate -u :'

    if self.verbose:
      self.cmd = self.cmd + '-v'

  def do_curl(self, url, method='GET', follow=False, args=None):

    self.cmd = self.cmd + ' -X ' + method
    if follow:
      self.cmd = self.cmd + ' -L'

    if args is not None:
      self.cmd = self.cmd + ' ' + args

    self.cmd = self.cmd + ' \'' + url + '\''
    logging.info("cmd: %s" % self.cmd)
    curl_result = subprocess.Popen(self.cmd, shell=True, stdout=subprocess.PIPE)
    logging.info("curl result: %s" % curl_result)
    return curl_result.communicate()[0]


  def do_curl_available_services(self, service_test):
    url = service_test['url']
    method = service_test['method']
    response = self.do_curl(url, method='GET')
