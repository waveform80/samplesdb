from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
import logging

from mock import Mock
from nose.tools import assert_raises
from webob.multidict import MultiDict
from pyramid import testing
from pyramid.httpexceptions import HTTPFound
from pyramid_mailer.mailer import Mailer

from samplesdb.image import can_resize, make_thumbnail
from samplesdb.forms import css_add_class, css_del_class, FormRenderer
from samplesdb.scripts.initializedb import init_instances
from samplesdb.licenses import DummyLicensesFactory
from samplesdb.security import *
from samplesdb.models import *
from samplesdb.views.root import *
from samplesdb.views.account import *
from samplesdb.views.collections import *
from samplesdb.views.samples import *


def test_can_resize():
    assert can_resize('image/png')
    assert can_resize('image/jpeg')
    assert not can_resize('application/octet-stream')
    assert not can_resize('image/svg+xml')
    assert not can_resize('text/html')


def test_image_resize():
    test_img = os.path.join(os.path.dirname(__file__), 'static', 'pyramid.png')
    test_out = os.path.join(os.path.dirname(__file__), 'static', 'test.png')
    assert os.path.exists(test_img)
    if os.path.exists(test_out):
        os.unlink(test_out)
    assert not os.path.exists(test_out)
    make_thumbnail(test_img, test_out)
    assert os.path.exists(test_out)
    os.unlink(test_out)


def test_css_add_class():
    assert css_add_class({}, 'foo') == {'class_': 'foo'}
    assert css_add_class({'class_': 'foo'}, 'foo') == {'class_': 'foo'}
    assert set(css_add_class({'class_': 'foo bar'}, 'baz')['class_'].split()) == set(('foo', 'bar', 'baz'))


def test_css_del_class():
    assert css_del_class({'class_': 'foo'}, 'foo') == {}
    assert css_del_class({'class_': 'foo bar'}, 'foo') == {'class_': 'bar'}
    assert set(css_del_class({'class_': 'foo bar'}, 'baz')['class_'].split()) == set(('foo', 'bar'))


class UnitFixture(object):
    """Fixture for unit-tests"""

    def setup(self):
        from samplesdb import ROUTES
        from sqlalchemy import create_engine
        self.config = testing.setUp()
        self.mailer = Mock(Mailer)
        self.config.registry['mailer'] = self.mailer
        self.config.registry['licenses'] = DummyLicensesFactory()
        self.config.registry.settings['site_title'] = 'TESTING'
        self.config.registry.settings['session.constant_csrf_token'] = '1234'
        for route_name, route_url in ROUTES.items():
            self.config.add_route(route_name, route_url)
        engine = create_engine('sqlite://')
        DBSession.configure(bind=engine)
        Base.metadata.create_all(engine)
        init_instances()

    def teardown(self):
        DBSession.remove()
        testing.tearDown()


class FunctionalFixture(object):
    """Fixture for functional tests"""

    def setup(self):
        import DNS
        from samplesdb import main
        from webtest import TestApp
        settings = {
            'pyramid.includes':            'pyramid_beaker pyramid_mailer pyramid_tm',
            'licenses_cache_dir':          os.environ.get('TEMP', '.'),
            'sqlalchemy.url':              'sqlite://',
            'site_title':                  'TESTING',
            'session.type':                'memory',
            'session.key':                 'samplesdb',
            'session.secret':              'test',
            'session.constant_csrf_token': '1234',
            'testing':                     '1',
            }
        self.test = TestApp(main(None, **settings))
        Base.metadata.create_all(self.test.app.engine)
        init_instances()
        self.mailer = Mock(Mailer)
        self.test.app.registry['mailer'] = self.mailer
        DNS.DnsRequest = Mock(DNS.DnsRequest)

    def teardown(self):
        DBSession.remove()


class RootViewUnitTests(UnitFixture):
    def make_one(self):
        request = testing.DummyRequest()
        request.POST = MultiDict()
        request.user = Mock()
        request.referer = request.url
        view = RootView(request)
        return view

    def test_root_home(self):
        view = self.make_one()
        result = view.home()
        assert isinstance(result['form'], FormRenderer)
        assert result['form'].form.schema == LoginSchema

    def test_root_faq(self):
        view = self.make_one()
        result = view.faq()


