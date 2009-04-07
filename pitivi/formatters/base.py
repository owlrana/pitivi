# PiTiVi , Non-linear video editor
#
#       formatter.base
#
# Copyright (c) 2009, Edward Hervey <bilboed@bilboed.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
Base Formatter classes
"""

from pitivi.project import Project
from pitivi.utils import uri_is_reachable, uri_is_valid
from pitivi.signalinterface import Signallable

class FormatterError(Exception):
    pass

class FormatterURIError(Exception):
    """An error occured with a URI"""

class FormatterLoadError(FormatterError):
    """An error occured while loading the Project"""

class FormatterParseError(FormatterLoadError):
    """An error occured while parsing the project file"""

class FormatterSaveError(FormatterError):
    """An error occured while saving the Project"""

class FormatterOverwriteError(FormatterSaveError):
    """A project can't be saved because it will be overwritten"""

class Formatter(object, Signallable):
    """
    Provides convenience methods for storing and loading
    Project files.

    Signals:
     - C{missing-uri} : A uri can't be found.

    @cvar description: Description of the format.
    @type description: C{str}
    @cvar project: The project being loaded/saved
    @type project: L{Project}
    """

    __signals__ = {
        "missing-uri" : ["uri"]
        }

    description = "Description of the format"
    ProjectClass = Project

    def __init__(self):
        # mapping of directory changes
        # key : old path
        # value : new path
        self.directorymapping = {}

        self.project = None

    #{ Load/Save methods

    def newProject(self):
        return self.ProjectClass()

    def loadProject(self, location, project=None):
        """
        Loads the project from the given location.

        @postcondition: There is no guarantee that the returned project
        is fully loaded. Callers should check

        @type location: C{URI}
        @param location: The location of a file. Needs to be an absolute URI.
        @rtype: L{Project}
        @return: The L{Project}
        @raise FormatterLoadError: If the file couldn't be properly loaded.
        """
        # check if the location is
        # .. a uri
        # .. a valid uri
        # .. a reachable valid uri
        # FIXME : Allow subclasses to handle this for 'online' (non-file://) URI
        if not uri_is_valid(location) or not uri_is_reachable(location):
            raise FormatterURIError()

        # parse the format (subclasses)
        # FIXME : maybe have a convenience method for opening a location
        self.parse(location)

        if not project:
            project = self.newProject()

        # ask for all sources being used
        uris = []
        factories = []
        wtf = []
        for x in self._getSources():
            if isinstance(x, SourceFactory):
                factories.append(x)
            elif isinstance(x, str):
                uris.append(x)
            else:
                raise FormatterLoadError("Got invalid sources !")

        # from this point on we're safe !
        self.project = project
        project._formatter = self

        # add all factories to the project sourcelist
        for fact in factories:
            project.sources.addFactory(fact)

        # if all sources were discovered, or don't require discovering,
        if uris == []:
            # then
            # .. Fill in the timeline
            self._fillTimeline(self)
            # .. make the project as loaded
            self.project.loaded = True
        else:
            # else
            # .. connect to the sourcelist 'ready' signal
            self.project.sources.connect("ready", self._sourcesReadyCb)
            # .. Add all uris to be discovered to the project sourcelist
            self.project.loaded = False
            self.project.sources.addUris(uris)

        # finally return the project.
        return self.project

    def saveProject(self, project, location, overwrite=False):
        """
        Saves the given project to the given location.

        @type project: L{Project}
        @param project: The Project to store.
        @type location: C{URI}
        @param location: The location where to store the project. Needs to be
        an absolute URI.
        @param overwrite: Whether to overwrite existing location.
        @type overwrite: C{bool}
        @raise FormatterURIError: If the location isn't a valid C{URI}.
        @raise FormatterOverwriteError: If the location already exists and overwrite is False.
        @raise FormatterSaveError: If the file couldn't be properly stored.
        """
        if not uri_is_valid(location):
            raise FormatterURIError()
        if overwrite == False and uri_is_reachable(location):
            raise FormatterOverwriteError()
        self._saveProject(project, location)

    #}

    @classmethod
    def canHandle(cls, location):
        """
        Can this Formatter load the project at the given location.

        @type location: C{URI}
        @param location: The location. Needs to be an absolute C{URI}.
        @rtype: C{bool}
        @return: True if this Formatter can load the L{Project}.
        """
        raise NotImplementedError

    #{ Subclass methods

    def _saveProject(self, project, location):
        """
        Save the given project to the given location.

        Sub classes should implement this.

        @precondition: The location is guaranteed to be writable.

        @param project: the project to store.
        @type project: L{Project}
        @type location: C{URI}
        @param location: The location where to store the project. Needs to be
        an absolute URI.
        """
        raise NotImplementedError

    def _getSources(self):
        """
        Return all the sources used in a project.

        To be implemented by subclasses.

        The returned sources can be either:
         - C{URI}
         - any L{SourceFactory} fully-discovered subclass.

        The returned locations (C{URI}) must be valid uri. Subclasses can
        call L{validateSourceURI} to make sure the C{URI} is valid.

        @precondition: L{_parse} will be called before, so subclasses can
        use any information they extracted during that call.
        @returns: A list of sources used in the given project.
        """
        raise NotImplementedError

    def _parse(self, location):
        """
        Open and parse the given location.

        To be implemented by subclasses.

        If any error occurs during this step, subclasses should raise the
        FormatterParseError exception.
        """
        raise NotImplementedError

    #{ Missing uri methods

    def addMapping(self, oldpath, newpath):
        """
        Add a mapping for moved files.

        This should be called in callbacks from 'missing-uri'.

        @param oldpath: Old location (as provided by 'missing-uri').
        @type oldpath: C{URI}
        @param newpath: The new location corresponding to oldpath.
        @type newpath: C{URI}
        """
        raise NotImplementedError

    def validateSourceURI(self, uri):
        """
        Makes sure the given uri is accessible for reading.

        Subclasses should call this method for any C{URI} they parse,
        in order to make sure they have the valid C{URI} on this given
        setup.

        @returns: The valid 'uri'. It might be different from the
        input. Sub-classes must use this for any URI they wish to
        read from. If no valid 'uri' can be found, None will be
        returned.
        @rtype: C{URI} or C{None}
        """
        if not uri_is_valid(uri):
            return None

        # skip non local uri
        if not uri.split('://', 1)[0] in ["file"]:
            return uri

        # first check the good old way
        if not uri_is_valid(uri) or not uri_is_reachable(uri):
            return None

        localpath = uri.split('://', 1)[1]

        # else let's figure out if we have a compatible mapping
        for k, v in self.directorymapping.iteritems():
            if localpath.startswith(k):
                return localpath.replace(k, v, 1)

        # else, let's fire the signal...
        self.emit('missing-uri', uri)

        # and check again
        for k, v in self.directorymapping.iteritems():
            if localpath.startswith(k):
                return localpath.replace(k, v, 1)

        # Houston, we have lost contact with mission://fail
        return None

    #}

    def _sourcesReadyCb(self, sources):
        self._fillTimeline(self)
        self.project.loaded = True
        Project.emit(self.project, 'loaded')


class LoadOnlyFormatter(Formatter):
    def saveProject(self, project, location):
        raise FormatterSaveError("No Saving feature")


class SaveOnlyFormatter(Formatter):
    def saveProject(self, project, location):
        raise FormatterSaveError("No Saving feature")


class DefaultFormatter(Formatter):

    description = "PiTiVi default file format"

    pass

