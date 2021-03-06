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
API namespace for the Flask application.
'''

import flask


API = flask.Blueprint('api_ns', __name__, url_prefix='/api')

from pkgdb.doc_utils import load_doc

import acls
import collections
import packagers
import packages


@API.route('/')
def api():
    ''' Display the api information page. '''
    api_collection_new = load_doc(collections.api_collection_new)
    api_collection_status = load_doc(collections.api_collection_status)
    api_collection_list = load_doc(collections.api_collection_list)

    api_packager_acl = load_doc(packagers.api_packager_acl)
    api_packager_list = load_doc(packagers.api_packager_list)

    api_package_new = load_doc(packages.api_package_new)
    api_package_orphan = load_doc(packages.api_package_orphan)
    api_package_unorphan = load_doc(packages.api_package_unorphan)
    api_package_deprecate = load_doc(packages.api_package_deprecate)
    api_package_undeprecate = load_doc(packages.api_package_undeprecate)
    api_package_list = load_doc(packages.api_package_list)

    api_acl_get = load_doc(acls.api_acl_get)
    api_acl_update = load_doc(acls.api_acl_update)
    api_acl_reassign = load_doc(acls.api_acl_reassign)

    return flask.render_template(
        'api.html',
        collections=[
            api_collection_new, api_collection_status, api_collection_list,
        ],
        packagers=[
            api_packager_acl, api_packager_list,
        ],
        packages=[
            api_package_new, api_package_orphan, api_package_unorphan,
            api_package_deprecate, api_package_undeprecate,
            api_package_list,
        ],
        acls=[
            api_acl_get, api_acl_update, api_acl_reassign,
        ]
    )
