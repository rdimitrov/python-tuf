"""
<Program Name>
  updater.py

<Author>
  Pankhuri Goyal <pankhurigoyal02@gmail.com>

<Started>
  June 2014.

<Copyright>
	See LICENSE for licensing information.

<Purpose>
	Interposition is the high-level integration of TUF. 'updater.py' is used to
  perform high-level integration of TUF to the software updater. This means 
  that all the processes which are taking place in the low-level integration 
  will be done automatically. This layer of processes will be transparent to 
  the client.
  Updater.py have two classes named as Updater and UpdaterController.
  #TODO: Add more description to purpose.
  #TODO: Add Pros and Cons of using interposition.

<Example Interpostion>

  To implement interpostion client only need to have two files -
  1. A python file which client will have to run in order to perform 
     interposition. For example - interposition.py.

     # First import the main module called interposition which contains all 
     # the required directories and classes.
     import tuf.interposition              
    
     # urllib_tuf and urllib2_tuf are TUF's copy of urllib and urllib2
     from tuf.interposition import urllib_tuf as urllib
     from tuf.interposition import urllib2_tuf as urllib2
     
     # From tuf.interposition, configure() method is called.
     # configure() is within __init__.py
     # Ways to call this method are as follows :
     # First, configure() - By default, the configuration object is expected 
     # to be situated in the current working directory in the file with the 
     # name "tuf.interposition.json".
     # Second, configure(filename="/path/to/json")
     # Configure() returns a dictionary of configurations
     configurations = tuf.interposition.configure()

     url = 'http://example.com/path/to/document'
     # This is the standard way of opening and retrieving url in python.
     urllib.urlopen(url)
     urllib.urlretrieve(url)
     urllib2.urlopen(url)

     # Remove TUF interposition for previously read configurations. That is 
     # remove the updater object.
     tuf.interposition.deconfigure(configurations)


  2. A JSON object which tells tuf.interposition which URLs to intercept, how 
     to transform them (if necessary), and where to forward them (possibly over
     SSL) for secure responses via TUF. By default, the name of the file is 
     tuf.interposition.json which is as follows -
    
     # configurations are simply a JSON object which allows you to answer 
     # these questions -
     # - Which network location get intercepted?
     # - Given a network location, which TUF mirrors should we forward 
     #   requests to?
     # - Given a network location, which paths should be intercepted?
     # - Given a TUF mirror, how do we verify its SSL certificate?
     {
     # This is required root object.
       "configurations": {
       # Which network location should be intercepted?
       # Network locations may be specified as "hostname" or "hostname:port".
         "seattle.poly.edu": {
         # Where do we find the client copy of the TUF server metadata?
           "repository_directory": ".",
           # Where do we forward the requests to seattle.poly.edu?
             "repository_mirrors" : {
                "mirror1": {
                # In this case, we forward them to http://tuf.seattle.poly.edu
                  "url_prefix": "http://localhost:8001",
                  # You do not have to worry about these default parameters.
                  "metadata_path": "metadata",
                  "targets_path": "targets",
                  "confined_target_dirs": [ "" ]
             }
           }
         }
       }
     }

  # After making these two files on the client side, run interposition.py. This
  # will start the interposition process. It generates a log file in the same 
  # directory which can be used for a review.

"""

import mimetypes
import os.path
import re
import shutil
import tempfile
import urllib
import urlparse


import tuf.client.updater
import tuf.conf


# We import them directly into our namespace so that there is no name conflict.
from configuration import Configuration, InvalidConfiguration
from utility import Logger, InterpositionException
#TODO: Remove utility because the Logger is it two places. 




################################ GLOBAL CLASSES ################################


#TODO: Put this class in the Exception file of TUF.
class URLMatchesNoPattern(InterpositionException):
  """URL matches no user-specified regular expression pattern."""
  pass