class AccountViewUnitTests(UnitFixture):
    def make_one(self):
        request = testing.DummyRequest()
        request.POST = MultiDict()
        request.user = Mock()
        request.referer = request.url
        view = AccountView(request)
        return view

    def test_account_login_form(self):
        view = self.make_one()
        result = view.login()
        assert 'form' in result
        assert isinstance(result['form'], FormRenderer)
        assert result['form'].form.schema == LoginSchema
        assert result['form'].form.came_from == 'http://example.com'

    def test_account_login_redirect(self):
        view = self.make_one()
        view.request.url = 'http://example.com/login'
        result = view.login()
        assert 'form' in result
        assert result['form'].form.came_from != 'http://example.com/login'

    def test_account_login_bad(self):
        view = self.make_one()
        view.request.method = 'POST'
        view.request.POST['_came_from'] = 'http://example.com/foo'
        view.request.POST['username'] = 'admin@example.com'
        view.request.POST['password'] = 'badpass'
        view.request.POST['submit'] = 'Submit'
        result = view.login()
        assert 'form' in result
        assert isinstance(result['form'], FormRenderer)
        assert view.request.session.peek_flash() == ['Invalid login']

    def test_account_login_good(self):
        view = self.make_one()
        view.request.method = 'POST'
        view.request.POST['_came_from'] = 'http://example.com/foo'
        view.request.POST['username'] = 'admin@example.com'
        view.request.POST['password'] = 'adminpass'
        view.request.POST['submit'] = 'Submit'
        result = view.login()
        assert isinstance(result, HTTPFound)
        assert result.headers['Location'] == 'http://example.com/foo'

    def test_account_logout(self):
        view = self.make_one()
        result = view.logout()
        assert isinstance(result, HTTPFound)
        assert 'Location' in result.headers

    def test_account_index(self):
        import pytz
        view = self.make_one()
        result = view.index()
        # Just make sure there are plenty of timezones listed by default and
        # that UTC is one of them
        assert len(view.timezones) > 100
        assert ('UTC', '(UTC+0000) UTC') in view.timezones

    def test_account_create(self):
        view = self.make_one()
        result = view.create()
        assert 'form' in result
        assert isinstance(result['form'], FormRenderer)
        assert result['form'].form.schema == AccountCreateSchema

    def test_account_create_bad(self):
        view = self.make_one()
        view.request.method = 'POST'
        view.request.POST['email'] = 'foo@foo.com'
        view.request.POST['email_confirm'] = view.request.POST['email']
        view.request.POST['password'] = 'foo'
        view.request.POST['password_confirm'] = 'bar'
        view.request.POST['salutation'] = 'Mr.'
        view.request.POST['given_name'] = 'Foo'
        view.request.POST['surname'] = ''
        view.request.POST['organization'] = 'Baz University'
        view.request.POST['limits'] = 'academic'
        view.request.POST['timezone_name'] = 'UTC'
        view.request.POST['_came_from'] = view.request.referer
        result = view.create()
        assert 'form' in result
        assert isinstance(result['form'], FormRenderer)
        assert 'password_confirm' in result['form'].form.errors
        assert 'surname' in result['form'].form.errors

    def test_account_create_good(self):
        view = self.make_one()
        view.request.method = 'POST'
        view.request.POST['email'] = 'foo@foo.com'
        view.request.POST['email_confirm'] = view.request.POST['email']
        view.request.POST['password'] = 'foo'
        view.request.POST['password_confirm'] = view.request.POST['password']
        view.request.POST['salutation'] = 'Mr.'
        view.request.POST['given_name'] = 'Foo'
        view.request.POST['surname'] = 'Bar'
        view.request.POST['organization'] = 'Baz University'
        view.request.POST['limits'] = 'free'
        view.request.POST['timezone_name'] = 'UTC'
        view.request.POST['_came_from'] = view.request.referer
        result = view.create()
        assert isinstance(result, HTTPFound)
        assert 'Location' in result.headers

    def test_account_edit(self):
        view = self.make_one()
        result = view.edit()
        assert 'form' in result
        assert isinstance(result['form'], FormRenderer)
        assert result['form'].form.schema == AccountEditSchema

    def test_account_edit_bad(self):
        view = self.make_one()
        view.request.method = 'POST'
        view.request.POST['salutation'] = 'Mr.'
        view.request.POST['given_name'] = 'Foo'
        view.request.POST['surname'] = ''
        view.request.POST['organization'] = 'Baz University'
        view.request.POST['timezone_name'] = 'UTC'
        view.request.POST['password_new'] = ''
        view.request.POST['password_new_confirm'] = ''
        result = view.edit()
        assert 'form' in result
        assert isinstance(result['form'], FormRenderer)
        assert 'surname' in result['form'].form.errors

    def test_account_edit_good(self):
        view = self.make_one()
        view.request.user.password = 'foo'
        view.request.method = 'POST'
        view.request.POST['salutation'] = 'Mr.'
        view.request.POST['given_name'] = 'Foo'
        view.request.POST['surname'] = 'Baz'
        view.request.POST['organization'] = 'Baz University'
        view.request.POST['timezone_name'] = 'UTC'
        view.request.POST['password_new'] = ''
        view.request.POST['password_new_confirm'] = ''
        view.request.POST['_came_from'] = view.request.referer
        result = view.edit()
        assert isinstance(result, HTTPFound)
        assert 'Location' in result.headers
        assert view.request.user.surname == 'Baz'
        # Ensure password is unchanged
        assert view.request.user.password == 'foo'

    def test_account_change_pass(self):
        view = self.make_one()
        view.request.method = 'POST'
        view.request.POST['salutation'] = 'Mr.'
        view.request.POST['given_name'] = 'Foo'
        view.request.POST['surname'] = 'Baz'
        view.request.POST['organization'] = 'Baz University'
        view.request.POST['timezone_name'] = 'UTC'
        view.request.POST['password_new'] = 'bar'
        view.request.POST['password_new_confirm'] = 'bar'
        view.request.POST['_came_from'] = view.request.referer
        result = view.edit()
        assert isinstance(result, HTTPFound)
        assert 'Location' in result.headers
        assert view.request.user.password == 'bar'

    def test_account_verify_email(self):
        email = 'example@example.com'
        address = EmailAddress(email=email, user_id=1)
        DBSession.add(address)
        DBSession.flush()
        view = self.make_one()
        view.request.GET['email'] = email
        result = view.verify_email()
        assert 'verification' in result
        assert result['verification'].email.email == email

    def test_account_verify_too_fast(self):
        email = 'example@example.com'
        address = EmailAddress(email=email, user_id=1)
        DBSession.add(address)
        DBSession.flush()
        # First verification attempt
        view = self.make_one()
        view.request.GET['email'] = email
        view.verify_email()
        # Make another one too quickly
        view = self.make_one()
        view.request.GET['email'] = email
        assert_raises(VerificationTooFast, view.verify_email)

    def test_account_verify_too_many(self):
        from datetime import datetime, timedelta
        email = 'example@example.com'
        address = EmailAddress(email=email, user_id=1)
        DBSession.add(address)
        DBSession.flush()
        # First verification attempt
        for i in range(VERIFICATION_LIMIT):
            view = self.make_one()
            view.request.GET['email'] = email
            view.verify_email()
            # Re-write the new verification record to make it appear old in
            # order to allow us to create a new one
            new_created = datetime.utcnow() - timedelta(seconds=VERIFICATION_INTERVAL)
            verification = DBSession.query(EmailVerification).\
                filter(EmailVerification.email_ref == email).\
                filter(EmailVerification.created > new_created).one()
            verification.created = new_created - timedelta(seconds=1)
            DBSession.flush()
        view = self.make_one()
        view.request.GET['email'] = email
        assert_raises(VerificationTooMany, view.verify_email)

    def test_account_verify_complete(self):
        email = 'example@example.com'
        address = EmailAddress(email=email, user_id=1)
        verification = EmailVerification(email)
        DBSession.add(address)
        DBSession.add(verification)
        DBSession.flush()
        view = self.make_one()
        view.request.matchdict['code'] = verification.id
        result = view.verify_complete()
        assert 'verification' in result
        assert result['verification'].email.email == email

    def test_account_verify_bad(self):
        from pyramid.httpexceptions import HTTPNotFound
        view = self.make_one()
        view.request.matchdict['code'] = 'foo'
        assert_raises(HTTPNotFound, view.verify_complete)


