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
Top level of the pkgdb Flask application.
'''

import flask
import os

from functools import wraps
from flask.ext.fas_openid import FAS

import lib as pkgdblib


__version__ = '0.1.0'

APP = flask.Flask(__name__)
APP.config.from_object('pkgdb.default_config')
if 'PKGDB_CONFIG' in os.environ:  # pragma: no cover
    APP.config.from_envvar('PKGDB_CONFIG')

# Set up FAS extension
FAS = FAS(APP)

SESSION = pkgdblib.create_session(APP.config['DB_URL'])


class FakeFasUser(object):
    """ Fake FAS user used for the tests. """
    id = 100
    username = 'pingou'
    groups = ['packager', 'cla_done']


def is_pkgdb_admin(user):
    """ Is the user a pkgdb admin.
    """
    if not user:
        return False
    if not user.cla_done or len(user.groups) < 1:
        return False

    admins = APP.config['ADMIN_GROUP']
    if isinstance(admins, basestring):
        admins = [admins]
    admins = set(admins)

    return len(admins.intersection(set(user.groups))) > 0


def is_pkg_admin(user, package, branch):
    """ Is the user an admin for this package.
    Admin =
        - user has approveacls rights
        - user is a pkgdb admin
    """
    if not user:
        return False
    if is_pkgdb_admin(user):
        return True
    else:
        return pkgdblib.has_acls(
            SESSION, user=user.username,
            package=package, branch=branch, acl='approveacls')


def fas_login_required(function):
    """ Flask decorator to ensure that the user is logged in against FAS.
    """
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if flask.g.fas_user is None:
            return flask.redirect(flask.url_for(
                '.login', next=flask.request.url))
        return function(*args, **kwargs)
    return decorated_function


def packager_login_required(function):
    """ Flask decorator to ensure that the user is logged in against FAS
    and is part of the 'packager' group.
    """
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if flask.g.fas_user is None:
            return flask.redirect(flask.url_for(
                '.login', next=flask.request.url))
        elif 'packager' not in flask.g.fas_user.groups:
            flask.flash('You must be a packager', 'errors')
            return flask.redirect(flask.url_for('ui_ns.msg'))
        return function(*args, **kwargs)
    return decorated_function


def is_admin(function):
    """ Decorator used to check if the loged in user is a pkgdb admin
    or not.
    """
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if flask.g.fas_user is None or \
                not flask.g.fas_user.cla_done or \
                len(flask.g.fas_user.groups) < 1:
            return flask.redirect(flask.url_for('.login',
                                                next=flask.request.url))
        elif not is_pkgdb_admin(flask.g.fas_user):
            flask.flash('You are not an administrator of pkgdb', 'errors')
            return flask.redirect(flask.url_for('ui_ns.msg'))
        else:
            return function(*args, **kwargs)
    return decorated_function


# Import the API namespace
from api import API
from api import acls
from api import collections
from api import packages
from api import packagers
APP.register_blueprint(API)

# Import the UI namespace
from ui import UI
from ui import acls
from ui import admin
from ui import collections
from ui import packages
from ui import packagers
APP.register_blueprint(UI)


# pylint: disable=W0613
@APP.teardown_request
def shutdown_session(exception=None):
    """ Remove the DB session at the end of each request. """
    SESSION.remove()
