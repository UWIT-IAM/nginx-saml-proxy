from flask import Flask, Response, request, session, abort, redirect
import flask
from werkzeug.middleware.proxy_fix import ProxyFix
import uw_saml2
from urllib.parse import urljoin
from datetime import timedelta
import os
import secrets
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_prefix=1)
POSTBACK_ROUTE = '/login'
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
@app.route('/status/2fa')
@app.route('/status/group/<group>')
@app.route('/status/group/<group>/2fa')
@app.route('/status/2fa/group/<group>')
def status(group=None):
    """
    Report current authentication status. Return 401 if not authenticated,
    403 if a group was requested that the user is not a member of, or 200
    if the user is authenticated. Presence of /2fa in the url also enforces
    that 2FA authentication occurred and will return a 401 otherwise.

    group - a UW Group the user must be a member of. An SP must be registered
        to receive that group.
    """
    userid = session.get('userid')
    groups = session.get('groups', [])
    wants_2fa = '2fa' in request.path.split('/')
    has_2fa = session.get('has_2fa', False)
    if not userid or (wants_2fa and not has_2fa):
        abort(401)
    if group and group not in groups:
        message = f"{userid} not a member of {group} or SP can't receive it"
        app.logger.error(message)
        abort(403)
    str_2fa = str(has_2fa).lower()
    headers = {'X-Saml-User': userid,
               'X-Saml-Groups': ':'.join(groups),
               'X-Saml-2fa': str_2fa}
    txt = f'Logged in as: {userid}\nGroups: {str(groups)}\n2FA: {str_2fa}'
    return Response(txt, status=200, headers=headers)


def _saml_args():
    """Get entity_id and acs_url from request.headers."""
    entity_id = request.url_root[:-1]  # remove trailing slash
    acs_url = urljoin(request.url_root, POSTBACK_ROUTE[1:])
    if 'X-Saml-Entity-Id' in request.headers:
        entity_id = request.headers['X-Saml-Entity-Id']
    if 'X-Saml-Acs' in request.headers:
        acs_url = urljoin(request.url_root, request.headers['X-Saml-Acs'])
    return dict(entity_id=entity_id, acs_url=acs_url)


@app.route('/login/')
@app.route('/login/<path:return_to>')
@app.route('/2fa/')
@app.route('/2fa/<path:return_to>')
def login_redirect(return_to=''):
    """
    Redirect to the IdP for SAML initiation.
    2FA is triggered by presence of session variable 'wants_2fa', which gets
    set in a status check.
    
    return_to - the path to redirect back to after authentication. This and
        the request.query_string are set on the SAML RelayState.
    """
    app.logger.error(f'URL ROOT {request.url_root}')
    query_string = '?' + request.query_string.decode()
    if query_string == '?':
        query_string = ''
    return_to = f'/{return_to}{query_string}'
    args = _saml_args()
    if request.path.startswith('/2fa/'):
        args['two_factor'] = True
    return redirect(uw_saml2.login_redirect(return_to=return_to, **args))


@app.route(POSTBACK_ROUTE, methods=['GET', 'POST'])
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
    session['has_2fa'] = attributes.get('two_factor')
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
