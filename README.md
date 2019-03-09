# nginx-saml-proxy

This docker image can be used as a standalone proxy for an nginx `auth_request`
authentication. You supply it a UW-registered SAML Entity ID and ACS postback
URL, the proxy will take care of the rest.

Example nginx.conf would look like the following...

```
location / {
    auth_request /saml/status/group/uw_it_all;
    auth_request_set $auth_user $upstream_http_x_saml_user;
    error_page 401 = @login_required;
    proxy_set_header Remote-User $auth_user;
    proxy_pass http://secure:5000/;
}

location /saml/ { 
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Saml-Entity-Id https://samldemo.iamdev.s.uw.edu/saml;
    # acs - post-back url registered with the IdP.
    proxy_set_header X-Saml-Acs /saml/login;
    proxy_pass http://saml:5000/;
}

location @login_required {
    return 302 https://$http_host/saml/login$request_uri;
}
```

See the [example nginx config](test/nginx/server.conf) for more examples.

## SECRET_KEY

This app wants an environment variable `SECRET_KEY`, which should be a secure,
randomly-generated string. Otherwise, we generate one on the fly, which only
works as long as the app is running, and won't work in a distributed environment.
SECRET_KEY is used to sign cookies, so setting a new key effectively
invalidates all existing sessions.
