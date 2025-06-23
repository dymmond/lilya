# Security

This section explains how to harden lilya based projects.
It explains how to use the security features and common attack vectors.

## Host limiting

**Problem**

We have no public API and the project should only serve for a specific host (dns name).
We don't want other traffic which could maybe originate from a ddos.

**Solution**

The `TrustedHostMiddleware` can solve the problem. Here we can either block or mark wrong hosts. Its usage is descriped in
[TrustedHostMiddleware](./middleware/trustedhost.md).

## GET-based search

**Problem**

We want a search which reflects in the url bar like google does. So we can refer to the search in other modules.
The issue: scammers can inject arbitary text blocks (despite they are proper escaped) and fool users.
For example by injecting texts like: "Call xy for help.".
It can be very convincing when the user doesn't understand that the text is only used for the search.
This is especcially today a problem because search boxes are customized and look fancy.

**Solution**

The [TrustedReferrerMiddleware](./middleware/trustedreferrer.md) helps here.
With this middlware we can ensure only legitim hosts can inject parameters via GET parameters and refer. By default, only `referrer_is_trusted` is
injected in the scope. So a warning or an import dialog can pop up or the get parameters are just ignored.

```python
{!> ../../../docs_src/middleware/available/trusted_referrers_simple.py !}
```

## Resource exhaustion

**Problem**

Some calls are quite expensive. An automated caller can clog up server resources.

**Solution**

We have currently only the building blocks for ratelimiting in lilya. We can use the clientip middleware to extract the
ip of the client and use it for ratelimiting purposes.

There is however an external project for ratelimiting:

<a href="https://github.com/abersheeran/asgi-ratelimit">RateLimitMiddleware</a>

## Session fixing

**Problem**

Session stealing by stealing cookies via malware.

**Solution**

This technique works by using the clientip and the session middleware. We limit a session to an ip.
We have even two options: `ClientIPMiddleware` or `ClientIPScopeOnlyMiddleware`, depending if we need
headers. Usage is documented in [SessionFixingMiddleware](./middleware.md#sessionfixingmiddleware).
