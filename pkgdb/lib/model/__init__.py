# -*- coding: utf-8 -*-
#
# Copyright © 2013  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions
# of the GNU General Public License v.2, or (at your option) any later
# version.  This program is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY expressed or implied, including the
# implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.  You
# should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Any Red Hat trademarks that are incorporated in the source
# code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission
# of Red Hat, Inc.
#

'''
Mapping of python classes to Database Tables.
'''

__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources

import datetime
import logging

import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.orm.collections import mapped_collection
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import and_
from sqlalchemy.sql.expression import Executable, ClauseElement

BASE = declarative_base()

error_log = logging.getLogger('pkgdb.lib.model.packages')

DEFAULT_GROUPS = {'provenpackager': {'commit': True}}


def create_tables(db_url, alembic_ini=None, debug=False):
    """ Create the tables in the database using the information from the
    url obtained.

    :arg db_url, URL used to connect to the database. The URL contains
        information with regards to the database engine, the host to
        connect to, the user and password and the database name.
          ie: <engine>://<user>:<password>@<host>/<dbname>
    :kwarg alembic_ini, path to the alembic ini file. This is necessary
        to be able to use alembic correctly, but not for the unit-tests.
    :kwarg debug, a boolean specifying wether we should have the verbose
        output of sqlalchemy or not.
    :return a session that can be used to query the database.

    """
    engine = create_engine(db_url, echo=debug)
    BASE.metadata.create_all(engine)
    #engine.execute(collection_package_create_view(driver=engine.driver))
    if db_url.startswith('sqlite:'):
        def _fk_pragma_on_connect(dbapi_con, con_record):
            dbapi_con.execute('pragma foreign_keys=ON')
        sa.event.listen(engine, 'connect', _fk_pragma_on_connect)

    if alembic_ini is not None:  # pragma: no cover
        # then, load the Alembic configuration and generate the
        # version table, "stamping" it with the most recent rev:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(alembic_ini)
        command.stamp(alembic_cfg, "head")

    scopedsession = scoped_session(sessionmaker(bind=engine))
    create_status(scopedsession)
    return scopedsession


def create_status(session):
    """ Fill in the status tables. """
    for acl in ['commit', 'watchbugzilla', 'watchcommits', 'approveacls']:
        obj = PkgAcls(acl)
        session.add(obj)

    for status in ['Approved', 'Awaiting Review', 'Denied', 'Obsolete',
                   'Removed']:
        obj = AclStatus(status)
        session.add(obj)

    for status in ['EOL', 'Active', 'Under Development']:
        obj = CollecStatus(status)
        session.add(obj)

    for status in ['Approved', 'Removed', 'Deprecated', 'Orphaned']:
        obj = PkgStatus(status)
        session.add(obj)

    session.commit()

### TODO: this is a view, create it as such...
#class CollectionPackage(Executable, ClauseElement):
    #'''Information about how many `Packages` are in a `Collection`

    #View -- CollectionPackage
    #'''

    #__tablename__ = 'CollectionPackage'
    #id = sa.Column(sa.Integer, nullable=False, primary_key=True)
    #name = sa.Column(sa.Text, nullable=False)
    #version = sa.Column(sa.Text, nullable=False)
    #status = sa.Column(sa.Enum('EOL', 'Active', 'Under Development',
                               #name='collection_status'),
                       #nullable=False)
    #numpkgs = sa.Column(sa.Integer, nullable=False)

    ## pylint: disable-msg=R0902, R0903
    #def __repr__(self):
        ## pylint: disable-msg=E1101
        #return 'CollectionPackage(id=%r, name=%r, version=%r,' \
            #' status=%r, numpkgs=%r,' \
            #% (self.id, self.name, self.version, self.status,
               #self.numpkgs)

#@compiles(CollectionPackage)
#def collection_package_create_view(*args, **kw):
    #sql_string = 'CREATE OR REPLACE VIEW'
    #if 'driver' in kw:
        #if kw['driver'] == 'pysqlite':
            #sql_string = 'CREATE VIEW IF NOT EXISTS'
    #return '%s CollectionPackage AS '\
           #'SELECT c.id, c.name, c.version, c.status, count(*) as numpkgs '\
           #'FROM "PackageListing" pl, "Collection" c '\
           #'WHERE pl.collection_id = c.id '\
           #'AND pl.status = "Approved" '\
           #'GROUP BY c.id, c.name, c.version, c.status '\
           #'ORDER BY c.name, c.version;' % sql_string


