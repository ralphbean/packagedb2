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
API for package management.
'''

import flask
import itertools

import pkgdb.forms
import pkgdb.lib as pkgdblib
from pkgdb.api import API


## Package
@API.route('/package/new/', methods=['POST'])
def api_package_new():
    ''' Create a new package.

    :arg packagename: String of the package name to be created.
    :arg summary: String of the summary description of the package.

    '''
    httpcode = 200
    output = {}

    collections = pkgdb.lib.search_collection(
        SESSION, '*', 'Under Development')
    collections.extend(pkgdb.lib.search_collection(SESSION, '*', 'Active'))
    pkg_status = pkgdb.lib.get_status(SESSION, 'pkg_status')['pkg_status']

    form = forms.AddPackageForm(
        csrf_enabled=False,
        collections=collections,
        pkg_status_list=pkg_status,
    )
    if form.validate_on_submit():
        pkg_name = form.pkg_name.data
        pkg_summary = form.pkg_summary.data
        pkg_reviewURL = form.pkg_reviewURL.data
        pkg_status = form.pkg_status.data
        pkg_shouldopen = form.pkg_shouldopen.data
        pkg_collection = form.pkg_collection.data
        pkg_owner = form.pkg_owner.data
        pkg_upstreamURL = form.pkg_upstreamURL.data

        try:
            message = pkgdblib.add_package(SESSION,
                                           pkg_name=pkg_name,
                                           pkg_summary=pkg_summary,
                                           pkg_reviewURL=pkg_reviewURL,
                                           pkg_status=pkg_status,
                                           pkg_shouldopen=pkg_shouldopen,
                                           pkg_collection=pkg_collection,
                                           pkg_owner=pkg_owner,
                                           pkg_upstreamURL=pkg_upstreamURL,
                                           user=flask.g.fas_user)
            SESSION.commit()
            output['output'] = 'ok'
            output['messages'] = [message]
        except pkgdblib.PkgdbException, err:
            SESSION.rollback()
            output['output'] = 'notok'
            output['error'] = err
            httpcode = 500
    else:
        output['output'] = 'notok'
        output['error'] = 'Invalid input submitted'
        if form.errors:
            detail = []
            for error in form.errors:
                detail.append('%s: %s' % (error,
                              '; '.join(form.errors[error])))
            output['error_detail'] = detail
        httpcode = 500

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout


@API.route('/package/orphan/', methods=['POST'])
def api_package_orphan():
    ''' Orphan a list of packages.

    :arg packagenames: List of string of the packages name.
    :arg branches: List of string of the branches name in which these
        packages will be orphaned.
    :arg all_pkgs: boolean (defaults to False) stipulating if all the
        packages of the user (you or someon else if you are admin) are
        getting orphaned.

     '''
    httpcode = 200
    output = {}

    form = forms.PackageOwnerForm(
        csrf_enabled=False
    )
    if form.validate_on_submit():
        pkg_names = form.pkg_name.data.split(',')
        pkg_branchs = form.clt_name.data.split(',')
        pkg_owner = form.pkg_owner.data

        try:
            for pkg_name, pkg_branch in itertools.product(
                    pkg_names, pkg_branchs):
                message = pkgdblib.update_pkg_poc(
                    SESSION,
                    pkg_name=pkg_name,
                    clt_name=clt_name,
                    pkg_owner='orphan',
                    user=flask.g.fas_user,
                )
            SESSION.commit()
            output['output'] = 'ok'
            output['messages'] = [message]
        except pkgdblib.PkgdbException, err:
            SESSION.rollback()
            output['output'] = 'notok'
            output['error'] = err
            httpcode = 500
    else:
        output['output'] = 'notok'
        output['error'] = 'Invalid input submitted'
        if form.errors:
            detail = []
            for error in form.errors:
                detail.append('%s: %s' % (error,
                              '; '.join(form.errors[error])))
            output['error_detail'] = detail
        httpcode = 500

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout


@API.route('/package/unorphan/', methods=['POST'])
def api_package_unorphan():
    ''' Unorphan a list of packages.

    :arg packagenames: List of string of the packages name.
    :arg branches: List of string of the branches name in which these
        packages will be unorphaned.
    :arg username: String of the name of the user taking ownership of
        this package. If you are not an admin, this name must be None.

    '''
    httpcode = 200
    output = {}

    form = forms.PackageOwnerForm(
        csrf_enabled=False,
    )
    if form.validate_on_submit():
        pkg_names = form.pkg_name.data.split(',')
        pkg_branchs = form.pkg_branch.data.split(',')
        pkg_owner = form.pkg_owner.data

        try:
            for pkg_name, pkg_branch in itertools.product(
                    pkg_names, pkg_branchs):
                message = pkgdblib.unorphan_package(
                    session=SESSION,
                    pkg_name=pkg_name,
                    clt_name=pkg_branch,
                    pkg_user=pkg_owner,
                    user=flask.g.fas_user
                )
            SESSION.commit()
            output['output'] = 'ok'
            output['messages'] = [message]
        except pkgdblib.PkgdbException, err:
            SESSION.rollback()
            output['output'] = 'notok'
            output['error'] = err
            httpcode = 500
    else:
        output['output'] = 'notok'
        output['error'] = 'Invalid input submitted'
        if form.errors:
            detail = []
            for error in form.errors:
                detail.append('%s: %s' % (error,
                              '; '.join(form.errors[error])))
            output['error_detail'] = detail
        httpcode = 500

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout


@API.route('/package/deprecate/', methods=['POST'])
def api_package_deprecate():
    ''' Deprecate a list of packages.

    :arg packagenames: List of string of the packages name.
    :arg branches: List of string of the branches name in which these
        packages will be deprecated.

    '''
    httpcode = 200
    output = {}

    form = forms.DeprecatePackageForm(csrf_enabled=False)
    if form.validate_on_submit():
        pkg_names = form.pkg_name.data.split(',')
        pkg_branchs = form.clt_name.data.split(',')

        try:
            for pkg_name, pkg_branch in itertools.product(
                    pkg_names, pkg_branchs):
                message = pkgdblib.update_pkg_status(
                    SESSION,
                    pkg_name=pkg_name,
                    clt_name=clt_name,
                    status='Deprecated',
                    user=flask.g.fas_user,
                )
            SESSION.commit()
            output['output'] = 'ok'
            output['messages'] = [message]
        except pkgdblib.PkgdbException, err:
            SESSION.rollback()
            output['output'] = 'notok'
            output['error'] = err
            httpcode = 500
    else:
        output['output'] = 'notok'
        output['error'] = 'Invalid input submitted'
        if form.errors:
            detail = []
            for error in form.errors:
                detail.append('%s: %s' % (error,
                              '; '.join(form.errors[error])))
            output['error_detail'] = detail
        httpcode = 500

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout


@API.route('/package/undeprecate/', methods=['POST'])
def api_package_undeprecate():
    ''' Un-deprecate a list of packages.

    :arg packagenames: List of string of the packages name.
    :arg branches: List of string of the branches name in which these
        packages will be un-deprecated.

    '''
    httpcode = 200
    output = {}

    form = forms.DeprecatePackageForm(csrf_enabled=False)
    if form.validate_on_submit():
        pkg_names = form.pkg_name.data.split(',')
        pkg_branchs = form.clt_name.data.split(',')

        try:
            for pkg_name, pkg_branch in itertools.product(
                    pkg_names, pkg_branchs):
                message = pkgdblib.update_pkg_status(
                    SESSION,
                    pkg_name=pkg_name,
                    clt_name=clt_name,
                    status='Approved',
                    user=flask.g.fas_user,
                )
            SESSION.commit()
            output['output'] = 'ok'
            output['messages'] = [message]
        except pkgdblib.PkgdbException, err:
            SESSION.rollback()
            output['output'] = 'notok'
            output['error'] = err
            httpcode = 500
    else:
        output['output'] = 'notok'
        output['error'] = 'Invalid input submitted'
        if form.errors:
            detail = []
            for error in form.errors:
                detail.append('%s: %s' % (error,
                              '; '.join(form.errors[error])))
            output['error_detail'] = detail
        httpcode = 500

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout


@API.route('/package/list/')
@API.route('/package/list/<pkgname>/')
def api_package_list(pkgname=None):
    ''' List packages.

    :arg packagename: Pattern to list packages from their name.
    :arg branches: List of string of the branches name in which these
        packages will be searched.
    :arg owner: String of the user name to to which restrict the search.
    :arg orphaned: Boolean to retrict the search to orphaned packages.
    :arg deprecated: Boolean to retrict the search to deprecated
        packages.

    '''
    httpcode = 200
    output = {}

    pattern = flask.request.args.get('pgkname', pkgname)
    branches = flask.request.args.get('branches', None)
    owner = flask.request.args.get('owner', None)
    orphaned = bool(flask.request.args.get('orphaned', False))
    deprecated = bool(flask.request.args.get('deprecated', False))

    try:
        packages = pkgdblib.search_package(
            SESSION,
            pkg_name=pattern,
            clt_name=branches,
            pkg_owner=owner,
            orphaned=orphaned,
            deprecated=deprecated,
        )
        SESSION.commit()
        output['output'] = 'ok'
        output['packages'] = [pkg.to_json() for pkg in packages]
    except pkgdblib.PkgdbException, err:
        SESSION.rollback()
        output['output'] = 'notok'
        output['error'] = err
        httpcode = 500

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout
