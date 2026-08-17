# API Authentication and Authorization Testing

## Authentication vs Authorization

Authentication and authorization are different security concepts.

Authentication answers:

"Who are you?"

Authorization answers:

"What are you allowed to do?"

For API testing, both should be tested independently.

Example:

A user may successfully authenticate but still be unauthorized to access
an administrator-only endpoint.

---

# Authentication

Authentication verifies the identity of the client or user making an API
request.

Common API authentication mechanisms include:

- API keys
- Basic authentication
- Bearer tokens
- OAuth 2.0
- JWT-based authentication
- Session-based authentication
- Mutual TLS where applicable

The exact authentication mechanism depends on the API architecture and
security requirements.

---

# API Key Authentication

An API key is a value supplied by the client to identify or authenticate
the request.

Example:

Authorization: ApiKey <api-key>

The actual header format depends on the API contract.

Test scenarios should include:

- Valid API key.
- Invalid API key.
- Missing API key.
- Expired API key where expiration is supported.
- Revoked API key.
- Empty API key.
- Malformed API key.
- API key belonging to an unauthorized client.

Expected behavior should be validated against the API security contract.

---

# Basic Authentication

Basic authentication typically sends a username and password as
credentials.

Test scenarios should include:

- Valid username and password.
- Invalid username.
- Invalid password.
- Invalid username and password.
- Missing credentials.
- Empty credentials.
- Malformed Authorization header.
- Locked or disabled user.
- Expired credentials where supported.

Sensitive credentials should not be exposed in logs, error responses, or
client-visible messages.

---

# Bearer Token Authentication

Bearer token authentication commonly uses an access token in the
Authorization header.

Example:

Authorization: Bearer <access-token>

Test scenarios should include:

- Valid token.
- Missing token.
- Invalid token.
- Expired token.
- Revoked token.
- Malformed token.
- Token belonging to another user.
- Token with insufficient permissions.

The API should validate the token according to its authentication and
authorization requirements.

---

# OAuth 2.0

OAuth 2.0 is an authorization framework that allows applications to obtain
access to protected resources without directly sharing the user's
credentials with the resource server.

A typical flow may involve:

1. Client requests authorization.
2. Authorization server authenticates and authorizes the user.
3. Client receives an authorization result.
4. Client obtains an access token.
5. Client uses the access token to access protected APIs.
6. The resource server validates the access token.

The exact OAuth flow depends on the application's architecture and
requirements.

---

# OAuth Access Tokens

An access token is generally used by the client to access protected
resources.

Example:

Authorization: Bearer <access-token>

Test scenarios include:

- Valid access token.
- Expired access token.
- Invalid access token.
- Revoked access token.
- Missing access token.
- Malformed access token.
- Token with insufficient scope.
- Token issued for a different audience where applicable.

---

# OAuth Refresh Tokens

A refresh token can be used to obtain a new access token when the existing
access token expires, depending on the OAuth implementation.

Important test scenarios include:

- Valid refresh token.
- Invalid refresh token.
- Expired refresh token.
- Revoked refresh token.
- Missing refresh token.
- Malformed refresh token.
- Reuse of a refresh token where rotation is implemented.
- Refresh token issued to another client.
- Refresh token with invalid client credentials.
- Refresh token after the associated authorization is revoked.

Expected behavior must follow the application's OAuth security design.

---

# Access Token Expiration Testing

Access token expiration should be tested explicitly.

Test scenarios:

1. Use a valid access token before expiration.
2. Allow the token to expire.
3. Send a request using the expired token.
4. Verify that the API rejects the request appropriately.
5. Obtain a new access token.
6. Retry the request with the valid token.
7. Verify successful access.

The test should confirm that an expired token cannot continue to provide
unauthorized access.

---

# Refresh Token Flow Testing

A typical refresh-token test flow is:

1. Obtain an access token and refresh token.
2. Use the access token to access a protected API.
3. Allow the access token to expire or simulate expiration.
4. Attempt to access the API using the expired access token.
5. Verify that access is rejected.
6. Submit the refresh token to the token endpoint.
7. Verify that a new access token is returned when the refresh request is
   valid.
8. Use the new access token to access the protected API.
9. Verify successful access.

Additional negative scenarios should also be tested.

---

# Refresh Token Negative Testing

Important negative test scenarios include:

- Missing refresh token.
- Empty refresh token.
- Invalid refresh token.
- Expired refresh token.
- Revoked refresh token.
- Malformed refresh token.
- Refresh token belonging to another client.
- Refresh token used after authorization is revoked.
- Reuse of an already rotated refresh token where rotation is implemented.
- Invalid client authentication.
- Unsupported grant type.

The expected response should be validated against the application's
security contract.

---

# Token Rotation Testing

Some systems rotate refresh tokens after successful use.

A simplified rotation scenario is:

1. Client has refresh token A.
2. Client uses refresh token A.
3. Server issues access token B and refresh token C.
4. Refresh token A becomes invalid if the implementation requires
   single-use rotation.