class PkgAcls(BASE):
    __tablename__ = 'PkgAcls'

    status = sa.Column(sa.String(50), primary_key=True)

    def __init__(self, status):
        """ Constructor. """
        self.status = status

    @classmethod
    def all_txt(cls, session):
        """ Return all the Acls in plain text for packages. """
        return [item.status for item in session.query(cls).all()]


class PkgStatus(BASE):
    __tablename__ = 'PkgStatus'

    status = sa.Column(sa.String(50), primary_key=True)

    def __init__(self, status):
        """ Constructor. """
        self.status = status

    @classmethod
    def all_txt(cls, session):
        """ Return all the status in plain text for packages. """
        return [item.status for item in session.query(cls).all()]


class AclStatus(BASE):
    __tablename__ = 'AclStatus'

    status = sa.Column(sa.String(50), primary_key=True)

    def __init__(self, status):
        """ Constructor. """
        self.status = status

    @classmethod
    def all_txt(cls, session):
        """ Return all the status in plain text for packages. """
        return [item.status for item in session.query(cls).all()]


class CollecStatus(BASE):
    __tablename__ = 'CollecStatus'

    status = sa.Column(sa.String(50), primary_key=True)

    def __init__(self, status):
        """ Constructor. """
        self.status = status

    @classmethod
    def all_txt(cls, session):
        """ Return all the status in plain text for a collection. """
        return [item.status for item in session.query(cls).all()]


class PackageListingAcl(BASE):
    '''Give a person or a group ACLs on a specific PackageListing.

    Table -- PackageListingAcl
    '''

    __tablename__ = 'PackageListingAcl'

    id = sa.Column(sa.Integer, primary_key=True)
    fas_name = sa.Column(sa.String(32), nullable=False)
    packagelisting_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('PackageListing.id',
                      ondelete='CASCADE',
                      onupdate='CASCADE'
                      ),
        nullable=False,
    )
    acl = sa.Column(sa.String(50), sa.ForeignKey('PkgAcls.status'),
                    nullable=False)
    status = sa.Column(sa.String(50), sa.ForeignKey('AclStatus.status'),
                       nullable=False)

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    packagelist = relation('PackageListing')

    __table_args__ = (
        sa.UniqueConstraint('fas_name', 'packagelisting_id', 'acl'),
    )

    @classmethod
    def all(cls, session):
        ''' Return the list of all Collections present in the database.

        :arg cls: the class object
        :arg session: the database session used to query the information.

        '''
        return session.query(cls).all()

    @classmethod
    def get_top_maintainers(cls, session, limit=10):
        """ Return the username and number of commits ACLs ordered by number
        of commits.

        :arg session: session with which to connect to the database
        :arg limit: the number of top maintainer to return, defaults to 10.

        """
        query = session.query(
            sa.func.distinct(cls.fas_name),
            sa.func.count(
                sa.func.distinct(PackageListing.package_id)
            ).label('cnt')
        ).filter(
            cls.packagelisting_id == PackageListing.id
        ).filter(
            cls.acl == 'commit'
        ).filter(
            cls.status == 'Approved'
        ).group_by(
            cls.fas_name
        ).order_by(
            'cnt DESC'
        ).limit(limit)
        return query.all()

    @classmethod
    def get_acl_packager(cls, session, packager):
        """ Retrieve the ACLs associated with a packager.

        :arg session: the database session used to connect to the
            database
        :arg packager: the username of the packager to retrieve the ACls
            of
        """
        acls = session.query(PackageListingAcl).filter(
            PackageListingAcl.fas_name == packager
        ).all()
        return acls

    @classmethod
    def get_acl_package(cls, session, user, package,
                        status="Awaiting Review"):
        """ Return the pending ACLs for the specified package owned by
        user.

        """
        # Get all the packages of this person
        stmt = session.query(Package.id).filter(
            Package.name == package
        ).subquery()

        stmt2 = session.query(PackageListing.id).filter(
            PackageListing.package_id == stmt
        ).subquery()

        query = session.query(cls).filter(
            PackageListingAcl.packagelisting_id.in_(stmt2)
        ).filter(
            PackageListingAcl.fas_name == user
        )

        if status:
            query = query.filter(
                cls.status == status
            )
        return query.all()

    @classmethod
    def get_or_create(cls, session, user, packagelisting_id, acl, status):
        """ Retrieve the PersonPackageListing which associates a person
        with a package in a certain collection.

        :arg session: the database session used to connect to the
            database
        :arg user: the username
        :arg packagelisting_id: the identifier of the PackageListing
            entry.
        :arg acl: the ACL that person has on that package
        :arg status: the status of the ACL
        """
        try:
            personpkg = session.query(PackageListingAcl).filter(
                PackageListingAcl.fas_name == user
            ).filter(
                PackageListingAcl.packagelisting_id == packagelisting_id
            ).filter(
                PackageListingAcl.acl == acl
            ).one()
        except NoResultFound:
            personpkg = PackageListingAcl(
                fas_name=user,
                packagelisting_id=packagelisting_id,
                acl=acl,
                status=status)
            session.add(personpkg)
            session.flush()

        return personpkg

    @classmethod
    def get_pending_acl(cls, session, user):
        """ Return for all the packages of which `user` is point of
        contact the ACL which have status 'Awaiting Review'.

        :arg session:
        :arg user:
        """
        stmt = session.query(PackageListing.id).filter(
            PackageListing.point_of_contact == user
        ).subquery()

        # Match the other criteria
        query = session.query(cls).filter(
            cls.packagelisting_id.in_(stmt)
        ).filter(
            cls.status == 'Awaiting Review'
        )
        return query.all()

    # pylint: disable-msg=R0903
    def __init__(self, fas_name, packagelisting_id, acl, status):
        self.fas_name = fas_name
        self.packagelisting_id = packagelisting_id
        self.acl = acl
        self.status = status

    def __repr__(self):
        return 'PackageListingAcl(id:%r, %r, PackageListing:%r, Acl:%s, ' \
            '%s)' % (
                self.id, self.fas_name, self.packagelisting_id, self.acl,
                self.status)

    def to_json(self):
        """ Return a dictionnary representation of this object. """
        return dict(
            packagelist=self.packagelist.to_json(),
            fas_name=self.fas_name,
            acl=self.acl,
            status=self.status,
        )


