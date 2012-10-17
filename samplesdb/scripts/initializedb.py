import os
import sys
import transaction

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
    )

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
    with transaction.manager:
        # Create admin permission
        # Create administrators group
        # Create administrator user
        # Create administrator email-address
        # Create administrator default collection
        # Create "unlimited" limit
        # Create "academic" limit
        # Create "commercial" limit
        # Create "owner" role
        # Create "editor" role
        # Create "auditor" role
        # Create "viewer" role
        pass
