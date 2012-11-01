from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import transaction
from mock import Mock
from pyramid import testing

from samplesdb.models import DBSession, Base, EmailAddress, User
from samplesdb.scripts.initializedb import init_instances

def setup():
    print('Calling setup')
    from samplesdb import ROUTES
    from sqlalchemy import create_engine
    config = testing.setUp()
    for route_name, route_url in ROUTES.items():
        config.add_route(route_name, route_url)
    engine = create_engine('sqlite://')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)
    init_instances()

def teardown():
    DBSession.remove()
    testing.tearDown()

def test_root_home():
    from samplesdb.views.root import RootView
    from samplesdb.views.account import LoginSchema
    from samplesdb.forms import FormRenderer
    request = testing.DummyRequest()
    handler = RootView(request)
    info = handler.home()
    assert isinstance(info['form'], FormRenderer)
    assert info['form'].form.schema == LoginSchema

def test_root_faq():
    from samplesdb.views.root import RootView
    request = testing.DummyRequest()
    handler = RootView(request)
    info = handler.faq()

def test_account_login():
    from samplesdb.views.account import AccountView, LoginSchema
    from samplesdb.forms import FormRenderer
    request = testing.DummyRequest()
    handler = AccountView(request)
    info = handler.login()
    # TODO Test authenticate is called
    # TODO Test authentication in a functional test?
    # TODO With functional test, ensure remember headers are set
    assert isinstance(info['form'], FormRenderer)
    assert info['form'].form.schema == LoginSchema
    assert info['form'].form.data['came_from'] == 'http://example.com'

def test_account_logout():
    from samplesdb.views.account import AccountView
    from pyramid.httpexceptions import HTTPFound
    request = testing.DummyRequest()
    handler = AccountView(request)
    response = handler.logout()
    assert isinstance(response, HTTPFound)
    assert 'Location' in response.headers

def test_account_index():
    from samplesdb.views.account import AccountView
    request = testing.DummyRequest()
    handler = AccountView(request)
    info = handler.index()

def test_account_create():
    from samplesdb.views.account import AccountView, SignUpSchema
    from samplesdb.forms import FormRenderer
    request = testing.DummyRequest()
    handler = AccountView(request)
    info = handler.create()
    assert isinstance(info['form'], FormRenderer)
    assert info['form'].form.schema == SignUpSchema
    assert len(info['timezones']) > 100
    assert ('UTC', '(UTC+0000) UTC') in info['timezones']

def test_account_verify_email():
    from samplesdb.views.account import AccountView
    from samplesdb.models import EmailVerification
    from pyramid_mailer.mailer import Mailer
    from pyramid_mailer.message import Message
    email = 'example@example.com'
    address = EmailAddress(email=email, user_id=1)
    DBSession.add(address)
    DBSession.flush()
    verifications = DBSession.query(EmailVerification).all()
    assert len(verifications) == 0
    request = testing.DummyRequest()
    request.registry.settings['site_title'] = 'Test'
    mailer = Mock(Mailer)
    request.registry['mailer'] = mailer
    request.matchdict['email'] = email
    handler = AccountView(request)
    info = handler.verify_email()
    assert info['email'] == email
    assert info['timeout']
    verifications = DBSession.query(EmailVerification).all()
    assert len(verifications) == 1
    assert mailer.send.call_count == 1
    assert isinstance(mailer.send.call_args[0][0], Message)
    # Make sure the verification code appears in the email
    assert verifications[0].id in mailer.send.call_args[0][0].body
    transaction.abort()

def test_account_verify_complete():
    from samplesdb.views.account import AccountView
    from samplesdb.models import EmailVerification
    email = 'example@example.com'
    address = EmailAddress(email=email, user_id=1)
    verification = EmailVerification(email)
    DBSession.add(address)
    DBSession.add(verification)
    DBSession.flush()
    verifications = DBSession.query(EmailVerification).all()
    assert len(verifications) == 1
    request = testing.DummyRequest()
    request.matchdict['code'] = verification.id
    handler = AccountView(request)
    info = handler.verify_complete()
    verifications = DBSession.query(EmailVerification).all()
    assert len(verifications) == 0
    assert address.verified
    transaction.abort()

def test_account_verify_cancel():
    from samplesdb.views.account import AccountView
    from samplesdb.models import EmailVerification
    email = 'example@example.com'
    address = EmailAddress(email=email, user_id=1)
    verification = EmailVerification(email)
    DBSession.add(address)
    DBSession.add(verification)
    DBSession.flush()
    verifications = DBSession.query(EmailVerification).all()
    assert len(verifications) == 1
    request = testing.DummyRequest()
    request.matchdict['code'] = verification.id
    handler = AccountView(request)
    info = handler.verify_complete()
    verifications = DBSession.query(EmailVerification).all()
    assert len(verifications) == 0
    assert not address.verified
    transaction.abort()