class Updater(object):
  """I am an Updater model."""


  def __init__(self, configuration):
    CREATED_TEMPDIR_MESSAGE = "Created temporary directory at {tempdir}"

    self.configuration = configuration
    # A temporary directory used for this updater over runtime.
    self.tempdir = tempfile.mkdtemp()
    Logger.debug(CREATED_TEMPDIR_MESSAGE.format(tempdir=self.tempdir))

    # must switch context before instantiating updater
    # because updater depends on some module (tuf.conf) variables
    self.switch_context()
    self.updater = tuf.client.updater.Updater(self.configuration.hostname,
                                              self.configuration.repository_mirrors)
    
    # Update the client's top-level metadata.  The download_target() method does
    # not automatically refresh top-level prior to retrieving target files and
    # their associated Targets metadata, so update the top-level
    # metadata here.
    Logger.info('Refreshing top-level metadata for interposed '+repr(configuration))
    self.updater.refresh()
  
 
  def refresh(self):
    """Refresh top-level metadata"""
    self.updater.refresh()


  def cleanup(self):
    """Clean up after certain side effects, such as temporary directories."""

    DELETED_TEMPDIR_MESSAGE = "Deleted temporary directory at {tempdir}"
    shutil.rmtree(self.tempdir)
    Logger.debug(DELETED_TEMPDIR_MESSAGE.format(tempdir=self.tempdir))


  def download_target(self, target_filepath):
    """Downloads target with TUF as a side effect."""

    # download file into a temporary directory shared over runtime
    destination_directory = self.tempdir
    
    # Note: join() discards 'destination_directory' if 'target_filepath'
    # contains a leading path separator (i.e., is treated as an absolute path).
    filename = os.path.join(destination_directory, target_filepath.lstrip(os.sep))
    
    # Switch TUF context.
    self.switch_context()
    
    # Locate the fileinfo of 'target_filepath'.  updater.target() searches
    # Targets metadata in order of trust, according to the currently trusted
    # snapshot.  To prevent consecutive target file requests from referring to
    # different snapshots, top-level metadata is not automatically refreshed.
    targets = [self.updater.target(target_filepath)]

    # TODO: targets are always updated if destination directory is new, right?
    updated_targets = self.updater.updated_targets(targets, destination_directory)

    for updated_target in updated_targets:
      self.updater.download_target(updated_target, destination_directory)

    return destination_directory, filename


  # TODO: decide prudent course of action in case of failure
  def get_target_filepath(self, source_url):
    # Locate the fileinfo of 'target_filepath'.  updater.target() searches
    # Targets metadata in order of trust, according to the currently trusted
    # snapshot.  To prevent consecutive target file requests from referring to
    # different snapshots, top-level metadata is not automatically refreshed.
    targets = [self.updater.target(target_filepath)]

    # TODO: targets are always updated if destination directory is new, right?
    updated_targets = self.updater.updated_targets(targets, destination_directory)

    for updated_target in updated_targets:
      self.updater.download_target(updated_target, destination_directory)

    return destination_directory, filename


  # TODO: decide prudent course of action in case of failure
  def get_target_filepath(self, source_url):
    """Given source->target map, figure out what TUF *should* download given a
    URL."""

    WARNING_MESSAGE = "Possibly invalid target_paths for " + \
        "{network_location}! No TUF interposition for {url}"

    parsed_source_url = urlparse.urlparse(source_url)
    target_filepath = None

    try:
      # Does this source URL match any regular expression which tells us
      # how to map the source URL to a target URL understood by TUF?
      for target_path in self.configuration.target_paths:

        # target_path: { "regex_with_groups", "target_with_group_captures" }
        # e.g. { ".*(/some/directory)/$", "{0}/index.html" }
        source_path_pattern, target_path_pattern = target_path.items()[0]
        source_path_match = re.match(source_path_pattern, parsed_source_url.path)

        # TODO: A failure in string formatting is *critical*.
        if source_path_match is not None:
          target_filepath = target_path_pattern.format(*source_path_match.groups())

          # If there is more than one regular expression which
          # matches source_url, we resolve ambiguity by order of
          # appearance.
          break

      # If source_url does not match any regular expression...
      if target_filepath is None:
        # ...then we raise a predictable exception.
        raise URLMatchesNoPattern(source_url)

    except:
      Logger.exception(WARNING_MESSAGE.format(
        network_location=self.configuration.network_location, url=source_url))
      raise

    else:
      return target_filepath


  # TODO: distinguish between urllib and urllib2 contracts
  def open(self, url, data=None):
    filename, headers = self.retrieve(url, data=data)

    # TUF should always open files in binary mode and remain transparent to the
    # software updater.  Opening files in text mode slightly alters the
    # end-of-line characters and prevents binary files from properly loading on
    # Windows.
    # http://docs.python.org/2/tutorial/inputoutput.html#reading-and-writing-files
    # TODO: like tempfile, ensure file is deleted when closed?
    # open() in the line below is a predefined function in python.
    temporary_file = open(filename, 'rb')

    #TODO: addinfourl is not in urllib package anymore. We need to check if
    # other option for this is working or not.
    # Extend temporary_file with info(), getcode(), geturl()
    # http://docs.python.org/2/library/urllib.html#urllib.urlopen
    response = urllib.addinfourl(temporary_file, headers, url, code=200)

    return response


  # TODO: distinguish between urllib and urllib2 contracts
  def retrieve(self, url, filename=None, reporthook=None, data=None):
    INTERPOSITION_MESSAGE = "Interposing for {url}"

    Logger.info(INTERPOSITION_MESSAGE.format(url=url))

    # What is the actual target to download given the URL? Sometimes we would
    # like to transform the given URL to the intended target; e.g. "/simple/"
    # => "/simple/index.html".
    target_filepath = self.get_target_filepath(url)

    # TODO: Set valid headers fetched from the actual download.
    # NOTE: Important to guess the mime type from the target_filepath, not the
    # unmodified URL.
    content_type, content_encoding = mimetypes.guess_type(target_filepath)
    headers = {
      # NOTE: pip refers to this same header in at least these two duplicate
      # ways.
      "content-type": content_type,
      "Content-Type": content_type,
    }

    # Download the target filepath determined by the original URL.
    temporary_directory, temporary_filename = self.download_target(target_filepath)

    if filename is None:
        # If no filename is given, use the temporary file.
        filename = temporary_filename
    else:
        # Otherwise, copy TUF-downloaded file in its own directory
        # to the location user specified.
        shutil.copy2(temporary_filename, filename)

    return filename, headers


  # TODO: thread-safety, perhaps with a context manager
  def switch_context(self):
      # Set the local repository directory containing the metadata files.
      tuf.conf.repository_directory = self.configuration.repository_directory

      # Set the local SSL certificates PEM file.
      tuf.conf.ssl_certificates = self.configuration.ssl_certificates