class CollectionsViewUnitTests(UnitFixture):
    def make_one(self, collection_id=None):
        request = testing.DummyRequest()
        request.POST = MultiDict()
        request.user = User.by_email('admin@example.com')
        request.referer = request.url
        if collection_id is not None:
            request.matchdict['collection_id'] = collection_id
            context = CollectionContextFactory(request)
        else:
            context = RootContextFactory(request)
        view = CollectionsView(context, request)
        return view

    def test_collections_index(self):
        view = self.make_one()
        result = view.index()
        # XXX Nothing to test here?

    def test_collections_create(self):
        view = self.make_one()
        result = view.create()
        assert 'form' in result
        assert isinstance(result['form'], FormRenderer)
        assert result['form'].form.schema == CollectionCreateSchema

    def test_collections_create_bad(self):
        view = self.make_one()
        view.request.method = 'POST'
        view.request.POST['name'] = 'New Collection'
        view.request.POST['license'] = 'notspecified'
        view.request.POST['users-0.user'] = 'i-dont-exist@nowhere.org'
        view.request.POST['users-0.role'] = 'owner'
        result = view.create()
        assert 'form' in result
        assert isinstance(result['form'], FormRenderer)
        assert 'users-0.user' in result['form'].form.errors
        assert 'name' not in result['form'].form.errors
        assert 'owner' in result['form'].form.errors

    def test_collections_create_good(self):
        view = self.make_one()
        view.request.method = 'POST'
        view.request.POST['name'] = 'New Collection'
        view.request.POST['owner'] = 'Mr. Foo'
        view.request.POST['license'] = 'notspecified'
        view.request.POST['_came_from'] = view.request.referer
        result = view.create()
        assert isinstance(result, HTTPFound)
        assert 'Location' in result.headers
        assert DBSession.query(Collection).join(UserCollection).\
                filter(UserCollection.user_id==view.request.user.id).\
                filter(Collection.name=='New Collection').first()

    def test_collections_view(self):
        view = self.make_one(1)
        result = view.view()
        assert 'filter' in result
        assert result['filter'] in ('all', 'existing', 'destroyed')
        assert 'display' in result
        assert result['display'] in ('grid', 'table')
        assert 'samples' in result


