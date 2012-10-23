from __future__ import (
    unicode_literals,
    print_function,
    absolute_import,
    division,
    )

import os
import sys
import transaction
from datetime import datetime

from sqlalchemy import engine_from_config
from pyramid.paster import get_appsettings, setup_logging

from samplesdb.models import (
    DBSession,
    EmailAddress,
    User,
    UserLimit,
    Group,
    Permission,
    Collection,
    Role,
    Base,
    )

def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri>\n'
          '(example: "%s development.ini")' % (cmd, cmd)) 
    sys.exit(1)

def main(argv=sys.argv):
    if len(argv) != 2:
        usage(argv)
    config_uri = argv[1]
    setup_logging(config_uri)
    settings = get_appsettings(config_uri)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.create_all(engine)
    import pdb; pdb.set_trace()
    with transaction.manager:
        admin_perm = Permission(
            id='admin', description='Administration authority')
        admins_group = Group(
            id='admins', description='Group of administrators')
        unlimited_limit = UserLimit(
            id='unlimited', collections_limit=1000000, samples_limit=1000000)
        academic_limit = UserLimit(
            id='academic', collections_limit=10, samples_limit=10000)
        admin_user = User(name='Administrator', limits_id='unlimited')
        admin_email = EmailAddress(
            email='admin@example.com', validated=datetime.utcnow())
        admin_collection = Collection(name='Default')
        admin_perm.groups.append(admins_group)
        admins_group.users.append(admin_user)
        admin_user.emails.append(admin_email)
        admin_user.password = 'adminpass'
        # Create administrator default collection
        # Create "academic" limit
        # Create "commercial" limit
        # Create "owner" role
        # Create "editor" role
        # Create "auditor" role
        # Create "viewer" role
        pass