class Collection(BASE):
    '''A Collection of packages.

    Table -- Collection
    '''

    __tablename__ = 'Collection'
    id = sa.Column(sa.Integer, nullable=False, primary_key=True)
    name = sa.Column(sa.Text, nullable=False)
    version = sa.Column(sa.Text, nullable=False)
    status = sa.Column(sa.String(50), sa.ForeignKey('CollecStatus.status'),
                       nullable=False)
    owner = sa.Column(sa.String(32), nullable=False)
    publishURLTemplate = sa.Column(sa.Text)
    pendingURLTemplate = sa.Column(sa.Text)
    summary = sa.Column(sa.Text)
    description = sa.Column(sa.Text)
    branchname = sa.Column(sa.String(32), unique=True, nullable=False)
    distTag = sa.Column(sa.String(32), unique=True, nullable=False)
    git_branch_name = sa.Column(sa.Text)

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    __table_args__ = (
        sa.UniqueConstraint('name', 'version'),
    )

    # pylint: disable-msg=R0902, R0903
    def __init__(self, name, version, status, owner,
                 publishURLTemplate=None, pendingURLTemplate=None,
                 summary=None, description=None, branchname=None,
                 distTag=None, git_branch_name=None):
        self.name = name
        self.version = version
        self.status = status
        self.owner = owner
        self.publishURLTemplate = publishURLTemplate
        self.pendingURLTemplate = pendingURLTemplate
        self.summary = summary
        self.description = description
        self.branchname = branchname
        self.distTag = distTag
        self.git_branch_name = git_branch_name

    def __repr__(self):
        return 'Collection(%r, %r, %r, %r, publishurltemplate=%r,' \
               ' pendingurltemplate=%r, summary=%r, description=%r)' % (
                   self.name, self.version, self.status, self.owner,
                   self.publishURLTemplate, self.pendingURLTemplate,
                   self.summary, self.description)

    def api_repr(self, version):
        """ Used by fedmsg to serialize Collections in messages. """
        if version == 1:
            return dict(
                name=self.name,
                version=self.version,
                publishurltemplate=self.publishURLTemplate,
                pendingurltemplate=self.pendingURLTemplate,
            )
        elif version == 2:
            return dict(
                name=self.name,
                version=self.version,
                branchname=self.branchname,
                publishurltemplate=self.publishURLTemplate,
                pendingurltemplate=self.pendingURLTemplate,
            )
        else:  # pragma: no cover
            raise NotImplementedError("Unsupported version %r" % version)

    @classmethod
    def by_name(cls, session, branch_name):
        '''Return the Collection that matches the simple name

        :arg branch_name: branch name for a Collection
        :returns: The Collection that matches the name
        :raises sqlalchemy.InvalidRequestError: if the simple name is not found

        simple_name will be looked up as the Branch name.
        '''
        collection = session.query(cls).filter(
            Collection.branchname == branch_name).one()
        return collection

    @classmethod
    def all(cls, session):
        ''' Return the list of all Collections present in the database.

        :arg cls: the class object
        :arg session: the database session used to query the information.

        '''
        return session.query(cls).all()

    @classmethod
    def search(cls, session, clt_name, clt_status=None, offset=None,
               limit=None, count=False):
        ''' Return the Collections matching the criteria.

        :arg cls: the class object
        :arg session: the database session used to query the information.
        :arg clt_name: pattern to retrict the Collection queried
        :kwarg clt_status: the status of the Collection
        :kwarg offset: the offset to apply to the results
        :kwarg limit: the number of results to return
        :kwarg count: a boolean to return the result of a COUNT query
            if true, returns the data if false (default).

        '''
        # Get all the packages matching the name
        query = session.query(Collection).filter(
            Collection.branchname.like(clt_name)
        )
        if clt_status:
            query = query.filter(Collection.status == clt_status)

        if count:
            return query.count()

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        return query.all()