5. Client attempts to reuse refresh token A.
6. The server should reject the reused token according to the security
   design.

Test both successful rotation and reuse behavior.

---

# Token Revocation Testing

Token revocation testing verifies that revoked credentials cannot continue
to provide access.

Scenarios include:

- Revoke access token where supported.
- Revoke refresh token.
- Revoke user authorization.
- Disable the user.
- Attempt to access the API using previously issued credentials.

Expected behavior depends on the token architecture and revocation design.

---

# Authorization

Authorization determines whether an authenticated identity is allowed to
perform a specific operation.

Examples:

- Regular user can view their own profile.
- Administrator can view administrative information.
- Regular user cannot access administrator endpoints.
- User can read a resource but cannot delete it.
- User can access their own order but not another user's order.

---

# Role-Based Access Control Testing

When APIs use roles, test each important role independently.

Example roles:

- Admin
- Manager
- Standard User
- Read-only User

For each role, verify:

- Allowed operations.
- Forbidden operations.
- Accessible resources.
- Restricted resources.

Example:

A read-only user may be allowed to:

GET /orders/123

but may not be allowed to:

DELETE /orders/123

---

# Permission Testing

If authorization is permission-based, test individual permissions.

Example permissions:

- user.read
- user.create
- user.update
- user.delete

Test combinations such as:

- User with read permission.
- User without read permission.
- User with read and update permissions.
- User with update but without delete permission.

Verify that the API enforces the expected permission boundaries.

---

# Horizontal Authorization Testing

Horizontal authorization verifies that one user cannot access another
user's resources without permission.

Example:

User A owns:

GET /users/A/orders/100

User A should not automatically be able to access:

GET /users/B/orders/200

Test scenarios should include:

- Access own resource.
- Access another user's resource.
- Modify another user's resource.
- Delete another user's resource.

The expected behavior should follow the application's authorization
requirements.

---

# Vertical Authorization Testing

Vertical authorization verifies that a lower-privileged user cannot
perform operations reserved for a higher-privileged role.

Example:

A standard user should not be able to perform an administrator-only
operation.

Test scenarios include:

- Standard user accessing admin endpoint.
- Standard user modifying administrative configuration.
- Standard user attempting privileged operations.
- Administrator performing the same operation successfully.

---

# Authentication and Authorization Test Matrix

A useful test strategy is to combine authentication state and permission
state.

Example:

| Authentication | Authorization | Expected Behavior |
|---|---|---|
| Missing | Not applicable | Reject request |
| Invalid | Not applicable | Reject request |
| Valid | Insufficient permission | Reject request |
| Valid | Correct permission | Allow request |
| Expired | Not applicable | Reject request |
| Revoked | Not applicable | Reject request |

The exact status codes and error responses should be validated against the
API contract.

---

# Authentication Negative Test Cases

Common negative scenarios include:

1. Missing credentials.
2. Invalid credentials.
3. Expired credentials.
4. Revoked credentials.
5. Malformed credentials.
6. Empty credentials.
7. Credentials belonging to another client.
8. Credentials with insufficient scope.
9. Disabled user credentials.
10. Authentication against an unsupported endpoint.

---

# Authorization Negative Test Cases

Common authorization scenarios include:

1. Authenticated user accessing an unauthorized endpoint.
2. User accessing another user's resource.
3. Standard user accessing administrator functionality.
4. Read-only user attempting an update.
5. User without delete permission attempting deletion.
6. User with expired authorization attempting access.
7. User with insufficient OAuth scope.
8. User attempting to modify restricted data.

---

# Security Validation

Authentication and authorization testing should also consider whether
the API accidentally exposes sensitive information.

Verify that error responses do not unnecessarily expose:

- Passwords.
- Access tokens.
- Refresh tokens.
- API keys.
- Internal credentials.
- Stack traces.
- Database details.
- Internal server paths.
- Sensitive personal information.

---

# Authentication and Authorization Testing Best Practices

Recommended practices include:

- Test authentication independently from authorization.
- Test valid and invalid credentials.
- Test expired credentials.
- Test revoked credentials.
- Test missing credentials.
- Test malformed credentials.
- Test role-based access.
- Test permission boundaries.
- Test horizontal authorization.
- Test vertical authorization.
- Test token expiration.
- Test refresh-token behavior.
- Test token revocation where applicable.
- Verify sensitive data is not exposed.
- Validate security behavior against the documented API contract.
- Avoid storing real credentials in test source code.
- Use dedicated test credentials and test environments.

---

# QE Decision Guideline

For every protected API endpoint, ask:

1. Can an unauthenticated user access it?
2. Can an authenticated user without permission access it?
3. Can another user access this resource?
4. Can a lower-privileged role perform this operation?
5. What happens when the access token expires?
6. What happens when the access token is invalid?
7. What happens when the refresh token is invalid?
8. What happens when credentials are revoked?
9. Are sensitive details exposed in error responses?
10. Does the behavior match the documented security contract?

A strong authentication and authorization test strategy validates both
successful access and every important unauthorized access path.