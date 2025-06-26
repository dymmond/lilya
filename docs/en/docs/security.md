# Security

This section explains how to harden lilya based projects.
It explains how to use the security features and common attack vectors.

## Host limiting

### Problem

We have no public API and the project should only serve for a specific host (dns name).
We don't want other traffic which could maybe originate from a ddos.

### Solution

The `TrustedHostMiddleware` can solve the problem. Here we can either block or mark wrong hosts. Its usage is descriped in
[TrustedHostMiddleware](./middleware/trustedhost.md).

## The Challenge of URL-Reflected Search and Malicious Injections

### Problem

We sometimes need to implement a search function where the query is reflected in the URL bar, similar to Google's behavior.
This allows other modules in a project to easily reference the search term.

**The Security Risk: Arbitrary Text Injection**
A significant concern with this approach is the potential for scammers to inject arbitrary text blocks into the URL, even if properly escaped. This can be used to trick users, especially since modern search boxes are often highly customized and visually appealing.

For example, a scammer could inject text like "Call XY for help" into the URL. Users might mistakenly believe this text is part of the legitimate website content rather than solely a component of their search query, leading to convincing and harmful social engineering attacks.

### Solution

**Enhancing Security with TrustedReferrerMiddleware**
The  [TrustedReferrerMiddleware](./middleware/trustedreferrer.md) is a good tool for mitigating the risk of malicious parameter injection.
This middleware can be used to validate that a referral was only from a legitimate hosts. So the GET parameters can be used safely.

By default, the middleware injects `referrer_is_trusted` into the request scope. This allows your application to:

- Display a warning to the user.
- Trigger an import dialog.
- Simply ignore GET parameters from untrusted referrers.

This provides a robust defense against arbitrary text injection but still allows comfortable linking.

```python
{!> ../../../docs_src/middleware/available/trusted_referrers_simple.py !}
```

## Resource exhaustion

### Problem

Some calls are quite expensive. An automated caller can clog up server resources.

### Solution

**Rate Limiting in Lilya: Leveraging the `ClientIPMiddleware`**

Currently, Lilya provides foundational building blocks for implementing rate limiting. We can utilize the `ClientIPMiddleware` to extract the client's IP address, which then serves as a crucial identifier for applying rate-limiting policies. This allows us to control the rate of requests based on individual client IPs, preventing abuse and ensuring system stability.

There is however an external project for ASGI ratelimiting which should also work with `ClientIPMiddleware` because this middleware
inject the `x-real-ip` header:

<a href="https://github.com/abersheeran/asgi-ratelimit">RateLimitMiddleware</a>

## Session fixing

### Problem

Session stealing by stealing cookies via malware.
Especially for sessions with high privileges this is a problem.

### Solution

This technique works by using the clientip and the session middleware. We limit a session to an ip.
We have even two options: `ClientIPMiddleware` or `ClientIPScopeOnlyMiddleware`, depending if we need
headers. The usage is documented in [SessionFixingMiddleware](./middleware.md#sessionfixingmiddleware).

!!! Note
    If the client has an unstable connection, the session can reset from time to time. It is recommended to use the session fixing
    carefully only for sensitive areas or use the `notify_fn` parameter to port from the old session to the new session when appropiate.