class PackageListing(BASE):
    '''This associates a package with a particular collection.

    Table -- PackageListing
    '''

    __tablename__ = 'PackageListing'
    id = sa.Column(sa.Integer, nullable=False, primary_key=True)
    package_id = sa.Column(sa.Integer,
                           sa.ForeignKey('Package.id',
                                         ondelete="CASCADE",
                                         onupdate="CASCADE"
                                         ),
                           nullable=False)
    point_of_contact = sa.Column(sa.Text, nullable=False)
    collection_id = sa.Column(sa.Integer,
                              sa.ForeignKey('Collection.id',
                                            ondelete="CASCADE",
                                            onupdate="CASCADE"
                                            ),
                              nullable=False)
    status = sa.Column(sa.String(50), sa.ForeignKey('PkgStatus.status'),
                       nullable=False)
    status_change = sa.Column(sa.DateTime, nullable=False,
                              default=datetime.datetime.utcnow)
    __table_args__ = (
        sa.UniqueConstraint('package_id', 'collection_id'),
    )

    package = relation("Package")
    collection = relation("Collection")
    acls = relation(
        PackageListingAcl,
        backref=backref('packagelisting'),
    )

    def __init__(self, point_of_contact, status, package_id=None,
                 collection_id=None):
        self.package_id = package_id
        self.collection_id = collection_id
        self.point_of_contact = point_of_contact
        self.status = status

    packagename = association_proxy('package', 'name')

    @classmethod
    def by_package_id(cls, session, pkgid):
        """ Return the PackageListing object based on the Package ID.

        :arg pkgid: Integer, identifier of the package in the Package
            table

        """

        return session.query(cls).filter(
            PackageListing.package_id == pkgid
        ).all()

    @classmethod
    def by_pkgid_collectionid(cls, session, pkgid, collectionid):
        '''Return the PackageListing for the provided package in the
        specified collection.

        :arg pkgid: Integer, identifier of the package in the Package
            table
        :arg collectionid: Integer, identifier of the collection in the
            Collection table
        :returns: The PackageListing that matches this package identifier
            and collection iddentifier
        :raises sqlalchemy.InvalidRequestError: if the simple name is not found

        '''
        return session.query(cls).filter(
            PackageListing.package_id == pkgid
        ).filter(
            PackageListing.collection_id == collectionid
        ).one()

    @classmethod
    def search(cls, session, pkg_name, clt_id, pkg_owner=None,
               pkg_status=None, offset=None, limit=None, count=False):
        """
        Return the list of packages matching the given criteria

        :arg session: session with which to connect to the database
        :arg pkg_name: the name of the package
        :arg clt_id: the identifier of the collection
        :arg pkg_owner: name of the new owner of the package
        :arg pkg_status: status of the package
        :kwarg offset: the offset to apply to the results
        :kwarg limit: the number of results to return
        :kwarg count: a boolean to return the result of a COUNT query
            if true, returns the data if false (default).

        """
        # Get all the packages matching the name
        stmt = session.query(Package).filter(
            Package.name.like(pkg_name)
        ).subquery()
        # Match the other criteria
        query = session.query(cls).filter(
            PackageListing.package_id == stmt.c.id
        )

        if clt_id:
            query = query.filter(PackageListing.collection_id == clt_id)
        if pkg_owner:
            query = query.filter(
                PackageListing.point_of_contact == pkg_owner)
        if pkg_status:
            query = query.filter(PackageListing.status == pkg_status)

        if count:
            return query.count()

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def search_point_of_contact(cls, session, pattern, offset=None,
                                limit=None, count=False):
        """ Return all the package whose point_of_contact match the
        pattern.

        :arg session: session with which to connect to the database
        :arg pattern: pattern the point_of_contact of the package should
            match
        :kwarg offset: the offset to apply to the results
        :kwarg limit: the number of results to return
        :kwarg count: a boolean to return the result of a COUNT query
            if true, returns the data if false (default).

        """
        query1 = session.query(
            sa.func.distinct(cls.point_of_contact)
        ).filter(
            PackageListing.point_of_contact.like(pattern)
        )

        query2 = session.query(
            sa.func.distinct(PackageListingAcl.fas_name)
        ).filter(
            PackageListingAcl.fas_name.like(pattern)
        )
        query = query1.union(query2)

        if count:
            return query.count()

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def get_top_poc(cls, session, limit=10):
        """ Return the username and number of commits ACLs ordered by number
        of commits.

        :arg session: session with which to connect to the database
        :arg limit: the number of top maintainer to return, defaults to 10.

        """
        query = session.query(
            sa.func.distinct(PackageListing.point_of_contact),
            sa.func.count(
                sa.func.distinct(PackageListing.package_id)
            ).label('cnt')
        ).filter(
            PackageListing.status == 'Approved'
        ).group_by(
            PackageListing.point_of_contact
        ).order_by(
            'cnt DESC'
        ).limit(limit)
        return query.all()

    def __repr__(self):
        return 'PackageListing(id:%r, %r, %r, packageid=%r, collectionid=%r' \
               ')' % (
                   self.id, self.point_of_contact, self.status,
                   self.package_id, self.collection_id)

    def api_repr(self, version):
        """ Used by fedmsg to serialize PackageListing in messages. """
        if version == 1:
            return dict(
                package=self.package.api_repr(version),
                collection=self.collection.api_repr(version),
                point_of_contact=self.point_of_contact,
            )
        else:  # pragma: no cover
            raise NotImplementedError("Unsupported version %r" % version)

    def clone(self, branch, author_name):
        '''Clone the permissions on this PackageListing to another `Branch`.

        :arg branch: `branchname` to make a new clone for
        :arg author_name: Author of the change.  Note, will remove when logs
            are made generic
        :raises sqlalchemy.exceptions.InvalidRequestError: when a request
            does something that violates the SQL integrity of the database
            somehow.
        :returns: new branch
        :rtype: PackageListing
        '''
        # Retrieve the PackageListing for the to clone branch
        try:
            #pylint:disable-msg=E1101
            clone_branch = PackageListing.query.join('package').join(
                'collection'
            ).filter(
                and_(Package.name == self.package.name,
                     Collection.branchname == branch)
            ).one()
            #pylint:enable-msg=E1101
        except InvalidRequestError:
            ### Create a new package listing for this release ###

            # Retrieve the collection to make the branch for
            #pylint:disable-msg=E1101
            clone_collection = Branch.query.filter_by(branchname=branch).one()
            #pylint:enable-msg=E1101
            # Create the new PackageListing
            clone_branch = self.package.create_listing(
                clone_collection,
                self.owner,
                STATUS[self.statuscode],
                qacontact=self.qacontact,
                author_name=author_name)

        log_params = {'user': author_name,
                      'pkg': self.package.name,
                      'branch': branch}
        # Iterate through the acls in the master_branch
        #pylint:disable-msg=E1101
        for group_name, group in self.groups2.iteritems():
        #pylint:enable-msg=E1101
            log_params['group'] = group_name
            if group_name not in clone_branch.groups2:
                # Associate the group with the packagelisting
                #pylint:disable-msg=E1101
                clone_branch.groups2[group_name] = \
                    GroupPackageListing(group_name)
                #pylint:enable-msg=E1101
            clone_group = clone_branch.groups2[group_name]
            for acl_name, acl in group.acls2.iteritems():
                if acl_name not in clone_group.acls2:
                    clone_group.acls2[acl_name] = \
                        GroupPackageListingAcl(acl_name, acl.status)
                else:
                    # Set the acl to have the correct status
                    if acl.status != clone_group.acls2[acl_name].status:
                        clone_group.acls2[acl_name].status = acl.status

                #TODO: Create a log message for this acl

        #pylint:disable-msg=E1101
        for person_name, person in self.people2.iteritems():
        #pylint:enable-msg=E1101
            log_params['person'] = person_name
            if person_name not in clone_branch.people2:
                # Associate the person with the packagelisting
                #pylint:disable-msg=E1101
                clone_branch.people2[person_name] = \
                    PersonPackageListing(person_name)
                #pylint:enable-msg=E1101
            clone_person = clone_branch.people2[person_name]
            for acl_name, acl in person.acls2.iteritems():
                if acl_name not in clone_person.acls2:
                    clone_person.acls2[acl_name] = \
                        PersonPackageListingAcl(acl_name, acl.status)
                else:
                    # Set the acl to have the correct status
                    if clone_person.acls2[acl_name].status \
                            != acl.status:
                        clone_person.acls2[acl_name].status = acl.status
                #TODO: Create a log message for this acl

        return clone_branch

    def to_json(self):
        """ Return a dictionnary representation of this object. """
        return dict(package=self.package.api_repr(1),
                    collection=self.collection.api_repr(2),
                    point_of_contact=self.point_of_contact,
                    )


