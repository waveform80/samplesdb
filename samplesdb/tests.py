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
from pyramid import testing
from pyramid.httpexceptions import HTTPFound
from pyramid_mailer.mailer import Mailer

from samplesdb.image import can_resize, make_thumbnail
from samplesdb.forms import css_add_class, css_del_class, FormRenderer
from samplesdb.scripts.initializedb import init_instances
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
        view.request.POST['limits_id'] = 'academic'
        view.request.POST['timezone_name'] = 'UTC'
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
        view.request.POST['limits_id'] = 'academic'
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
        view.request.POST['users-0.user'] = 'i-dont-exist@nowhere.org'
        view.request.POST['users-0.role'] = 'owner'
        result = view.create()
        assert 'form' in result
        assert isinstance(result['form'], FormRenderer)
        assert 'users-0.user' in result['form'].form.errors
        assert 'name' not in result['form'].form.errors

    def test_collections_create_good(self):
        view = self.make_one()
        view.request.method = 'POST'
        view.request.POST['name'] = 'New Collection'
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
    def test(self):
        from webtest import Text
        from pyramid_mailer.message import Message
        import DNS
        # Visit the home page and FAQ
        res = self.test.get('/')
        res = res.click(href='/faq')
        # Attempt to login with bogus credentials
        res = res.click(href='/login')
        assert 'Login' in res
        res.form['username'] = 'foo@bar.org'
        res.form['password'] = 'baz'
        res = res.form.submit()
        assert 'Invalid login' in res
        # Attempt to login with the built-in admin account
        res.form['username'] = 'admin@example.com'
        res.form['password'] = 'adminpass'
        save_csrf = res.form['_csrf'].value
        res.form['_csrf'] = 'foo'
        # XXX Why isn't this failing with HTTPForbidden?!
        new_res = res.form.submit()
        res.form['_csrf'] = save_csrf
        res = res.form.submit()
        res = res.follow()
        assert 'My Collections' in res
        # Visit the account page
        res = res.click(href='/account')
        assert 'My Account' in res
        # Attempt to logout
        res = res.click(href='/logout')
        res = res.follow()
        # Go to the sign-up page and create a new account
        res = res.click(href='/signup')
        res.form['salutation'] = 'Mr.'
        res.form['given_name'] = 'Dave'
        res.form['surname'] = 'Foo'
        res.form['organization'] = 'University of Quux'
        res.form['limits_id'] = 'academic'
        res.form['email'] = 'foo@quux.edu'
        res.form['email_confirm'] = 'foo@quux.edu'
        res.form['password'] = 'quux'
        # ... with an incorrect password confirmation
        res.form['password_confirm'] = 'foo'
        res = res.form.submit()
        assert DNS.DnsRequest.called # XXX check manchester.ac.uk in call args
        assert 'Fields do not match' in res
        # ... correct the password and make sure an e-mail verification is sent
        res.form['password_confirm'] = 'quux'
        res = res.form.submit()
        res = res.follow()
        assert 'Verification Sent' in res
        verifications = DBSession.query(EmailVerification).all()
        assert len(verifications) == 1
        assert self.mailer.send.call_count == 1
        assert isinstance(self.mailer.send.call_args[0][0], Message)
        # Make sure the verification code appears in the email
        assert verifications[0].id in self.mailer.send.call_args[0][0].body
        url = None
        for line in self.mailer.send.call_args[0][0].body.splitlines():
            if line.startswith('http:'):
                url = line
                break
        assert url
        # Test a deliberately corrupted verification URL
        res = self.test.get(url + 'foo', status=404)
        res = self.test.get(url)
        verifications = DBSession.query(EmailVerification).all()
        assert len(verifications) == 0
        address = EmailAddress.by_email('foo@quux.edu')
        assert address.verified
        # Login with the newly verified account from the confirmation page
        res = res.click(href='/login', index=1)
        assert 'Login' in res
        res.form['username'] = 'foo@quux.edu'
        res.form['password'] = 'quux'
        res = res.form.submit()
        res = res.follow()
        assert 'My Collections' in res
        res = res.click(href='/account')
        assert 'My Account' in res
        # Attempt to change surname
        res = res.click(href='/account/edit')
        res.form['given_name'] = 'Adrian'
        res = res.form.submit()
        res = res.follow()
        assert User.by_email('foo@quux.edu').given_name == 'Adrian'
        # Ensure the edit didn't change our password
        res = res.click(href='/logout')
        res = res.follow()
        assert 'Home' in res
        res.form['username'] = 'foo@quux.edu'
        res.form['password'] = 'quux'
        res = res.form.submit()
        res = res.follow()
        assert 'My Collections' in res
        res = res.click(href='/account')
        assert 'My Account' in res
        # Attempt to change password
        res = res.click(href='/account/edit')
        assert 'Edit Account' in res
        res.form['password_new'] = 'foo'
        res.form['password_new_confirm'] = 'foo'
        res = res.form.submit()
        res = res.follow()
        # Check the change worked
        res = res.click(href='/logout')
        res = res.follow()
        assert 'Home' in res
        res.form['username'] = 'foo@quux.edu'
        res.form['password'] = 'foo'
        res = res.form.submit()
        res = res.follow()
        assert 'Login' not in res
        # Logout and create two new uesrs: Mr. Bar and Mr. Baz
        res = res.click(href='/logout')
        res = res.follow()
        res = self.test.get('/signup')
        res.form['salutation'] = 'Mr.'
        res.form['given_name'] = 'Dave'
        res.form['surname'] = 'Bar'
        res.form['organization'] = 'University of Quux'
        res.form['limits_id'] = 'academic'
        res.form['email'] = 'bar@quux.edu'
        res.form['email_confirm'] = 'bar@quux.edu'
        res.form['password'] = 'bar'
        res.form['password_confirm'] = 'bar'
        res = res.form.submit()
        res = res.follow()
        url = None
        for line in self.mailer.send.call_args[0][0].body.splitlines():
            if line.startswith('http:'):
                url = line
                break
        res = self.test.get(url)
        res = self.test.get('/signup')
        res.form['salutation'] = 'Mr.'
        res.form['given_name'] = 'Dave'
        res.form['surname'] = 'Baz'
        res.form['organization'] = 'University of Quux'
        res.form['limits_id'] = 'academic'
        res.form['email'] = 'baz@quux.edu'
        res.form['email_confirm'] = 'baz@quux.edu'
        res.form['password'] = 'baz'
        res.form['password_confirm'] = 'baz'
        res = res.form.submit()
        res = res.follow()
        url = None
        for line in self.mailer.send.call_args[0][0].body.splitlines():
            if line.startswith('http:'):
                url = line
                break
        res = self.test.get(url)
        res = res.click(href='/login', index=1)
        # Login as Mr. Foo again
        res.form['username'] = 'foo@quux.edu'
        res.form['password'] = 'foo'
        res = res.form.submit()
        res = res.follow()
        # Create a new collection
        res = res.click(href='/collections/new')
        res.form['name'] = 'Foo'
        res = res.form.submit()
        res = res.follow()
        collection = DBSession.query(Collection).filter(Collection.name=='Foo').first()
        assert collection is not None
        assert 'Foo Collection' in res
        # Go back to My Collections and create a new collection, this time
        # shared with Mr. Bar
        res = res.click('My Collections')
        res = res.click('New Collection')
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
        assert collection.users[User.by_email('foo@quux.edu')] == Role.by_id('owner')
        assert collection.users[User.by_email('bar@quux.edu')] == Role.by_id('editor')
        assert 'FooBar Collection' in res
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
        assert collection.users[User.by_email('foo@quux.edu')] == Role.by_id('owner')
        assert collection.users[User.by_email('bar@quux.edu')] == Role.by_id('editor')
        assert collection.users[User.by_email('baz@quux.edu')] == Role.by_id('viewer')
        assert 'FooBarBaz Collection' in res
