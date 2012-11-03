from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import transaction
from mock import Mock
from nose.tools import assert_raises
from pyramid import testing
from pyramid_mailer.mailer import Mailer

from samplesdb.models import DBSession, Base
from samplesdb.scripts.initializedb import init_instances


class UnitFixture(object):
    """Fixture for unit-tests"""

    def setup(self):
        from samplesdb import ROUTES
        from sqlalchemy import create_engine
        self.config = testing.setUp()
        self.mailer = Mock(Mailer)
        self.config.registry['mailer'] = self.mailer
        self.config.registry.settings['site_title'] = 'TESTING'
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
        from samplesdb import main
        from webtest import TestApp
        settings = {
            'sqlalchemy.url':              'sqlite://',
            'site_title':                  'TESTING',
            'session.type':                'memory',
            'session.constant_csrf_token': '1234567890',
            'testing':                     '1',
            }
        self.test = TestApp(main(None, **settings))
        Base.metadata.create_all(self.test.app.engine)
        init_instances()
        self.test.app.registry['mailer'] = Mock(Mailer)

    def teardown(self):
        DBSession.remove()


class RootViewUnitTests(UnitFixture):
    def make_one(self):
        from samplesdb.views.root import RootView
        request = testing.DummyRequest()
        view = RootView(request)
        return view

    def test_root_home(self):
        from samplesdb.views.account import LoginSchema
        from samplesdb.forms import FormRenderer
        view = self.make_one()
        result = view.home()
        assert isinstance(result['form'], FormRenderer)
        assert result['form'].form.schema == LoginSchema

    def test_root_faq(self):
        view = self.make_one()
        result = view.faq()


class RootViewFunctionalTests(FunctionalFixture):
    def test(self):
        res = self.test.get('/')
        # XXX Fill out login form badly
        # XXX Fill out login form properly
        res = self.test.get('/faq')



class AccountViewUnitTests(UnitFixture):
    def make_one(self):
        from samplesdb.views.account import AccountView
        request = testing.DummyRequest()
        view = AccountView(request)
        return view
    
    def test_account_login_form(self):
        from samplesdb.views.account import LoginSchema
        from samplesdb.forms import FormRenderer
        view = self.make_one()
        result = view.login()
        assert isinstance(result['form'], FormRenderer)
        assert result['form'].form.schema == LoginSchema
        assert result['form'].form.data['came_from'] == 'http://example.com'

    def test_account_login_redirect(self):
        from samplesdb.views.account import LoginSchema
        from samplesdb.forms import FormRenderer
        view = self.make_one()
        view.request.url = 'http://example.com/login'
        result = view.login()
        assert result['form'].form.data['came_from'] == 'http://example.com/collections'

    def test_account_logout(self):
        from pyramid.httpexceptions import HTTPFound
        view = self.make_one()
        result = view.logout()
        assert isinstance(result, HTTPFound)
        assert 'Location' in result.headers

    def test_account_index(self):
        view = self.make_one()
        result = view.index()

    def test_account_create(self):
        from samplesdb.views.account import AccountCreateSchema
        from samplesdb.forms import FormRenderer
        view = self.make_one()
        result = view.create()
        assert isinstance(result['form'], FormRenderer)
        assert result['form'].form.schema == AccountCreateSchema
        assert len(result['timezones']) > 100
        assert ('UTC', '(UTC+0000) UTC') in result['timezones']

    def test_account_verify_email(self):
        from samplesdb.models import EmailAddress
        email = 'example@example.com'
        address = EmailAddress(email=email, user_id=1)
        DBSession.add(address)
        DBSession.flush()
        view = self.make_one()
        view.request.matchdict['email'] = email
        result = view.verify_email()
        assert result['verification'].email.email == email

    def test_account_verify_too_fast(self):
        from samplesdb.models import EmailAddress, VerificationTooFast
        email = 'example@example.com'
        address = EmailAddress(email=email, user_id=1)
        DBSession.add(address)
        DBSession.flush()
        # First verification attempt
        view = self.make_one()
        view.request.matchdict['email'] = email
        view.verify_email()
        # Make another one too quickly
        view = self.make_one()
        view.request.matchdict['email'] = email
        assert_raises(VerificationTooFast, view.verify_email)

    def test_account_verify_too_many(self):
        from datetime import datetime, timedelta
        from samplesdb.models import (
            EmailAddress,
            EmailVerification,
            VerificationTooMany,
            VERIFICATION_LIMIT,
            VERIFICATION_INTERVAL,
            )
        email = 'example@example.com'
        address = EmailAddress(email=email, user_id=1)
        DBSession.add(address)
        DBSession.flush()
        # First verification attempt
        for i in range(VERIFICATION_LIMIT):
            view = self.make_one()
            view.request.matchdict['email'] = email
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
        view.request.matchdict['email'] = email
        assert_raises(VerificationTooMany, view.verify_email)

    def test_account_verify_complete(self):
        from samplesdb.models import EmailAddress, EmailVerification
        email = 'example@example.com'
        address = EmailAddress(email=email, user_id=1)
        verification = EmailVerification(email)
        DBSession.add(address)
        DBSession.add(verification)
        DBSession.flush()
        view = self.make_one()
        view.request.matchdict['code'] = verification.id
        result = view.verify_complete()
        assert result['verification'].email.email == email

    def test_account_verify_bad(self):
        from pyramid.httpexceptions import HTTPNotFound
        view = self.make_one()
        view.request.matchdict['code'] = 'foo'
        assert_raises(HTTPNotFound, view.verify_complete)


class AccountViewFunctionalTests(FunctionalFixture):
    def test(self):
        from pyramid_mailer.message import Message
        #verifications = DBSession.query(EmailVerification).all()
        #assert len(verifications) == 0
        res = self.test.get('/signup')
        # XXX Fill out sign-up form badly (assert errors)
        # XXX Fill out sign-up form properly
        # XXX Test verification is created
        #verifications = DBSession.query(EmailVerification).all()
        #assert len(verifications) == 1
        #assert self.mailer.send.call_count == 1
        #assert isinstance(self.mailer.send.call_args[0][0], Message)
        # Make sure the verification code appears in the email
        #assert verifications[0].id in self.mailer.send.call_args[0][0].body
        # XXX Call bad verification URL (assert 404)
        # XXX Call correct verification URL
        #verifications = DBSession.query(EmailVerification).all()
        #assert len(verifications) == 0
        #assert address.verified