class Package(BASE):
    '''Software we are packaging.

    This is equal to the software in one of our revision control directories.
    It is unversioned and not associated with a particular collection.

    Table -- Package
    '''

    __tablename__ = 'Package'
    id = sa.Column(sa.Integer, nullable=False, primary_key=True)
    name = sa.Column(sa.Text, nullable=False, unique=True)
    summary = sa.Column(sa.Text, nullable=False)
    review_url = sa.Column(sa.Text)
    upstream_url = sa.Column(sa.Text)
    status = sa.Column(sa.String(50), sa.ForeignKey('PkgStatus.status'),
                       nullable=False)
    shouldopen = sa.Column(sa.Boolean, nullable=False, default=True)

    listings = relation(PackageListing)

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    @classmethod
    def by_name(cls, session, pkgname):
        """ Return the package associated to the given name.

        :raises sqlalchemy.InvalidRequestError: if the package name is
            not found
        """
        return session.query(cls).filter(Package.name == pkgname).one()

    def __init__(self, name, summary, status, reviewurl=None,
                 shouldopen=None, review_url=None, upstream_url=None):
        self.name = name
        self.summary = summary
        self.status = status
        self.review_url = review_url
        self.shouldopen = shouldopen
        self.upstream_url = upstream_url

    def __repr__(self):
        return 'Package(%r, %r, %r, ' \
            'upstreamurl=%r, reviewurl=%r, shouldopen=%r)' % (
                self.name, self.summary, self.status,
                self.upstream_url, self.review_url, self.shouldopen)

    def api_repr(self, version):
        """ Used by fedmsg to serialize Packages in messages. """
        if version == 1:
            return dict(
                name=self.name,
                summary=self.summary,
                reviewurl=self.review_url,
                upstreamurl=self.upstream_url,
            )
        else:  # pragma: no cover
            raise NotImplementedError("Unsupported version %r" % version)

    def create_listing(self, collection, point_of_contact, statusname,
                       author_name=None):
        '''Create a new PackageListing branch on this Package.

        :arg collection: Collection that the new PackageListing lives on
        :arg owner: The owner of the PackageListing
        :arg statusname: Status to set the PackageListing to
        :kwarg author_name: Author of the change.  Note: will remove when
            logging is made generic
        :returns: The new PackageListing object.

        This creates a new PackageListing for this Package.
        The PackageListing has default values set for group acls.
        '''
        pkg_listing = PackageListing(point_of_contact=point_of_contact,
                                     status=statusname,
                                     collection_id=collection.id)
        pkg_listing.package_id = self.id

        #TODO: Create a log message
        return pkg_listing

    @classmethod
    def all(cls, session):
        ''' Return the list of all Collections present in the database.

        :arg cls: the class object
        :arg session: the database session used to query the information.

        '''
        return session.query(cls).all()

    @classmethod
    def search(cls, session, pkg_name, pkg_poc=None, pkg_status=None,
               offset=None, limit=None, count=False):
        """ Search the Packages for the one fitting the given pattern.

        :arg session: session with which to connect to the database
        :arg pkg_name: the name of the package
        :kwarg pkg_poc: name of the new point of contact for the package
        :kwarg pkg_status: status of the package
        :kwarg offset: the offset to apply to the results
        :kwarg limit: the number of results to return
        :kwarg count: a boolean to return the result of a COUNT query
            if true, returns the data if false (default).

        """
        query = session.query(Package).filter(
            Package.name.like(pkg_name)
        )
        if pkg_poc:
            query = query.join(PackageListing).filter(
                PackageListing.point_of_contact == pkg_poc
            )
        if pkg_status:
            query = query.filter(Package.status == pkg_status)

        if count:
            return query.count()

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def get_package_of_user(cls, session, user, pkg_status=None):
        """ Return the list of packages on which a given user has commit
        rights.

        :arg session: session with which to connect to the database.
        :arg user: the FAS username of the user of interest.
        :kwarg pkg_status: the status of the packages considered.

        """
        query = session.query(Package).filter(
            Package.id == PackageListing.package_id
        ).filter(
            PackageListing.id == PackageListingAcl.packagelisting_id
        ).filter(
            PackageListingAcl.fas_name == user
        ).filter(
            PackageListingAcl.acl == 'commit'
        ).filter(
            PackageListingAcl.status == 'Approved'
        )

        if pkg_status:
            query = query.filter(Package.status == pkg_status)

        return query.all()

    def to_json(self):
        ''' Return a dictionnary representation of the object.
        '''
        acls = [pkg.to_json() for pkg in self.listings]
        return {'name': self.name,
                'summary': self.summary,
                'status': self.status,
                'review_url': self.review_url,
                'upstream_url': self.upstream_url,
                'acls': acls,
                'creation_date': self.date_created
                }


