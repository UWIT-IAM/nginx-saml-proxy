from flask import Flask, Response, request, session, abort, redirect
import flask
from werkzeug.contrib.fixers import ProxyFix
import uw_saml2
from urllib.parse import urljoin
from datetime import timedelta
import os
import secrets
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
if os.environ.get('SECRET_KEY'):
    app.secret_key = os.environ['SECRET_KEY']
else:
    app.logger.error('Generating burner SECRET_KEY for demo purposes')
    app.secret_key = secrets.token_urlsafe(32)
app.config.update(
    SESSION_COOKIE_NAME='_saml_session',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12)
)


@app.route('/status')
@app.route('/status/group/<group>')
def status(group=None):
    """
    Report current authentication status. Return 401 if not authenticated,
    403 if a group was requested that the user is not a member of, or 200
    if the user is authenticated.

        group - a UW Group the user must be a member of.
    """
    userid = session.get('userid')
    groups = session.get('groups', [])
    if not userid:
        abort(401)
    if group and group not in groups:
        abort(403)
    headers = {'X-Saml-User': userid,
               'X-Saml-Groups': ':'.join(groups)}
    txt = f'Logged in as: {userid}\nGroups: {str(groups)}'
    return Response(txt, status=200, headers=headers)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Return a SAML Request redirect, or process a SAML Response, depending
    on whether GET or POST.
    """
    session.clear()
    args = {
        'entity_id': request.headers['X-Saml-Entity-Id'],
        'acs_url': urljoin(request.url_root, request.headers['X-Saml-Acs'])
    }
    if request.method == 'GET':
        args['return_to'] = request.args.get('url', None)
        return redirect(uw_saml2.login_redirect(**args))

    attributes = uw_saml2.process_response(request.form, **args)

    session['userid'] = attributes['uwnetid']
    session['groups'] = attributes.get('groups', [])
    app.logger.info(attributes)
    relay_state = request.form.get('RelayState')
    if relay_state and relay_state.startswith('/'):
        return redirect(urljoin(request.url_root, request.form['RelayState']))

    return status()


@app.route('/logout')
def logout():
    session.clear()
    return 'Logged out'


@app.route('/')
def healthz():
    """Return a 200 along with some useful links."""
    return '''
    <p><a href="login">Sign in</a></p><p><a href="logout">Logout</a></p>
    '''
