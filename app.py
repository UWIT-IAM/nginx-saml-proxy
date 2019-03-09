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

    group - a UW Group the user must be a member of. An SP must be registered
        to receive that group.
    """
    userid = session.get('userid')
    groups = session.get('groups', [])
    if not userid:
        abort(401)
    if group and group not in groups:
        message = f"{userid} not a member of {group} or SP can't receive it"
        app.logger.error(message)
        abort(403)
    headers = {'X-Saml-User': userid,
               'X-Saml-Groups': ':'.join(groups)}
    txt = f'Logged in as: {userid}\nGroups: {str(groups)}'
    return Response(txt, status=200, headers=headers)


def _saml_args():
    """Get entity_id and acs_url from request.headers."""
    return {
        'entity_id': request.headers['X-Saml-Entity-Id'],
        'acs_url': urljoin(request.url_root, request.headers['X-Saml-Acs'])
    }


@app.route('/login/')
@app.route('/login/<path:return_to>')
def login_redirect(return_to=''):
    """
    Redirect to the IdP for SAML initiation.
    
    return_to - the path to redirect back to after authentication. This and
        the request.query_string are set on the SAML RelayState.
    """
    query_string = '?' + request.query_string.decode()
    if query_string == '?':
        query_string = ''
    return_to = f'/{return_to}{query_string}'
    args = _saml_args()
    return redirect(uw_saml2.login_redirect(return_to=return_to, **args))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Process a SAML Response, and set the uwnetid and groups on the session.
    """
    session.clear()
    if request.method == 'GET':
        return login_redirect()

    args = _saml_args()
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
    <p><a href="login">Sign in</a></p>
    <p><a href="status">Status</a></p>
    <p><a href="logout">Logout</a></p>
    '''