class UpdaterController(object):
  """
  I am a controller of Updaters; given a Configuration, I will build and
  store an Updater which you can get and use later.
  """

  def __init__(self):
    # A private map of Updaters (network_location: str -> updater: Updater)
    self.__updaters = {}

    # A private set of repository mirror hostnames
    self.__repository_mirror_hostnames = set()


  def __check_configuration_on_add(self, configuration):
    """
    If the given Configuration is invalid, I raise an exception.
    Otherwise, I return some information about the Configuration,
    such as repository mirror hostnames.
    """

    INVALID_REPOSITORY_MIRROR = "Invalid repository mirror {repository_mirror}!"

    # Updater has a "global" view of configurations, so it performs
    # additional checks after Configuration's own local checks.
    assert isinstance(configuration, Configuration)

    # Restrict each (incoming, outgoing) hostname pair to be unique across
    # configurations; this prevents interposition cycles, amongst other
    # things.
    # GOOD: A -> { A:X, A:Y, B, ... }, C -> { D }, ...
    # BAD: A -> { B }, B -> { C }, C -> { A }, ...
    assert configuration.hostname not in self.__updaters
    assert configuration.hostname not in self.__repository_mirror_hostnames

    # Check for redundancy in server repository mirrors.
    repository_mirror_hostnames = configuration.get_repository_mirror_hostnames()

    for mirror_hostname in repository_mirror_hostnames:
      try:
        # Restrict each hostname in every (incoming, outgoing) pair to be
        # unique across configurations; this prevents interposition cycles,
        # amongst other things.
        assert mirror_hostname not in self.__updaters
        assert mirror_hostname not in self.__repository_mirror_hostnames

      except:
        error_message = \
          INVALID_REPOSITORY_MIRROR.format(repository_mirror=mirror_hostname)
        Logger.exception(error_message)
        raise InvalidConfiguration(error_message)

    return repository_mirror_hostnames



  def add(self, configuration):
    """Add an Updater based on the given Configuration."""

    repository_mirror_hostnames = self.__check_configuration_on_add(configuration)
    
    # If all is well, build and store an Updater, and remember hostnames.
    Logger.info('Adding updater for interposed '+repr(configuration))
    self.__updaters[configuration.hostname] = Updater(configuration)
    self.__repository_mirror_hostnames.update(repository_mirror_hostnames)
  
  
  
  def refresh(self, configuration):
    """Refresh the top-level metadata of the given Configuration."""

    assert isinstance(configuration, Configuration)

    repository_mirror_hostnames = configuration.get_repository_mirror_hostnames()

    assert configuration.hostname in self.__updaters
    assert repository_mirror_hostnames.issubset(self.__repository_mirror_hostnames)

    # Get the updater and refresh its top-level metadata.  In the majority of
    # integrations, a software updater integrating TUF with interposition will
    # usually only require an initial refresh() (i.e., when configure() is
    # called).  A series of target file requests may then occur, which are all
    # referenced by the latest top-level metadata updated by configure().
    # Although interposition was designed to remain transparent, for software
    # updaters that require an explicit refresh of top-level metadata, this
    # method is provided.
    Logger.info('Refreshing top-level metadata for '+ repr(configuration))
    updater = self.__updaters.get(configuration.hostname)
    updater.refresh()



  def get(self, url):
    """Get an Updater, if any, for this URL.

    Assumptions:
      - @url is a string."""

    GENERIC_WARNING_MESSAGE = "No updater or interposition for url={url}"
    DIFFERENT_NETLOC_MESSAGE = "We have an updater for netloc={netloc1} but not for netlocs={netloc2}"
    HOSTNAME_FOUND_MESSAGE = "Found updater for interposed network location: {netloc}"
    HOSTNAME_NOT_FOUND_MESSAGE = "No updater for hostname={hostname}"

    updater = None

    try:
      parsed_url = urlparse.urlparse(url)
      hostname = parsed_url.hostname
      port = parsed_url.port or 80
      netloc = parsed_url.netloc
      network_location = "{hostname}:{port}".format(hostname=hostname, port=port)

      # Sometimes parsed_url.netloc does not have a port (e.g. 80),
      # so we do a double check.
      network_locations = set((netloc, network_location))

      updater = self.__updaters.get(hostname)

      if updater is None:
        Logger.warn(HOSTNAME_NOT_FOUND_MESSAGE.format(hostname=hostname))

      else:

        # Ensure that the updater is meant for this (hostname, port).
        if updater.configuration.network_location in network_locations:
          Logger.info(HOSTNAME_FOUND_MESSAGE.format(netloc=network_location))
          # Raises an exception in case we do not recognize how to
          # transform this URL for TUF. In that case, there will be no
          # updater for this URL.
          target_filepath = updater.get_target_filepath(url)

        else:
          # Same hostname, but different (not user-specified) port.
          Logger.warn(DIFFERENT_NETLOC_MESSAGE.format(
            netloc1=updater.configuration.network_location, netloc2=network_locations))
          updater = None

    except:
      Logger.exception(GENERIC_WARNING_MESSAGE.format(url=url))
      updater = None

    finally:
      if updater is None:
        Logger.warn(GENERIC_WARNING_MESSAGE.format(url=url))

      return updater


  def remove(self, configuration):
    """Remove an Updater matching the given Configuration."""

    UPDATER_REMOVED_MESSAGE = "Updater removed for interposed {configuration}."

    assert isinstance(configuration, Configuration)