class Log(BASE):
    '''Base Log record.

    This is a Log record.  All logs will be entered via a subclass of this.

    Table -- Log
    '''

    __tablename__ = 'Log'
    id = sa.Column(sa.Integer, nullable=False, primary_key=True)
    user = sa.Column(sa.String(32), nullable=False)
    change_time = sa.Column(sa.DateTime, nullable=False,
                            default=datetime.datetime.utcnow)
    package_id = sa.Column(sa.Integer,
                           sa.ForeignKey('Package.id',
                                         ondelete='RESTRICT',
                                         onupdate='CASCADE'
                                         ),
                           nullable=True,
                           )
    description = sa.Column(sa.Text, nullable=False)

    def __init__(self, user, package_id, description):
        self.user = user
        self.package_id = package_id
        self.description = description

    def __repr__(self):
        return 'Log(user=%r, description=%r, change_time=%r)' % (
            self.user, self.description,
            self.change_time.strftime('%Y-%m-%d %H:%M:%S'))

    @classmethod
    def search(cls, session, package_id=None, from_date=None, limit=None,
               offset=None, count=False):
        ''' Return the list of the last Log entries present in the database.

        :arg cls: the class object
        :arg session: the database session used to query the information.
        :kwarg limit: limit the result to X row
        :kwarg offset: start the result at row X
        :kwarg from_date: the date from which to give the entries
        :kwarg count: a boolean to return the result of a COUNT query
            if true, returns the data if false (default).

        '''
        query = session.query(
            cls
        )

        if count:
            return query.count()

        if package_id:
            query = query.filter(cls.package_id == package_id)

        if from_date:
            query = query.filter(cls.change_time <= from_date)

        query = query.order_by(cls.change_time.asc())

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    @classmethod
    def insert(cls, session, user, package, description):
        ''' Insert the given log entry into the database.

        :arg session: the session to connect to the database with
        :arg user: the username of the user doing the action
        :arg package: the `Package` object of the package changed
        :arg description: a short textual description of the action
            performed

        '''
        if package:
            log = Log(user, package.id, description)
        else:
            log = Log(user, None, description)
        session.add(log)
        session.flush()