class SiteFunctionalTest(FunctionalFixture):
    def last_verify_url(self):
        # Returns the last verification URL "sent" to a user
        url = None
        for line in self.mailer.send.call_args[0][0].body.splitlines():
            if line.startswith('http:'):
                url = line
                break
        return url

    def sub_login(self, username, password):
        res = self.test.get('/login')
        assert 'Login' in res
        res.form['username'] = username
        res.form['password'] = password
        return res.form.submit()

    def sub_create(self, salutation, given_name, surname, organization,
            limits, email, email_confirm, password, password_confirm):
        res = self.test.get('/signup')
        res.form['salutation'] = salutation
        res.form['given_name'] = given_name
        res.form['surname'] = surname
        res.form['organization'] = organization
        res.form['limits'] = limits
        res.form['email'] = email
        res.form['email_confirm'] = email_confirm
        res.form['password'] = password
        res.form['password_confirm'] = password_confirm
        return res.form.submit()

    def sub_make_user(self, name):
        self.sub_create(
            salutation='Mr.',
            given_name='Dave',
            surname=name.title(),
            organization='University of Quux',
            limits='academic',
            email='%s@quux.edu' % name,
            email_confirm='%s@quux.edu' % name,
            password=name,
            password_confirm=name,
            ).follow()
        self.test.get(self.last_verify_url())

    def sub_get_user(self, name):
        return User.by_email('%s@quux.edu' % name)

    def sub_login_user(self, name):
        return self.sub_login('%s@quux.edu' % name, name).follow()

    def sub_logout_user(self):
        return self.test.get('/logout').follow()

    def test_root(self):
        # Retrieve the root page and test we can get to the FAQ
        res = self.test.get('/')
        res.click(href='/faq')

    def test_csrf(self):
        res = self.test.get('/login')
        assert 'Login' in res
        res.form['username'] = 'admin@example.com'
        res.form['password'] = 'adminpass'
        res.form['_csrf'] = 'foo'
        # XXX Why isn't this failing with HTTPForbidden?!
        res = res.form.submit()

    def test_login_bad(self):
        res = self.sub_login('foo@bar.org', 'baz')
        assert 'Invalid login' in res

    def test_login_good(self):
        return self.sub_login('admin@example.com', 'adminpass').follow()

    def test_logout(self):
        self.test_login_good()
        return self.test.get('/logout').follow()

    def test_account_create_bad(self):
        res = self.sub_create(
            salutation='Mr.',
            given_name='Dave',
            surname='Foo',
            organization='University of Quux',
            limits='academic',
            email='foo@quux.edu',
            email_confirm='foo@quux.edu',
            password='quux',
            password_confirm='foo',
            )
        assert 'Fields do not match' in res

    def test_account_create_good(self):
        from pyramid_mailer.message import Message
        import DNS
        res = self.sub_create(
            salutation='Mr.',
            given_name='Dave',
            surname='Foo',
            organization='University of Quux',
            limits='academic',
            email='foo@quux.edu',
            email_confirm='foo@quux.edu',
            password='quux',
            password_confirm='quux',
            )
        # Check a DNS request was attempted
        assert DNS.DnsRequest.called # XXX check quux.edu in call args
        res = res.follow()
        assert 'Verification Sent' in res
        # Check for the verification request in the database
        verifications = DBSession.query(EmailVerification).all()
        assert len(verifications) == 1
        assert self.mailer.send.call_count == 1
        assert isinstance(self.mailer.send.call_args[0][0], Message)
        # Make sure the verification code appears in the email
        assert verifications[0].id in self.mailer.send.call_args[0][0].body

    def test_account_verify_bad(self):
        self.test_account_create_good()
        url = self.last_verify_url()
        # Test a deliberately corrupted verification URL
        res = self.test.get(url + 'foo', status=404)

    def test_account_verify_good(self):
        self.test_account_create_good()
        url = self.last_verify_url()
        # Test the correct verification URL
        res = self.test.get(url)
        verifications = DBSession.query(EmailVerification).all()
        assert len(verifications) == 0
        address = EmailAddress.by_email('foo@quux.edu')
        assert address.verified
        # Login with the newly verified account from the confirmation page
        res = self.sub_login('foo@quux.edu', 'quux')
        res = res.follow()
        assert 'My Collections' in res

    def test_account_edit(self):
        self.test_account_verify_good()
        # Attempt to change given name
        res = self.test.get('/account/edit')
        res.form['given_name'] = 'Adrian'
        res = res.form.submit()
        res = res.follow()
        user = User.by_email('foo@quux.edu')
        # Assert change affected given name and nothing else
        assert user.salutation == 'Mr.'
        assert user.given_name == 'Adrian'
        assert user.surname == 'Foo'
        assert user.organization == 'University of Quux'
        assert user.limits_id == 'academic'
        # Ensure the edit didn't change our password
        res.click(href='/logout').follow()
        self.sub_login('foo@quux.edu', 'quux').follow()
        # Attempt to change password
        res = self.test.get('/account/edit')
        assert 'Edit Account' in res
        res.form['password_new'] = 'foo'
        res.form['password_new_confirm'] = 'foo'
        res = res.form.submit().follow()
        # Check the change worked
        res.click(href='/logout').follow()
        self.sub_login('foo@quux.edu', 'foo').follow()

    def test_collection_create(self):
        self.test_login_good()
        res = self.test.get('/collections/new')
        res.form['name'] = 'Foo'
        res = res.form.submit().follow()
        collection = DBSession.query(Collection).filter(Collection.name=='Foo').first()
        assert collection is not None
        assert 'Foo Collection' in res
        return res

    def test_collection_create_shared(self):
        from webtest import Text
        self.sub_make_user('foo')
        self.sub_make_user('bar')
        self.sub_login_user('foo')
        res = self.test.get('/collections/new')
        res.form['name'] = 'FooBar'
        res.form.fields.setdefault('users-0.user', []).append(
            Text(res.form, tag='input', name='users-0.user', pos=0))
        res.form.fields.setdefault('users-0.role', []).append(
            Text(res.form, tag='input', name='users-0.role', pos=0))
        res.form['users-0.user'] = 'bar@quux.edu'
        res.form['users-0.role'] = 'editor'
        res = res.form.submit()
        res = res.follow()
        collection = DBSession.query(Collection).filter(Collection.name=='FooBar').first()
        assert collection is not None
        foo = self.sub_get_user('foo')
        bar = self.sub_get_user('bar')
        assert foo in collection.users
        assert bar in collection.users
        assert collection.users[foo] == Role.by_id('owner')
        assert collection.users[bar] == Role.by_id('editor')
        assert 'FooBar Collection' in res
        return res

    def test_collection_edit(self):
        from webtest import Text
        self.test_collection_create_shared()
        self.sub_logout()
        self.sub_make_user('baz')
        self.sub_login_user('foo')
        # Edit the collection, rename it, and add in Mr. Baz as a viewer
        res = res.click('Edit Collection')
        res.form['name'] = 'FooBarBaz'
        res.form.fields.setdefault('users-2.user', []).append(
            Text(res.form, tag='input', name='users-2.user', pos=0))
        res.form.fields.setdefault('users-2.role', []).append(
            Text(res.form, tag='input', name='users-2.role', pos=0))
        res.form['users-2.user'] = 'baz@quux.edu'
        res.form['users-2.role'] = 'viewer'
        res = res.form.submit()
        res = res.follow()
        collection = DBSession.query(Collection).filter(Collection.name=='FooBarBaz').first()
        assert collection is not None
        foo = self.sub_get_user('foo')
        bar = self.sub_get_user('bar')
        baz = self.sub_get_user('baz')
        assert foo in collection.users
        assert bar in collection.users
        assert baz in collection.users
        assert collection.users[foo] == Role.by_id('owner')
        assert collection.users[bar] == Role.by_id('editor')
        assert collection.users[baz] == Role.by_id('viewer')
        assert 'FooBarBaz Collection' in res
        return res

